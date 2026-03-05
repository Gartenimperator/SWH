try:
    import uasyncio as asyncio
except ImportError:
    import asyncio


class EventBus:
    def __init__(self):
        self._queue = []
        self._event = asyncio.Event()

    def emit(self, event, data=None):
        """Add an event to the queue and wake up any waiting listener."""
        self._queue.append((event, data or {}))
        self._event.set()

    async def listen(self):
        """Wait for and return the next (event, data) tuple."""
        while not self._queue:
            self._event.clear()
            await self._event.wait()
        return self._queue.pop(0)
