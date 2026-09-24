"""Which browser uploaded which tasks.

There are no user accounts in the MVP, so each browser gets a random owner token in its signed
session cookie. The task ids it uploaded are stored in Redis under that token, and a task's
status is only served to its owner: knowing a task id alone is not enough to read its data.
"""

from typing import Any, Protocol

import redis


class TaskOwnership(Protocol):
    def add(self, owner: str, task_ids: list[str]) -> None: ...

    def owns(self, owner: str, task_id: str) -> bool: ...


class RedisTaskOwnership:
    def __init__(self, client: Any, *, ttl_seconds: int) -> None:
        self._client = client
        self._ttl = ttl_seconds

    @classmethod
    def from_url(cls, url: str, *, ttl_seconds: int) -> "RedisTaskOwnership":
        return cls(redis.Redis.from_url(url), ttl_seconds=ttl_seconds)  # connects lazily, on first use

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
