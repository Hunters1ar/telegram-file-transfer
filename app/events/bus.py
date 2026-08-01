import asyncio
from typing import Callable, Awaitable, Any, Dict, List

class EventBus:
    def __init__(self):
        self.subscribers: Dict[str, List[Callable[[Any], Awaitable[None]]]] = {}

    def subscribe(self, event_name: str, handler: Callable[[Any], Awaitable[None]]):
        if event_name not in self.subscribers:
            self.subscribers[event_name] = []
        self.subscribers[event_name].append(handler)
        print(f"Subscribed handler {handler.__name__} to {event_name}")

    async def publish(self, event_name: str, payload: Any):
        if event_name in self.subscribers:
            handlers = self.subscribers[event_name]
            # Fire and forget
            for handler in handlers:
                asyncio.create_task(handler(payload))

event_bus = EventBus()

# Event Constants
class Events:
    FILE_CREATED = "FILE_CREATED"
    FILE_DELETED = "FILE_DELETED"
    FILE_DOWNLOADED = "FILE_DOWNLOADED"
    FILE_SHARED = "FILE_SHARED"
    REMOTE_UPLOAD_COMPLETED = "REMOTE_UPLOAD_COMPLETED"
