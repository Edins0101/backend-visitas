from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class InMemoryCallTrackingStore:
    def __init__(self):
        self._lock = Lock()
        self._by_call_sid: dict[str, dict] = {}
        self._visit_to_call_sid: dict[str, str] = {}

    def register_call(
        self,
        call_sid: str,
        visit_id: str,
        to: str,
        resident_name: str,
        visitor_name: str,
    ) -> dict:
        now = _utc_now_iso()
        with self._lock:
            record = {
                "callSid": call_sid,
                "visitId": visit_id,
                "to": to,
                "residentName": resident_name,
                "visitorName": visitor_name,
                "callStatus": "initiated",
                "decision": None,
                "digit": None,
                "answeredBy": None,
                "duration": None,
                "from": None,
                "createdAt": now,
                "updatedAt": now,
            }
            self._by_call_sid[call_sid] = record
            self._visit_to_call_sid[visit_id] = call_sid
            return dict(record)

    def update_status(
        self,
        call_sid: str,
        visit_id: str | None,
        call_status: str,
        *,
        duration: str | None = None,
        answered_by: str | None = None,
        from_number: str | None = None,
        to_number: str | None = None,
    ) -> dict:
        now = _utc_now_iso()
        with self._lock:
            record = self._by_call_sid.get(call_sid)
            if record is None:
                record = {
                    "callSid": call_sid,
                    "visitId": visit_id or "",
                    "to": to_number or "",
                    "residentName": "",
                    "visitorName": "",
                    "callStatus": call_status,
                    "decision": None,
                    "digit": None,
                    "answeredBy": answered_by,
                    "duration": duration,
                    "from": from_number,
                    "createdAt": now,
                    "updatedAt": now,
                }
                self._by_call_sid[call_sid] = record
            else:
                record["callStatus"] = call_status
                if duration is not None:
                    record["duration"] = duration
                if answered_by is not None:
                    record["answeredBy"] = answered_by
                if from_number is not None:
                    record["from"] = from_number
                if to_number is not None:
                    record["to"] = to_number
                record["updatedAt"] = now

            if visit_id:
                record["visitId"] = visit_id
                self._visit_to_call_sid[visit_id] = call_sid

            return dict(record)

    def update_decision(
        self,
        *,
        call_sid: str | None,
        visit_id: str | None,
        decision: str,
        digit: str,
    ) -> dict | None:
        now = _utc_now_iso()
        with self._lock:
            record = None
            if call_sid:
                record = self._by_call_sid.get(call_sid)
            if record is None and visit_id:
                mapped_call_sid = self._visit_to_call_sid.get(visit_id)
                if mapped_call_sid:
                    record = self._by_call_sid.get(mapped_call_sid)

            if record is None:
                return None

            record["decision"] = decision
            record["digit"] = digit
            record["updatedAt"] = now
            if visit_id:
                record["visitId"] = visit_id
                self._visit_to_call_sid[visit_id] = record["callSid"]
            return dict(record)

    def get_by_call_sid(self, call_sid: str) -> dict | None:
        with self._lock:
            record = self._by_call_sid.get(call_sid)
            return dict(record) if record else None

    def get_by_visit_id(self, visit_id: str) -> dict | None:
        with self._lock:
            call_sid = self._visit_to_call_sid.get(visit_id)
            if not call_sid:
                return None
            record = self._by_call_sid.get(call_sid)
            return dict(record) if record else None
