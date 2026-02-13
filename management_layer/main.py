from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import threading
import grpc
from concurrent import futures
import time

import database, models
import auth, rooms
import grpc_server
import service_pb2_grpc


# models.Base.metadata.create_all(bind=database.engine) # Moved to startup event


app = FastAPI(title="StreamLink Management Layer")

# Create database tables if they don't exist
models.Base.metadata.create_all(bind=database.engine)


origins = [
    "https://streamlink-deploy.vercel.app",
    "http://localhost:5173",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(rooms.router)

@app.get("/")
def health_check():
    return {"status": "ok", "message": "StreamLink Management Layer is running"}

def run_grpc_server():
    """Runs the gRPC server in a separate thread."""
    print("Starting gRPC Server on :50051...")
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    service_pb2_grpc.add_ManagementServiceServicer_to_server(grpc_server.ManagementService(), server)
    server.add_insecure_port('0.0.0.0:50051')
    server.start()
    server.wait_for_termination()

@app.on_event("startup")
async def startup_event():

    t = threading.Thread(target=run_grpc_server, daemon=True)
    t.start()
    print("gRPC Server thread started.")

if __name__ == '__main__':

    print("Starting HTTP Server on :8000...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False) # Reload false for threading safety in dev
