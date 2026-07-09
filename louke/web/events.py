from __future__ import annotations

import asyncio
from typing import Any


class EventBroker:
    def __init__(self) -> None:
        self._queues: set[asyncio.Queue[dict[str, Any]]] = set()

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._queues.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        self._queues.discard(queue)

    async def publish(self, event: str, data: dict[str, Any]) -> None:
        for queue in list(self._queues):
            await queue.put({"event": event, "data": data})

    def publish_nowait(self, event: str, data: dict[str, Any]) -> None:
        for queue in list(self._queues):
            queue.put_nowait({"event": event, "data": data})
