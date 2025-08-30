from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker
from config import Config

engine = create_engine(Config.DB_URI)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "AdminAccount"
    Id = Column(Integer, primary_key=True)
    Username = Column(String(100), unique=True, nullable=False)
    Password = Column(String(255), nullable=False)  # stored MD5 hash
