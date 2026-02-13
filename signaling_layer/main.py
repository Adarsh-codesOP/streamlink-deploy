from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio
import json
import uvicorn
from contextlib import asynccontextmanager

from connection_manager import manager
from redis_manager import redis_manager
from grpc_client import grpc_client
import config

@asynccontextmanager
async def lifespan(app: FastAPI):

    print("Starting redis")
    await redis_manager.set_callback(handle_redis_message)
    await redis_manager.connect()
    yield

    print("Shutting down")

app = FastAPI(lifespan=lifespan)
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def handle_redis_message(channel: str, data: str):
    """Callback triggered by RedisManager when a message arrives."""
    if channel.startswith("room:"):
        try:
            room_id = int(channel.split(":")[1])
            message_data = json.loads(data)
            

            if message_data.get("type") == "system_kick":
                target_user_id = message_data.get("user_id")
                print(f"Received System Kick for User {target_user_id} in Room {room_id}")
                await manager.kick_user(room_id, target_user_id)
                return


            await manager.broadcast_to_room(room_id, data)
        except Exception as e:
            print(f"Error handling redis message: {e}")

@app.websocket("/ws/{room_id}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: int, user_id: int):

    await websocket.accept()

    try:
        # Validate User with Management Layer
        print(f"DEBUG: Validating join for user {user_id} in room {room_id}...")
        try:
            allowed, reason = await grpc_client.validate_join(user_id, room_id)
            print(f"DEBUG: Validation result: allowed={allowed}, reason={reason}")
        except Exception as e:
            print(f"DEBUG: gRPC validate_join failed: {e}")
            raise e

        if not allowed:
            print(f"DEBUG: Join Denied for User {user_id}: {reason}")
            await websocket.close(code=1008, reason=reason)
            return

        # Connect to Room Manager
        print("DEBUG: Connecting to ConnectionManager...")
        await manager.connect(websocket, room_id, user_id)
        
        # Subscribe to Redis Room Channel
        print("DEBUG: Subscribing to Redis...")
        await redis_manager.subscribe(room_id)

        # Notify Management Layer (Non-blocking attempt)
        print("DEBUG: Notifying Management Layer (user_joined)...")
        try:
            await grpc_client.user_joined(user_id, room_id)
        except Exception as e:
            print(f"DEBUG: gRPC Join/Update Error: {e}")

        # Send Initial State (Existing Users)
        print("DEBUG: Sending initial state...")
        active_user_ids = manager.get_active_users(room_id)
        await websocket.send_text(json.dumps({
            "type": "existing_users",
            "ids": active_user_ids
        }))

        # Broadcast Join Details via Redis
        print("DEBUG: Broadcasting user_joined to Redis...")
        await redis_manager.publish(room_id, {
            "type": "user_joined",
            "user_id": user_id
        })

        print(f"DEBUG: User {user_id} successfully connected to Room {room_id}. Entering main loop.")

        # Main WebSocket Loop
        while True:
            data = await websocket.receive_text()
            # print(f"DEBUG: Received data: {data}") # Optional: can be noisy
            message_data = json.loads(data)
            
            msg_type = message_data.get("type")

            # Chat Message
            if msg_type == "chat":
                content = message_data.get("content")
                
                #real time delivery using redis
                payload = {
                    "type": "chat",
                    "user_id": user_id,
                    "content": content
                }
                await redis_manager.publish(room_id, payload)
                
                #persistant message to management server
                try:
                    asyncio.create_task(grpc_client.store_message(user_id, room_id, content))
                except Exception as e:
                     print(f"gRPC Store Message Error: {e}")

            # WebRTC signal
            elif msg_type in ["offer", "answer", "candidate"]:
                # Broadcast signal
                payload = {
                    "type": msg_type,
                    "user_id": user_id,
                    "target_id": message_data.get("target_id"),
                    "data": message_data.get("data")
                }

                await redis_manager.publish(room_id, payload)

    except WebSocketDisconnect:
        print(f"User {user_id} disconnected")
        manager.disconnect(websocket)
        
        # Unsubscribe if room empty
        if manager.get_room_count(room_id) == 0:
            await redis_manager.unsubscribe(room_id)

        try:
            await grpc_client.user_left(user_id, room_id)
        except Exception as e:
            print(f"gRPC Leave Error: {e}")
            
        # Notify others
        await redis_manager.publish(room_id, {
            "type": "user_left",
            "user_id": user_id
        })

    except Exception as e:
        print(f"WEBSOCKET FAILURE: {e}")
        import traceback
        traceback.print_exc()
        try:
            # Shorten reason to fit WS limit (123 bytes)
            reason_str = str(e)[:120]
            await websocket.close(code=1011, reason=reason_str) 
        except:
            pass # Socket might be already closed



if __name__ == "__main__":
    uvicorn.run("main:app", host=config.HOST, port=config.PORT, reload=True)
