import json
import os
import re
import time
from datetime import datetime
from typing import Dict, List
import requests

LOG_PATTERNS = {
    "mainlog": re.compile(r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*<= (?P<recipient>\S+)|=> (?P<to>\S+).* from <(?P<from>[^>]*)>.*\bmsgid=(?P<msgid>\S+).*\bstatus=(?P<status>\S+)?"),
    "rejectlog": re.compile(r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*rejected.*<(?P<from>[^>]*)> -> (?P<recipient>\S+): (?P<error>.*)$"),
    "paniclog": re.compile(r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*$"),
}

class Agent:
    def __init__(self, cfg: Dict):
        self.cfg = cfg
        self.state_path = cfg.get("state_file", "./state.json")
        self.state = self._load_state()

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
        if kind == "mainlog":
            m = LOG_PATTERNS["mainlog"].match(line)
            if m:
                ts = datetime.strptime(m.group("ts"), "%Y-%m-%d %H:%M:%S")
                sender = m.group("from")
                recipient = m.group("recipient") or m.group("to")
                status = m.group("status")
                message_id = m.group("msgid")
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
        return {
            "server_name": self.cfg.get("server_name"),
            "kind": kind,
            "timestamp": ts.isoformat(),
            "sender": sender,
            "recipient": recipient,
            "status": status,
            "message": message,
            "message_id": message_id,
        }

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
                item = self._parse_line(kind, line)
                batch.append(item)
            offsets[path] = new_off
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
