from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import database, models, schemas
import os
from auth import oauth2_scheme # Need to fix imports since auth.py depends on grpc_server config
from jose import JWTError, jwt
from grpc_server import SECRET_KEY, ALGORITHM
import redis
import json

router = APIRouter(prefix="/rooms", tags=["Rooms"])

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: int = payload.get("id")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user

@router.post("/", response_model=schemas.RoomResponse)
def create_room(room: schemas.RoomCreate, current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    db_room = db.query(models.Room).filter(models.Room.name == room.name).first()
    if db_room:
        raise HTTPException(status_code=400, detail="Room already exists")
    
    new_room = models.Room(
        name=room.name,
        max_participants=room.max_participants,
        created_by=current_user.id
    )
    db.add(new_room)
    db.commit()
    db.refresh(new_room)
    return new_room

@router.get("/", response_model=List[schemas.RoomResponse])
def list_rooms(db: Session = Depends(database.get_db)):
    return db.query(models.Room).filter(models.Room.is_active == True).all()

@router.get("/{room_id}", response_model=schemas.RoomResponse)
def get_room(room_id: int, db: Session = Depends(database.get_db)):
    room = db.query(models.Room).filter(models.Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room

@router.post("/{room_id}/block")
def block_user_from_room(room_id: int, user_to_block_id: int, reason: str = "Banned by admin", current_user: models.User = Depends(get_current_user), db: Session = Depends(database.get_db)):

    room = db.query(models.Room).filter(models.Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")


    if room.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Only room creator can ban users")


    if user_to_block_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot ban yourself")
        

    user_to_block = db.query(models.User).filter(models.User.id == user_to_block_id).first()
    if not user_to_block:
         raise HTTPException(status_code=404, detail="User not found")


    existing_ban = db.query(models.RoomBan).filter(models.RoomBan.room_id == room_id, models.RoomBan.user_id == user_to_block_id).first()
    if existing_ban:
        return {"message": "User already banned"}
        
    new_ban = models.RoomBan(user_id=user_to_block_id, room_id=room_id, reason=reason)
    db.add(new_ban)
    db.commit()
    

    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        r = redis.from_url(redis_url, decode_responses=True)
        kick_message = json.dumps({
            "type": "system_kick",
            "user_id": user_to_block_id
        })
        r.publish(f"room:{room_id}", kick_message)
        print(f"Sent output kick for user {user_to_block_id} in room {room_id}")
    except Exception as e:
        print(f"Failed to send kick message to Redis: {e}")

    return {"message": f"User {user_to_block.username} banned from room {room.name}"}
    return {"message": f"User {user_to_block.username} banned from room {room.name}"}

@router.get("/{room_id}/messages")
def get_room_messages(room_id: int, limit: int = 50, db: Session = Depends(database.get_db)):
    messages = db.query(models.Message).filter(models.Message.room_id == room_id).order_by(models.Message.timestamp.asc()).limit(limit).all()
    
    return [
        {
            "id": msg.id,
            "content": msg.content,
            "user_id": msg.user_id,
            "username": msg.sender.username if msg.sender else "Unknown",
            "timestamp": msg.timestamp
        }
        for msg in messages
    ]
