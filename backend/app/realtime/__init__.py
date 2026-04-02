"""
Real-time WebSocket support for instant updates.
Uses flask-sock for WebSocket connections.
"""

import json
import threading
from typing import Dict, Set, Optional, Any

from flask import request
from flask_sock import Sock

from app.services.auth_service import AuthService

sock = Sock()

# Connected clients: ws -> set of room names
_clients: Dict[Any, Set[str]] = {}
_lock = threading.Lock()


def _get_token() -> Optional[str]:
    """Extract JWT from query param ?token= or from request."""
    token = request.args.get('token')
    if token:
        return token
    # Also support Bearer in query (unusual but possible)
    auth = request.args.get('Authorization')
    if auth and auth.startswith('Bearer '):
        return auth[7:]
    return None


def _validate_connection() -> Optional[dict]:
    """Validate WebSocket connection via JWT. Returns user_data or None."""
    token = _get_token()
    if not token:
        return None
    success, user_data, _ = AuthService.validate_token_middleware(token)
    return user_data if success else None


def broadcast(event: str, data: dict, room: Optional[str] = None) -> None:
    """
    Broadcast an event to connected clients.
    - If room is None: send to all connected clients
    - If room is set: send only to clients subscribed to that room
    """
    payload = json.dumps({'event': event, 'data': data})
    with _lock:
        if room is None:
            targets = list(_clients.keys())
        else:
            targets = [ws for ws, rooms in _clients.items() if room in rooms]
    for ws in targets:
        try:
            ws.send(payload)
        except Exception:
            pass  # Client may have disconnected


def broadcast_to_rooms(event: str, data: dict, rooms: list) -> None:
    """Broadcast to clients in any of the given rooms."""
    payload = json.dumps({'event': event, 'data': data})
    room_set = set(rooms)
    with _lock:
        targets = [ws for ws, client_rooms in _clients.items() if room_set & client_rooms]
    seen = set()
    for ws in targets:
        if id(ws) in seen:
            continue
        seen.add(id(ws))
        try:
            ws.send(payload)
        except Exception:
            pass


def register_websocket(app):
    """Register the WebSocket route with the Flask app."""
    sock.init_app(app)

    @sock.route('/ws')
    def websocket_route(ws):
        user_data = _validate_connection()
        if not user_data:
            try:
                ws.send(json.dumps({'event': 'error', 'data': {'message': 'Unauthorized'}}))
                ws.close()
            except Exception:
                pass
            return

        user_id = user_data.get('user_id')
        role = user_data.get('role', '')
        client_rooms = {f'user:{user_id}', f'role:{role}'}

        with _lock:
            _clients[ws] = client_rooms

        try:
            # Receive messages (subscribe/unsubscribe)
            while True:
                try:
                    raw = ws.receive(timeout=300)  # 5 min timeout for keepalive
                except Exception:
                    break
                if raw is None:
                    continue
                try:
                    msg = json.loads(raw)
                    msg_type = msg.get('type')
                    if msg_type == 'subscribe':
                        rooms = msg.get('rooms', [])
                        # Validate: user can only subscribe to user:{own_id}, role:{own_role}, floor:{any}
                        for r in rooms:
                            if isinstance(r, str):
                                if r.startswith('user:') and r != f'user:{user_id}':
                                    continue
                                if r.startswith('role:') and r != f'role:{role}':
                                    continue
                                client_rooms.add(r)
                    elif msg_type == 'unsubscribe':
                        for r in msg.get('rooms', []):
                            if isinstance(r, str):
                                client_rooms.discard(r)
                except (json.JSONDecodeError, TypeError):
                    pass
        finally:
            with _lock:
                _clients.pop(ws, None)
            try:
                ws.close()
            except Exception:
                pass
