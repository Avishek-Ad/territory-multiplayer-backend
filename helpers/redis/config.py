import redis

REDIS_URL = "redis://localhost:6379/0"

redis_client = redis.from_url(REDIS_URL, decode_responses=True)

try:
    redis_client.ping()
    print("🚀 Successfully connected to the Redis container!")
except redis.exceptions.ConnectionError as e:
    print(f"❌ Critical Error: Could not connect to Redis at {REDIS_URL}")
    print(f"👉 Error Details: {e}")
    print("👉 Hint: Check if your Docker container is running or if port 6379 is mapped correctly.")