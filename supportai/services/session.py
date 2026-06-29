import time as _time
import uuid
from typing import Optional


class SessionManager:
    """Minimal session manager for the SupportAI pipeline."""

    _sessions: dict[str, dict] = {}
    _expiry_minutes: int = 60

    @classmethod
    def set_expiry(cls, minutes: int) -> None:
        cls._expiry_minutes = minutes

    @classmethod
    def active_count(cls) -> int:
        now = _time.time()
        cls._evict_expired(now)
        return len(cls._sessions)

    @classmethod
    def _evict_expired(cls, now: float | None = None) -> None:
        if now is None:
            now = _time.time()
        cutoff = now - (cls._expiry_minutes * 60)
        expired = [
            sid
            for sid, s in cls._sessions.items()
            if s.get("_last_active", now) < cutoff
        ]
        for sid in expired:
            del cls._sessions[sid]

    def _touch(self, sid: str) -> None:
        if sid in self._sessions:
            self._sessions[sid]["_last_active"] = _time.time()

    async def get_or_create(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        channel: str = "chat",
    ) -> str:
        self._evict_expired()
        if session_id and session_id in self._sessions:
            self._touch(session_id)
            return session_id
        sid = session_id or str(uuid.uuid4())
        self._sessions[sid] = {
            "user_id": user_id,
            "channel": channel,
            "message_count": 0,
            "_last_active": _time.time(),
        }
        return sid

    async def get(self, session_id: str) -> Optional[dict]:
        self._evict_expired()
        s = self._sessions.get(session_id)
        if s:
            self._touch(session_id)
        return s
