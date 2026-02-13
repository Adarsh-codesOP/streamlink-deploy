from typing import List, Dict
from fastapi import WebSocket
import collections

class ConnectionManager:
    def __init__(self):

        self.active_connections: Dict[int, List[WebSocket]] = collections.defaultdict(list)
        self.socket_to_room: Dict[WebSocket, int] = {}
        self.socket_to_user: Dict[WebSocket, int] = {}

    async def connect(self, websocket: WebSocket, room_id: int, user_id: int):

        self.active_connections[room_id].append(websocket)
        self.socket_to_room[websocket] = room_id
        self.socket_to_user[websocket] = user_id
        print(f"User {user_id} connected to Room {room_id}")

    def disconnect(self, websocket: WebSocket):
        room_id = self.socket_to_room.get(websocket)
        user_id = self.socket_to_user.get(websocket)
        
        if room_id and websocket in self.active_connections[room_id]:
            self.active_connections[room_id].remove(websocket)
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]
        
        if websocket in self.socket_to_room:
            del self.socket_to_room[websocket]
        if websocket in self.socket_to_user:
            del self.socket_to_user[websocket]
            
        return room_id, user_id

    async def broadcast_to_room(self, room_id: int, message: str, exclude: WebSocket = None):
        """Sends a message to all local sockets in the room."""
        if room_id in self.active_connections:
            for connection in self.active_connections[room_id]:
                if connection != exclude:
                    try:
                        await connection.send_text(message)
                    except Exception as e:
                        print(f"Error broadcasting: {e}")

    def get_room_count(self, room_id: int) -> int:
        return len(self.active_connections.get(room_id, []))

    def get_active_users(self, room_id: int) -> List[int]:
        """Returns a list of unique user IDs currently in the room."""
        users = set()
        if room_id in self.active_connections:
            for ws in self.active_connections[room_id]:
                uid = self.socket_to_user.get(ws)
                if uid:
                    users.add(uid)
        return list(users)

    async def kick_user(self, room_id: int, user_id: int):
        """Disconnects a specific user from the room."""
        target_ws = None
        if room_id in self.active_connections:
            for ws in self.active_connections[room_id]:
                if self.socket_to_user.get(ws) == user_id:
                    target_ws = ws
                    break
        
        if target_ws:
            print(f"Kicking User {user_id} from Room {room_id}")
            try:
                await target_ws.close(code=4003, reason="You have been blocked from this room.")

            except Exception as e:
                print(f"Error closing socket for kicked user: {e}")


manager = ConnectionManager()
