from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from .db import get_db
from .models import Server

async def api_key_checker(x_api_key: str = Header(None), db: Session = Depends(get_db)) -> Server:
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing API key")
    server = db.query(Server).filter(Server.api_key == x_api_key).first()
    if not server:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return server
