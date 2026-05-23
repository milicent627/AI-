from fastapi import WebSocket


class WebSocketManager:
    def __init__(self):
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, story_id: str, ws: WebSocket):
        await ws.accept()
        self._connections.setdefault(story_id, []).append(ws)

    def disconnect(self, story_id: str, ws: WebSocket):
        if story_id in self._connections:
            self._connections[story_id] = [c for c in self._connections[story_id] if c != ws]

    async def notify(self, story_id: str, event: str, data: dict = None):
        for ws in self._connections.get(story_id, []):
            try:
                await ws.send_json({"event": event, "data": data or {}})
            except Exception:
                pass


ws_manager = WebSocketManager()
