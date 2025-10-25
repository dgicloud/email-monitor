from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from .db import Base

class Server(Base):
    __tablename__ = "servers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    api_key = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    logs = relationship("MailLog", back_populates="server")

class MailLog(Base):
    __tablename__ = "maillogs"
    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=False)
    kind = Column(String(20), nullable=False)
    sender = Column(String(255))
    recipient = Column(String(255))
    status = Column(String(50))
    message = Column(Text)
    message_id = Column(String(255))
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    server = relationship("Server", back_populates="logs")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
