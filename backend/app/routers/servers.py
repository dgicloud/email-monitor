import secrets
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Server, MailLog
from ..schemas import ServerCreate, ServerOut

router = APIRouter(prefix="/servers", tags=["servers"])

@router.post("/register", response_model=ServerOut)
def register_server(payload: ServerCreate, db: Session = Depends(get_db)):
    if db.query(Server).filter(Server.name == payload.name).first():
        raise HTTPException(status_code=400, detail="Server already exists")
    api_key = secrets.token_hex(32)
    s = Server(name=payload.name, api_key=api_key)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s

@router.get("", response_model=list[ServerOut])
def list_servers(db: Session = Depends(get_db)):
    return db.query(Server).order_by(Server.id.desc()).all()

@router.get("/register", response_model=ServerOut)
def register_server_q(name: str, db: Session = Depends(get_db)):
    if db.query(Server).filter(Server.name == name).first():
        raise HTTPException(status_code=400, detail="Server already exists")
    api_key = secrets.token_hex(32)
    s = Server(name=name, api_key=api_key)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s

@router.delete("/{server_id}")
def delete_server(server_id: int, db: Session = Depends(get_db)):
    s = db.query(Server).filter(Server.id == server_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Server not found")
    db.query(MailLog).filter(MailLog.server_id == s.id).delete()
    db.delete(s)
    db.commit()
    return {"detail": "deleted"}
