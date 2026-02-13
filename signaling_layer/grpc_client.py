import grpc
import service_pb2
import service_pb2_grpc
import config

class GrpcClient:
    def __init__(self):
        target = f"{config.MANAGEMENT_SERVICE_HOST}:{config.MANAGEMENT_SERVICE_PORT}"
        
        # Debug DNS Resolution
        try:
            import socket
            ip = socket.gethostbyname(config.MANAGEMENT_SERVICE_HOST)
            print(f"DEBUG: DNS Resolved {config.MANAGEMENT_SERVICE_HOST} -> {ip}")
        except Exception as e:
            print(f"CRITICAL: Check DNS failed for {config.MANAGEMENT_SERVICE_HOST}: {e}")

        if config.MANAGEMENT_SSL:
            print(f"DEBUG: Connecting to gRPC Service at {target} (SECURE)")
            creds = grpc.ssl_channel_credentials()
            self.channel = grpc.secure_channel(target, creds)
        else:
            print(f"DEBUG: Connecting to gRPC Service at {target} (INSECURE)")
            self.channel = grpc.insecure_channel(target)
        self.stub = service_pb2_grpc.ManagementServiceStub(self.channel)
        print(f"gRPC Client connected to {target}")

    async def validate_join(self, user_id: int, room_id: int):
        try:

            response = self.stub.ValidateJoin(service_pb2.JoinRequest(user_id=user_id, room_id=room_id))
            return response.allowed, response.reason
        except grpc.RpcError as e:
            error_details = e.details()
            if "DNS resolution failed" in error_details:
                # Provide clearer error for user
                error_msg = f"DNS Error: Host '{config.MANAGEMENT_SERVICE_HOST}' not found."
            else:
                error_msg = f"gRPC Error: {error_details} | Code: {e.code()}"
            
            print(f"DEBUG: gRPC Validation Failed: {error_msg}")
            return False, error_msg
        except Exception as e:
            print(f"DEBUG: Unknown Error in validate_join: {e}")
            return False, f"Unknown Error: {str(e)}"

    async def user_joined(self, user_id: int, room_id: int):
        try:
            self.stub.UserJoined(service_pb2.JoinRequest(user_id=user_id, room_id=room_id))
        except grpc.RpcError as e:
            print(f"gRPC UserJoined Failed: {e}")

    async def user_left(self, user_id: int, room_id: int):
        try:
            self.stub.UserLeft(service_pb2.JoinRequest(user_id=user_id, room_id=room_id))
        except grpc.RpcError as e:
            print(f"gRPC UserLeft Failed: {e}")

    async def store_message(self, user_id: int, room_id: int, content: str):
        try:
            self.stub.StoreMessage(service_pb2.MessageRequest(user_id=user_id, room_id=room_id, content=content))
        except grpc.RpcError as e:
            print(f"gRPC StoreMessage Failed: {e}")


grpc_client = GrpcClient()
