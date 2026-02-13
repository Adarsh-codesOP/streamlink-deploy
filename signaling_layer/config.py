import os

# Signaling Server Config
HOST = os.getenv("SIGNALING_HOST", "0.0.0.0")
PORT = int(os.getenv("SIGNALING_PORT", 8001))

# Management Layer Config (gRPC)
MANAGEMENT_SERVICE_HOST = os.getenv("MANAGEMENT_HOST", "127.0.0.1")
MANAGEMENT_SERVICE_PORT = int(os.getenv("MANAGEMENT_PORT", 50051))
MANAGEMENT_SSL = os.getenv("MANAGEMENT_SSL", "false").lower() == "true"

# Redis Config
REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379")

print(f"Config Loaded: Mgmt={MANAGEMENT_SERVICE_HOST}:{MANAGEMENT_SERVICE_PORT}, Redis={REDIS_URL}")
