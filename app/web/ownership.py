"""Which browser uploaded which tasks.

The task ids each account uploaded are stored in Redis under its user id, and a task's status is
only served to its owner: knowing a task id alone is not enough to read its data.
"""

from typing import Any, Protocol


class TaskOwnership(Protocol):
    def add(self, owner: str, task_ids: list[str]) -> None: ...

    def owns(self, owner: str, task_id: str) -> bool: ...


class RedisTaskOwnership:
    def __init__(self, client: Any, *, ttl_seconds: int) -> None:
        self._client = client
        self._ttl = ttl_seconds

    @staticmethod
    def _key(owner: str) -> str:
        return f"task-owner:{owner}"

    def add(self, owner: str, task_ids: list[str]) -> None:
        if not task_ids:
            return
        pipe = self._client.pipeline()
        pipe.sadd(self._key(owner), *task_ids)
        pipe.expire(self._key(owner), self._ttl)  # ownership expires together with the results
        pipe.execute()

    def owns(self, owner: str, task_id: str) -> bool:
        if not self._client.sismember(self._key(owner), task_id):
            return False
        # Sliding expiry: while the owner keeps polling, a long queue cannot make it lose access.
        self._client.expire(self._key(owner), self._ttl)
        return True
