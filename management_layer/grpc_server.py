import grpc
from concurrent import futures
import service_pb2
import service_pb2_grpc
import database, models
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt

import os

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key-change-this-in-production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

class ManagementService(service_pb2_grpc.ManagementServiceServicer):
    

    def Register(self, request, context):
        db: Session = database.SessionLocal()
        try:
            hashed_password = pwd_context.hash(request.password)
            user = models.User(username=request.username, password_hash=hashed_password)
            try:
                db.add(user)
                db.commit()
                db.refresh(user)
                return service_pb2.UserResponse(user_id=user.id, username=user.username)
            except Exception as e:
                return service_pb2.UserResponse(user_id=-1, username="Error: Username already exists")
        finally:
            db.close()

    def Login(self, request, context):
        db: Session = database.SessionLocal()
        try:
            user = db.query(models.User).filter(models.User.username == request.username).first()
            if not user or not pwd_context.verify(request.password, user.password_hash):
                return service_pb2.LoginResponse(access_token="", token_type="", user_id=-1)
            
            token_data = {"sub": user.username, "id": user.id}
            token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
            return service_pb2.LoginResponse(access_token=token, token_type="bearer", user_id=user.id)
        finally:
            db.close()

    def CreateRoom(self, request, context):
        db: Session = database.SessionLocal()
        try:
            new_room = models.Room(
                name=request.name,
                max_participants=request.max_participants,
                created_by=request.creator_id
            )
            db.add(new_room)
            db.commit()
            db.refresh(new_room)
            return service_pb2.RoomResponse(
                id=new_room.id, 
                name=new_room.name, 
                max_participants=new_room.max_participants,
                current_participants=new_room.current_participants
            )
        except Exception as e:
             return service_pb2.RoomResponse(id=-1, name="Error: Room exists")
        finally:
            db.close()

    def ListRooms(self, request, context):
        db: Session = database.SessionLocal()
        try:
            rooms = db.query(models.Room).filter(models.Room.is_active == True).all()
            response_rooms = []
            for r in rooms:
                response_rooms.append(service_pb2.RoomResponse(
                    id=r.id,
                    name=r.name,
                    max_participants=r.max_participants,
                    current_participants=r.current_participants
                ))
            return service_pb2.RoomListResponse(rooms=response_rooms)
        finally:
            db.close()

    def ValidateJoin(self, request, context):
        db: Session = database.SessionLocal()
        try:
            room = db.query(models.Room).filter(models.Room.id == request.room_id).first()
            if not room:
                return service_pb2.JoinResponse(allowed=False, reason="Room not found")
            
            ban = db.query(models.RoomBan).filter(
                models.RoomBan.room_id == request.room_id,
                models.RoomBan.user_id == request.user_id
            ).first()
            if ban:
                return service_pb2.JoinResponse(allowed=False, reason=f"Banned: {ban.reason}")

            return service_pb2.JoinResponse(allowed=True, reason="OK")
        finally:
            db.close()

    def UserJoined(self, request, context):
        db: Session = database.SessionLocal()
        try:
            room = db.query(models.Room).filter(models.Room.id == request.room_id).first()
            if room:
                room.current_participants += 1
                room.is_active = True
                db.commit()
            return service_pb2.JoinResponse(allowed=True, reason="Joined")
        finally:
            db.close()

    def UserLeft(self, request, context):
        db: Session = database.SessionLocal()
        try:
            room = db.query(models.Room).filter(models.Room.id == request.room_id).first()
            if room:
                room.current_participants -= 1
                if room.current_participants <= 0:
                    room.current_participants = 0
                    room.is_active = False
                    # db.delete(room)
                db.commit()
            return service_pb2.JoinResponse(allowed=True, reason="Left")
        finally:
            db.close()

    def StoreMessage(self, request, context):
        db: Session = database.SessionLocal()
        try:
            ban = db.query(models.RoomBan).filter(
                models.RoomBan.room_id == request.room_id,
                models.RoomBan.user_id == request.user_id
            ).first()
            if ban:
                return service_pb2.MessageResponse(success=False)

            new_msg = models.Message(
                room_id=request.room_id,
                user_id=request.user_id,
                content=request.content
            )
            db.add(new_msg)
            db.commit()
            return service_pb2.MessageResponse(success=True)
        except Exception:
            db.rollback()
            return service_pb2.MessageResponse(success=False)
        finally:
            db.close()

    def BlockUser(self, request, context):
        db: Session = database.SessionLocal()
        try:

            room = db.query(models.Room).filter(models.Room.id == request.room_id).first()
            if not room:
                return service_pb2.BlockResponse(success=False, error="Room not found")
            

            if room.created_by != request.requester_id:
                return service_pb2.BlockResponse(success=False, error="Only room owner can block")

            if request.user_to_block_id == request.requester_id:
                return service_pb2.BlockResponse(success=False, error="Cannot block yourself")

            existing_ban = db.query(models.RoomBan).filter(
                models.RoomBan.room_id == request.room_id,
                models.RoomBan.user_id == request.user_to_block_id
            ).first()
            
            if existing_ban:
                return service_pb2.BlockResponse(success=True) # Already blocked is a success state

            new_ban = models.RoomBan(
                room_id=request.room_id,
                user_id=request.user_to_block_id,
                reason=request.reason
            )
            db.add(new_ban)
            db.commit()
            return service_pb2.BlockResponse(success=True)
            
        except Exception as e:
            return service_pb2.BlockResponse(success=False, error=str(e))
        finally:
            db.close()

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    service_pb2_grpc.add_ManagementServiceServicer_to_server(ManagementService(), server)
    server.add_insecure_port('0.0.0.0:50051')
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
