import json
import os
import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests

LOG_PATTERNS = {
    "main_in": re.compile(
        r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+\S+\s+(?P<qid>\S+)\s+<=\s+(?P<sender>\S+).*?(?:\bid=(?P<msgid>\S+))?.*?(?:\bfor\s+(?P<recipient>\S+))?",
        re.IGNORECASE,
    ),
    "main_out": re.compile(
        r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+\S+\s+(?P<qid>\S+)\s+=>\s+(?P<recipient>\S+).*",
        re.IGNORECASE,
    ),
    "defer": re.compile(
        r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+\S+\s+(?P<qid>\S+)\s+==\s+(?P<recipient>\S+)\s+.*?\bdefer.*?:\s*(?P<reason>.*)$",
        re.IGNORECASE,
    ),
    "warning": re.compile(
        r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+\S+\s+(?P<qid>\S+)\s+<=\s+<>.*?T=\"(?P<subject>[^\"]*)\"\s+for\s+(?P<recipient>\S+)",
        re.IGNORECASE,
    ),
    # Local delivery with name and email in angle brackets, e.g.:
    # 2025-10-25 ... => marcosampaio <marcosampaio@dom.com> ... Saved
    "delivered_local": re.compile(
        r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+\S+\s+(?P<qid>\S+)\s+=>\s+(?:[^<]*<)?(?P<recipient>[^>]+)>.*(?:\bSaved\b)",
        re.IGNORECASE,
    ),
    "sender_id": re.compile(
        r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+\S+\s+Sender identification .*\bS=(?P<sender>\S+)$",
        re.IGNORECASE,
    ),
    # Authentication failures from dovecot_login:
    # 2025-10-25 ... dovecot_login authenticator failed ... (set_id=user@dom)
    "auth_failed": re.compile(
        r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*dovecot_login authenticator failed.*\(set_id=(?P<user>[^\)]+)\)",
        re.IGNORECASE,
    ),
    # Router/Transport, Host/IP, TLS, Size, Reply code (optional in various lines)
    "rt": re.compile(r".*\bR=(?P<router>\S+)\s+T=(?P<transport>\S+).*"),
    "host": re.compile(r".*\bH=(?P<host>[^\s\[]+)\s+\[(?P<ip>[^\]]+)\](?::(?P<port>\d+))?.*"),
    "tls": re.compile(r".*\bX=(?P<tls>TLS[^\s]+).*"),
    "size": re.compile(r".*\bS=(?P<size>\d+).*"),
    "reply": re.compile(r".*\bC=\"(?P<reply>[^\"]+)\".*"),
    # Completion marker
    "completed": re.compile(r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+(?P<qid>\S+)\s+Completed$"),
    "rejectlog": re.compile(r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*rejected.*<(?P<from>[^>]*)> -> (?P<recipient>\S+): (?P<error>.*)$"),
    "paniclog": re.compile(r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*$"),
}

class Agent:
    def __init__(self, cfg: Dict):
        self.cfg = cfg
        self.state_path = cfg.get("state_file", "./state.json")
        self.state = self._load_state()
        # In-memory correlation cache (not persisted across restarts)
        self.qid_cache: Dict[str, Dict] = {}
        self.qid_flush_seconds = int(self.cfg.get("qid_flush_seconds", 600))
        self.max_qid_cache = int(self.cfg.get("max_qid_cache", 10000))

    def _load_state(self) -> Dict:
        if os.path.exists(self.state_path):
            with open(self.state_path, "r") as f:
                return json.load(f)
        return {"offsets": {}}

    def _save_state(self):
        os.makedirs(os.path.dirname(self.state_path), exist_ok=True)
        with open(self.state_path, "w") as f:
            json.dump(self.state, f)

    def _parse_line(self, kind: str, line: str) -> Dict:
        ts = datetime.utcnow()
        sender = None
        recipient = None
        status = None
        message = line.strip()
        message_id = None
        qid = None
        meta: Dict[str, str] = {}
        if kind == "mainlog":
            # Completion line (flush trigger)
            mc = LOG_PATTERNS["completed"].match(line)
            if mc:
                ts = datetime.strptime(mc.group("ts"), "%Y-%m-%d %H:%M:%S")
                qid = mc.group("qid")
                return {
                    "qid": qid,
                    "timestamp": ts,
                    "completed": True,
                    "kind": kind,
                    "message": message,
                }
            m = LOG_PATTERNS["main_in"].match(line)
            if m:
                ts = datetime.strptime(m.group("ts"), "%Y-%m-%d %H:%M:%S")
                sender = m.group("sender")
                qid = m.group("qid")
                recipient = m.group("recipient") or recipient
                message_id = m.group("msgid") or message_id
                status = status or "received"
                # enrich optional meta
                for key, rx in ("rt", LOG_PATTERNS["rt"]), ("host", LOG_PATTERNS["host"]), ("tls", LOG_PATTERNS["tls"]), ("size", LOG_PATTERNS["size"]), ("reply", LOG_PATTERNS["reply"]):
                    mm = rx.match(line)
                    if mm:
                        meta.update({k: v for k, v in mm.groupdict().items() if v})
            else:
                m = LOG_PATTERNS["main_out"].match(line)
                if m:
                    ts = datetime.strptime(m.group("ts"), "%Y-%m-%d %H:%M:%S")
                    recipient = m.group("recipient")
                    qid = m.group("qid")
                    status = status or "delivered"
                    for key, rx in ("rt", LOG_PATTERNS["rt"]), ("host", LOG_PATTERNS["host"]), ("tls", LOG_PATTERNS["tls"]), ("size", LOG_PATTERNS["size"]), ("reply", LOG_PATTERNS["reply"]):
                        mm = rx.match(line)
                        if mm:
                            meta.update({k: v for k, v in mm.groupdict().items() if v})
                else:
                    m = LOG_PATTERNS["defer"].match(line)
                    if m:
                        ts = datetime.strptime(m.group("ts"), "%Y-%m-%d %H:%M:%S")
                        recipient = m.group("recipient")
                        qid = m.group("qid")
                        status = "deferred"
                        message = m.group("reason") or message
                    else:
                        m = LOG_PATTERNS["delivered_local"].match(line)
                        if m:
                            ts = datetime.strptime(m.group("ts"), "%Y-%m-%d %H:%M:%S")
                            recipient = m.group("recipient")
                            qid = m.group("qid")
                            status = "accepted"
                        else:
                            m = LOG_PATTERNS["warning"].match(line)
                            if m:
                                ts = datetime.strptime(m.group("ts"), "%Y-%m-%d %H:%M:%S")
                                recipient = m.group("recipient")
                                qid = m.group("qid")
                                status = "warning"
                                message = m.group("subject") or message
                            else:
                                m = LOG_PATTERNS["sender_id"].match(line)
                                if m:
                                    ts = datetime.strptime(m.group("ts"), "%Y-%m-%d %H:%M:%S")
                                    sender = m.group("sender")
                                    # qid pode não existir nessa linha
                                else:
                                    m = LOG_PATTERNS["auth_failed"].match(line)
                                    if m:
                                        ts = datetime.strptime(m.group("ts"), "%Y-%m-%d %H:%M:%S")
                                        sender = m.group("user")
                                        status = "failed"
                                        message = "dovecot_login authenticator failed"
        elif kind == "rejectlog":
            m = LOG_PATTERNS["rejectlog"].match(line)
            if m:
                ts = datetime.strptime(m.group("ts"), "%Y-%m-%d %H:%M:%S")
                sender = m.group("from")
                recipient = m.group("recipient")
                status = "rejected"
                message = m.group("error")
        elif kind == "paniclog":
            m = LOG_PATTERNS["paniclog"].match(line)
            if m:
                ts = datetime.strptime(m.group("ts"), "%Y-%m-%d %H:%M:%S")
                status = "panic"
        ev = {
            "server_name": self.cfg.get("server_name"),
            "kind": kind,
            "timestamp": ts.isoformat(),
            "sender": sender,
            "recipient": recipient,
            "status": status,
            "message": message,
            "message_id": message_id,
        }
        if qid:
            ev["qid"] = qid
        if meta:
            ev["meta"] = meta
        return ev

    def _update_qid_cache(self, ev: Dict):
        qid = ev.get("qid")
        if not qid:
            return
        c = self.qid_cache.get(qid) or {
            "first_ts": ev["timestamp"],
            "last_ts": ev["timestamp"],
            "sender": None,
            "recipient": None,
            "message_id": None,
            "status": None,
            "reason": None,
            "router": None,
            "transport": None,
            "host": None,
            "ip": None,
            "port": None,
            "tls": None,
            "size": None,
            "reply": None,
        }
        c["last_ts"] = ev["timestamp"]
        if ev.get("sender"): c["sender"] = ev["sender"]
        if ev.get("recipient"): c["recipient"] = ev["recipient"]
        if ev.get("message_id"): c["message_id"] = ev["message_id"]
        if ev.get("status"): c["status"] = ev["status"]
        if ev.get("status") == "deferred": c["reason"] = ev.get("message")
        meta = ev.get("meta") or {}
        if meta.get("router"): c["router"] = meta["router"]
        if meta.get("transport"): c["transport"] = meta["transport"]
        if meta.get("host"): c["host"] = meta["host"]
        if meta.get("ip"): c["ip"] = meta["ip"]
        if meta.get("port"): c["port"] = meta["port"]
        if meta.get("tls"): c["tls"] = meta["tls"]
        if meta.get("size"): c["size"] = meta["size"]
        if meta.get("reply"): c["reply"] = meta["reply"]
        self.qid_cache[qid] = c
        # Bound cache size (drop oldest arbitrary if exceeded)
        if len(self.qid_cache) > self.max_qid_cache:
            self.qid_cache.pop(next(iter(self.qid_cache)))

    def _flush_qid(self, qid: str) -> Optional[Dict]:
        c = self.qid_cache.pop(qid, None)
        if not c:
            return None
        # Compose message string with enriched meta (without changing backend schema)
        parts = []
        if c.get("reason"): parts.append(f"reason={c['reason']}")
        if c.get("router"): parts.append(f"R={c['router']}")
        if c.get("transport"): parts.append(f"T={c['transport']}")
        if c.get("host") or c.get("ip"):
            host = c.get("host") or ""
            ip = c.get("ip") or ""
            parts.append(f"H={host} [{ip}]")
        if c.get("tls"): parts.append(f"X={c['tls']}")
        if c.get("size"): parts.append(f"S={c['size']}")
        if c.get("reply"): parts.append(f"C=\"{c['reply']}\"")
        msg = "; ".join(parts) if parts else None
        return {
            "server_name": self.cfg.get("server_name"),
            "kind": "mainlog",
            "timestamp": c.get("last_ts") or c.get("first_ts"),
            "sender": c.get("sender"),
            "recipient": c.get("recipient"),
            "status": c.get("status"),
            "message": msg,
            "message_id": c.get("message_id"),
        }

    def _flush_timeouts(self) -> List[Dict]:
        out: List[Dict] = []
        now = datetime.utcnow()
        expired = []
        for qid, c in self.qid_cache.items():
            try:
                last = datetime.fromisoformat(c.get("last_ts"))
            except Exception:
                # Fallback if timestamp is already ISO string with Z missing
                last = now
            if (now - last) > timedelta(seconds=self.qid_flush_seconds):
                expired.append(qid)
        for qid in expired:
            item = self._flush_qid(qid)
            if item:
                out.append(item)
        return out

    def _read_new_lines(self, path: str, offset: int) -> (List[str], int):
        lines = []
        new_offset = offset
        try:
            with open(path, "r", errors="ignore") as f:
                f.seek(offset)
                for line in f:
                    lines.append(line)
                new_offset = f.tell()
        except FileNotFoundError:
            return [], offset
        return lines, new_offset

    def run_once(self):
        batch = []
        offsets = self.state.get("offsets", {})
        for kind, path in self.cfg.get("logs", {}).items():
            off = offsets.get(path, 0)
            lines, new_off = self._read_new_lines(path, off)
            for line in lines:
                ev = self._parse_line(kind, line)
                # Skip noise-only lines for mainlog unless correlated via QID
                if kind == "mainlog":
                    if ev.get("qid"):
                        # update cache and check for completion
                        if ev.get("completed"):
                            flushed = self._flush_qid(ev["qid"])  # flush if exists
                            if flushed:
                                batch.append(flushed)
                            continue
                        self._update_qid_cache(ev)
                        continue
                    # No QID: keep only if has meaningful fields
                    if not (ev.get("sender") or ev.get("recipient") or ev.get("message_id") or ev.get("status")):
                        continue
                    batch.append(ev)
                else:
                    # rejectlog/paniclog pass-through
                    batch.append(ev)
            offsets[path] = new_off
        # Flush timeouts for pending QIDs
        batch.extend(self._flush_timeouts())
        if batch:
            headers = {"X-API-Key": self.cfg.get("api_key")}
            url = self.cfg.get("api_url")
            try:
                r = requests.post(url, json=batch, headers=headers, timeout=10)
                r.raise_for_status()
            except Exception as e:
                return
        self.state["offsets"] = offsets
        self._save_state()

    def run(self):
        interval = int(self.cfg.get("interval_seconds", 10))
        while True:
            self.run_once()
            time.sleep(interval)

if __name__ == "__main__":
    cfg_path = os.getenv("AGENT_CONFIG", "config.json")
    with open(cfg_path, "r") as f:
        cfg = json.load(f)
    Agent(cfg).run()
