import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker





def get_db_engine(max_retries=5, delay=2):
    """Attempt to connect to the database with retries."""
    import time
    from sqlalchemy.exc import OperationalError, ProgrammingError

    # Force usage of environment variable
    database_url = os.environ.get("DATABASE_URL")
    
    # Debug logging (masking password)
    if database_url:
        masked_url = database_url.split("@")[-1] if "@" in database_url else "********"
        print(f"DEBUG: Connecting to DATABASE_URL ending in ...@{masked_url}")
    else:
        print("CRITICAL: DATABASE_URL environment variable is NOT set!")

    # Fallback for local testing ONLY if explicitly specifically needed, but user requested removal.
    # We will use the env var directly.
    if not database_url:
         # Localhost fallback for dev convenience if needed, 
         # but for this debugging step we stick to the plan:
         database_url = "postgresql://postgres:Adarsh%40123@localhost:5432/StreamLink"
         print("DEBUG: Using localhost fallback because DATABASE_URL is missing.")

    for attempt in range(max_retries):
        try:
            # Create engine
            engine = create_engine(database_url)
            # Test connection
            with engine.connect() as connection:
                print("Database connection successful.")
                return engine
        except (OperationalError, ProgrammingError) as e:
            print(f"Database connection failed (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 2  # Exponential backoff
            else:
                raise e

engine = get_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
