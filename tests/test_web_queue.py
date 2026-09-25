import pytest

from app.llm import LLMExtractionError, LLMTransientError
from app.pdf_text import NoTextLayerError, UnreadablePdfError
from app.web.ownership import RedisTaskOwnership
from app.web.queue import DEFAULT_ERROR, describe_error, to_status
from tests.fakes import FakeRedis


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        ("PENDING", "pending"),
        ("RECEIVED", "pending"),
        ("STARTED", "processing"),
        ("RETRY", "processing"),  # waiting to retry after a rate limit: still being processed
        ("SUCCESS", "completed"),
        ("FAILURE", "failed"),
        ("REVOKED", "failed"),
    ],
)
def test_celery_states_map_to_four_ui_states(state: str, expected: str) -> None:
    assert to_status(state, None).status == expected


def test_success_carries_the_result() -> None:
    status = to_status("SUCCESS", {"document": {"document_type": "other"}})

    assert status.result == {"document": {"document_type": "other"}}
    assert status.error is None


def test_failure_carries_a_user_message_not_the_exception() -> None:
    status = to_status("FAILURE", NoTextLayerError("internal detail /tmp_uploads/abc.pdf"))

    assert status.result is None
    assert status.error is not None
    assert "/tmp_uploads" not in status.error


@pytest.mark.parametrize(
    ("error", "fragment"),
    [
        (NoTextLayerError("x"), "scanned"),
        (UnreadablePdfError("x"), "damaged"),
        (LLMTransientError("x"), "busy"),
        (LLMExtractionError("x"), "structured data"),
        (type("UploadExpiredError", (Exception,), {})("x"), "Upload it again"),
    ],
)
def test_known_errors_get_specific_messages(error: Exception, fragment: str) -> None:
    assert fragment in describe_error(error)


def test_unknown_errors_get_a_generic_message() -> None:
    assert describe_error(ValueError("refusing to process /etc/passwd")) == DEFAULT_ERROR


def test_redis_ownership_records_tasks_with_the_result_ttl() -> None:
    redis = FakeRedis()
    ownership = RedisTaskOwnership(redis, ttl_seconds=3600)

    ownership.add("owner-a", ["t1", "t2"])

    assert ownership.owns("owner-a", "t1")
    assert not ownership.owns("owner-b", "t1")
    assert redis.ttls == {"task-owner:owner-a": 3600}  # ownership expires together with the results


def test_redis_ownership_ignores_empty_batches() -> None:
    redis = FakeRedis()

    RedisTaskOwnership(redis, ttl_seconds=60).add("owner-a", [])

    assert redis.sets == {}


def test_ownership_ttl_is_refreshed_while_the_owner_keeps_polling() -> None:
    # A long queue can outlast the TTL set at upload time; an active owner must not lose access.
    redis = FakeRedis()
    ownership = RedisTaskOwnership(redis, ttl_seconds=3600)
    ownership.add("owner-a", ["t1"])
    redis.ttls["task-owner:owner-a"] = 5  # almost expired

    assert ownership.owns("owner-a", "t1")
    assert redis.ttls["task-owner:owner-a"] == 3600


def test_checking_a_foreign_task_does_not_extend_anything() -> None:
    redis = FakeRedis()
    ownership = RedisTaskOwnership(redis, ttl_seconds=3600)

    assert not ownership.owns("owner-b", "t1")
    assert redis.ttls == {}
