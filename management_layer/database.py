import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker




# Default to local postgres if DATABASE_URL is not set (e.g. local dev without docker)
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:Adarsh%40123@localhost:5432/StreamLink")


def get_db_engine(max_retries=5, delay=2):
    """Attempt to connect to the database with retries."""
    import time
    from sqlalchemy.exc import OperationalError

    for attempt in range(max_retries):
        try:
            # Create engine
            engine = create_engine(SQLALCHEMY_DATABASE_URL)
            # Test connection
            with engine.connect() as connection:
                print("Database connection successful.")
                return engine
        except OperationalError as e:
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
