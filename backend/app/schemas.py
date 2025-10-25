from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

class AuthRequest(BaseModel):
    email: str
    password: str

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class ServerCreate(BaseModel):
    name: str

class ServerOut(BaseModel):
    id: int
    name: str
    api_key: str
    created_at: datetime
    class Config:
        from_attributes = True

class MailLogIn(BaseModel):
    server_name: str
    kind: str
    timestamp: datetime
    sender: Optional[str] = None
    recipient: Optional[str] = None
    status: Optional[str] = None
    message: Optional[str] = None
    message_id: Optional[str] = None

class MailLogQuery(BaseModel):
    server: Optional[str] = None
    email: Optional[str] = None
    kind: Optional[str] = None
    status: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None

class MailLogOut(BaseModel):
    id: int
    server_id: int
    kind: str
    sender: Optional[str]
    recipient: Optional[str]
    status: Optional[str]
    message: Optional[str]
    message_id: Optional[str]
    timestamp: datetime
    class Config:
        from_attributes = True
