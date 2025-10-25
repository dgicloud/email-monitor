from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from ..db import get_db
from ..models import MailLog, Server
from ..schemas import MailLogIn, MailLogOut
from ..deps import api_key_checker

router = APIRouter(prefix="/maillog", tags=["maillog"])

@router.post("")
def ingest(logs: List[MailLogIn], server: Server = Depends(api_key_checker), db: Session = Depends(get_db)):
    items = []
    for l in logs:
        ml = MailLog(
            server_id=server.id,
            kind=l.kind,
            timestamp=l.timestamp,
            sender=l.sender,
            recipient=l.recipient,
            status=l.status,
            message=l.message,
            message_id=l.message_id,
        )
        items.append(ml)
    db.add_all(items)
    db.commit()
    return {"ingested": len(items)}

@router.get("", response_model=List[MailLogOut])
def list_logs(
    db: Session = Depends(get_db),
    server: Optional[str] = Query(None),
    email: Optional[str] = Query(None),
    kind: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    limit: int = 100,
    offset: int = 0,
):
    q = db.query(MailLog)
    if server:
        q = q.join(Server).filter(Server.name == server)
    if email:
        q = q.filter((MailLog.sender == email) | (MailLog.recipient == email))
    if kind:
        q = q.filter(MailLog.kind == kind)
    if status:
        q = q.filter(MailLog.status == status)
    if date_from:
        q = q.filter(MailLog.timestamp >= date_from)
    if date_to:
        q = q.filter(MailLog.timestamp <= date_to)
    return q.order_by(MailLog.id.desc()).offset(offset).limit(limit).all()

@router.get("/kpi/summary")
def kpi_summary(db: Session = Depends(get_db), hours: int = 24):
    since = datetime.utcnow() - timedelta(hours=hours)
    mainlog_sum = func.sum(case((MailLog.kind == 'mainlog', 1), else_=0))
    rejectlog_sum = func.sum(case((MailLog.kind == 'rejectlog', 1), else_=0))
    paniclog_sum = func.sum(case((MailLog.kind == 'paniclog', 1), else_=0))

    total = db.query(func.count(MailLog.id)).scalar() or 0
    total_main = db.query(mainlog_sum).scalar() or 0
    total_reject = db.query(rejectlog_sum).scalar() or 0
    total_panic = db.query(paniclog_sum).scalar() or 0

    last_total = db.query(func.count(MailLog.id)).filter(MailLog.timestamp >= since).scalar() or 0
    last_main = db.query(mainlog_sum).filter(MailLog.timestamp >= since).scalar() or 0
    last_reject = db.query(rejectlog_sum).filter(MailLog.timestamp >= since).scalar() or 0
    last_panic = db.query(paniclog_sum).filter(MailLog.timestamp >= since).scalar() or 0

    return {
        "total": {"all": total, "mainlog": total_main, "rejectlog": total_reject, "paniclog": total_panic},
        "last_hours": hours,
        "since": since.isoformat() + "Z",
        "last": {"all": last_total, "mainlog": last_main, "rejectlog": last_reject, "paniclog": last_panic},
    }

@router.get("/kpi/timeseries")
def kpi_timeseries(db: Session = Depends(get_db), hours: int = 24):
    since = datetime.utcnow() - timedelta(hours=hours)
    bucket = func.date_trunc('hour', MailLog.timestamp).label('bucket')
    mainlog_sum = func.sum(case((MailLog.kind == 'mainlog', 1), else_=0)).label('mainlog')
    rejectlog_sum = func.sum(case((MailLog.kind == 'rejectlog', 1), else_=0)).label('rejectlog')
    paniclog_sum = func.sum(case((MailLog.kind == 'paniclog', 1), else_=0)).label('paniclog')
    total_sum = func.count(MailLog.id).label('total')

    rows = (
        db.query(bucket, mainlog_sum, rejectlog_sum, paniclog_sum, total_sum)
        .filter(MailLog.timestamp >= since)
        .group_by(bucket)
        .order_by(bucket.asc())
        .all()
    )
    data = [
        {
            "bucket": b.isoformat().replace("+00:00", "Z"),
            "mainlog": int(m or 0),
            "rejectlog": int(r or 0),
            "paniclog": int(p or 0),
            "total": int(t or 0),
        }
        for (b, m, r, p, t) in rows
    ]
    return {"last_hours": hours, "since": since.isoformat() + "Z", "series": data}
