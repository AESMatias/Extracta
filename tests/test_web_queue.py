from typing import Any

import pytest

from app.llm import LLMExtractionError, LLMTransientError
from app.pdf_text import NoTextLayerError, UnreadablePdfError
from app.web.ownership import RedisTaskOwnership
from app.web.queue import DEFAULT_ERROR, describe_error, to_status


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
    ],
)
def test_known_errors_get_specific_messages(error: Exception, fragment: str) -> None:
    assert fragment in describe_error(error)


def test_unknown_errors_get_a_generic_message() -> None:
    assert describe_error(ValueError("refusing to process /etc/passwd")) == DEFAULT_ERROR


class FakeRedis:
    def __init__(self) -> None:
        self.sets: dict[str, set[str]] = {}
        self.ttls: dict[str, int] = {}

    def pipeline(self) -> "FakeRedis":
        return self

    def sadd(self, key: str, *values: str) -> None:
        self.sets.setdefault(key, set()).update(values)

    def expire(self, key: str, seconds: int) -> None:
        self.ttls[key] = seconds

    def execute(self) -> list[Any]:
        return []

    def sismember(self, key: str, value: str) -> bool:
        return value in self.sets.get(key, set())


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
