import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool

load_dotenv()

USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port", "5432")
DBNAME = os.getenv("dbname", "postgres")

DATABASE_URL = f"postgresql+psycopg2://{USER}:{PASSWORD}@{HOST}:{PORT}/{DBNAME}?sslmode=require"

# If using Port 6543 (Transaction Pooler), disable SQLAlchemy pooling & prepared statements
if PORT == "6543":
    engine = create_engine(
        DATABASE_URL,
        poolclass=NullPool,
        connect_args={
            "prepare_threshold": None  # <--- DISABLES PREPARED STATEMENT CACHING
        }
    )
else:
    # Port 5432: Direct connection - enable pre-ping to automatically reconnect
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()