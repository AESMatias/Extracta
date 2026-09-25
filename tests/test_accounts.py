import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import Engine, select

from app.accounts import (
    AccountBlockedError,
    AccountError,
    Charge,
    EmailTakenError,
    InvalidCredentialsError,
    authenticate,
    google_sign_in,
    page_limit,
    privileges,
    record_usage,
    refund_usage,
    register,
    split_charge,
    usage,
)
from app.db import session_scope
from app.models import User

NOW = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)
PASSWORD = "correct horse battery"


def new_user(**changes: object) -> uuid.UUID:
    with session_scope() as db:
        user = register(db, email="Ana@Example.com ", password=PASSWORD, name="  Ana  Pérez ", require_approval=False)
        for key, value in changes.items():
            setattr(user, key, value)
        return user.id


def load(user_id: uuid.UUID) -> User:
    with session_scope() as db:
        user = db.get(User, user_id)
        assert user is not None
        return user


# --------------------------------------------------------------------------- registration


def test_registration_creates_an_active_free_account(db_engine: Engine) -> None:
    user = load(new_user())

    assert user.email == "ana@example.com"  # normalized
    assert user.name == "Ana Pérez"
    assert user.status == "active"
    assert user.plan == "free"
    assert user.password_hash is not None and PASSWORD not in user.password_hash
    assert user.password_hash.startswith("pbkdf2:sha256:600000")


def test_manual_approval_leaves_new_accounts_pending(db_engine: Engine) -> None:
    with session_scope() as db:
        user = register(db, email="bob@example.com", password=PASSWORD, name=None, require_approval=True)

    assert user.status == "pending"


def test_email_can_only_register_once(db_engine: Engine) -> None:
    new_user()

    with pytest.raises(EmailTakenError), session_scope() as db:
        register(db, email="ANA@example.com", password=PASSWORD, name=None, require_approval=False)


@pytest.mark.parametrize(
    ("email", "password"),
    [("not-an-email", PASSWORD), ("ana@example.com", "short"), ("ana@example.com", "ana@example.com")],
)
def test_invalid_registrations_are_refused(db_engine: Engine, email: str, password: str) -> None:
    with pytest.raises(AccountError), session_scope() as db:
        register(db, email=email, password=password, name=None, require_approval=False)


# --------------------------------------------------------------------------- password sign-in


def test_sign_in_with_the_right_password(db_engine: Engine) -> None:
    user_id = new_user()

    with session_scope() as db:
        user = authenticate(db, email="ANA@example.com", password=PASSWORD)

    assert user.id == user_id


@pytest.mark.parametrize(
    ("email", "password"), [("ana@example.com", "wrong password!"), ("nobody@example.com", PASSWORD)]
)
def test_wrong_password_and_unknown_email_get_the_same_error(db_engine: Engine, email: str, password: str) -> None:
    new_user()

    with pytest.raises(InvalidCredentialsError, match="Incorrect email or password"), session_scope() as db:
        authenticate(db, email=email, password=password)


@pytest.mark.parametrize("status", ["rejected", "suspended"])
def test_blocked_accounts_cannot_sign_in(db_engine: Engine, status: str) -> None:
    new_user(status=status)

    with pytest.raises(AccountBlockedError), session_scope() as db:
        authenticate(db, email="ana@example.com", password=PASSWORD)


def test_pending_accounts_can_sign_in(db_engine: Engine) -> None:
    new_user(status="pending")  # they see their dashboard with an "awaiting approval" notice

    with session_scope() as db:
        assert authenticate(db, email="ana@example.com", password=PASSWORD).status == "pending"


# --------------------------------------------------------------------------- Google sign-in


def google(db_email: str = "ana@example.com", verified: bool = True, sub: str = "google-123") -> User:
    with session_scope() as db:
        return google_sign_in(db, sub=sub, email=db_email, email_verified=verified, name="Ana", require_approval=False)


def test_google_creates_an_account_without_password(db_engine: Engine) -> None:
    user = google()

    assert user.google_sub == "google-123"
    assert user.password_hash is None
    assert user.status == "active"


def test_google_links_to_an_existing_email_account(db_engine: Engine) -> None:
    user_id = new_user()

    user = google()

    assert user.id == user_id
    assert load(user_id).google_sub == "google-123"


def test_google_returning_user_is_found_by_subject(db_engine: Engine) -> None:
    first = google()

    second = google(db_email="changed@example.com")

    assert second.id == first.id


def test_unverified_google_email_is_refused(db_engine: Engine) -> None:
    with pytest.raises(AccountError, match="not verified"):
        google(verified=False)
    with session_scope() as db:
        assert db.execute(select(User)).first() is None


# --------------------------------------------------------------------------- quota


def charge(task_pages: int, credits_used: int = 0) -> Charge:
    return Charge(task_id=str(uuid.uuid4()), pages=task_pages, credits_used=credits_used)


def test_free_plan_counts_pages_in_a_rolling_24_hours(db_engine: Engine) -> None:
    user_id = new_user()
    with session_scope() as db:
        user = db.get(User, user_id)
        assert user is not None
        record_usage(db, user, [charge(9)], NOW - timedelta(hours=25))  # outside the window
        record_usage(db, user, [charge(3)], NOW - timedelta(hours=3))
        record_usage(db, user, [charge(4)], NOW - timedelta(hours=1))

    with session_scope() as db:
        user = db.get(User, user_id)
        assert user is not None
        quota = usage(db, user, NOW)

    assert (quota.used, quota.limit, quota.remaining, quota.window_hours) == (7, 10, 3, 24)
    assert quota.next_slot_at == NOW + timedelta(hours=21)  # when the 3-hour-old pages stop counting


def test_paid_plans_count_pages_over_30_days(db_engine: Engine) -> None:
    user_id = new_user(plan="pro", plan_expires_at=NOW + timedelta(days=40))
    with session_scope() as db:
        user = db.get(User, user_id)
        assert user is not None
        record_usage(db, user, [charge(200)], NOW - timedelta(days=20))
        record_usage(db, user, [charge(50)], NOW - timedelta(days=31))  # outside the window
        quota = usage(db, user, NOW)

    assert (quota.used, quota.limit, quota.window_hours) == (200, 1000, 720)


def test_prepaid_pages_are_spent_and_given_back(db_engine: Engine) -> None:
    user_id = new_user(page_credits=50)
    task = charge(12, credits_used=8)
    with session_scope() as db:
        user = db.get(User, user_id)
        assert user is not None
        record_usage(db, user, [task], NOW)
        assert user.page_credits == 42
        assert usage(db, user, NOW).used == 4  # only the plan's share counts against the plan

    with session_scope() as db:
        assert refund_usage(db, task.task_id) == 12
        assert refund_usage(db, str(uuid.uuid4())) == 0  # unknown task: nothing to give back
    with session_scope() as db:
        user = db.get(User, user_id)
        assert user is not None
        assert user.page_credits == 50 and usage(db, user, NOW).used == 0


def test_split_charge() -> None:
    assert split_charge(5, plan_left=10, credits_left=0) == (5, 0)
    assert split_charge(5, plan_left=2, credits_left=10) == (2, 3)
    assert split_charge(5, plan_left=2, credits_left=2) is None


def test_paid_plan_and_admin_override_change_the_limit(db_engine: Engine) -> None:
    pro = load(new_user(plan="pro", plan_expires_at=NOW + timedelta(days=10)))
    assert page_limit(pro, NOW) == 1000
    assert page_limit(pro, NOW + timedelta(days=11)) == 10  # plan expired: back to Free

    pro.daily_limit_override = 7
    assert page_limit(pro, NOW) == 7


def test_prepaid_pages_widen_the_privileges(db_engine: Engine) -> None:
    free = load(new_user(page_credits=1))

    widened = privileges(free, NOW)

    assert (widened["max_pages_per_pdf"], widened["max_files_per_upload"], widened["can_save_to_db"]) == (100, 20, True)
    free.page_credits = 0
    assert privileges(free, NOW)["can_save_to_db"] is False
