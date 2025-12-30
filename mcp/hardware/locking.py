"""Station locking mechanism for exclusive hardware access.

ADR-032: Phase 1 - Hardware Server

Provides session-based locking to prevent concurrent access to hardware
test stations. Only one session can hold a lock at a time.
"""
import threading
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class Lock:
    """Represents an active lock on a station."""
    station: str
    session_id: str
    acquired_at: float
    expires_at: float


class StationLocker:
    """Thread-safe station locking manager."""

    def __init__(self):
        self._locks: dict[str, Lock] = {}
        self._lock = threading.Lock()

    def acquire(self, station: str, session_id: str, timeout: int = 300) -> bool:
        """Acquire exclusive lock on a station.

        Args:
            station: Name of the station to lock
            session_id: Unique identifier for the session
            timeout: Lock timeout in seconds (default 5 minutes)

        Returns:
            True if lock acquired, False if station already locked
        """
        with self._lock:
            # Clean expired locks
            self._cleanup_expired()

            # Check if already locked
            if station in self._locks:
                existing = self._locks[station]
                if existing.session_id == session_id:
                    # Same session - extend lock
                    existing.expires_at = time.time() + timeout
                    return True
                return False

            # Acquire new lock
            now = time.time()
            self._locks[station] = Lock(
                station=station,
                session_id=session_id,
                acquired_at=now,
                expires_at=now + timeout
            )
            return True

    def release(self, station: str, session_id: str) -> bool:
        """Release a lock on a station.

        Args:
            station: Name of the station to unlock
            session_id: Session that holds the lock

        Returns:
            True if lock released, False if not held by this session
        """
        with self._lock:
            if station not in self._locks:
                return True  # Already unlocked

            lock = self._locks[station]
            if lock.session_id != session_id:
                return False  # Different session holds lock

            del self._locks[station]
            return True

    def is_locked(self, station: str) -> Optional[Lock]:
        """Check if a station is locked.

        Args:
            station: Name of the station to check

        Returns:
            Lock object if locked, None if available
        """
        with self._lock:
            self._cleanup_expired()
            return self._locks.get(station)

    def _cleanup_expired(self) -> None:
        """Remove expired locks (internal, called with lock held)."""
        now = time.time()
        expired = [
            station for station, lock in self._locks.items()
            if lock.expires_at < now
        ]
        for station in expired:
            del self._locks[station]

    def list_locks(self) -> list[Lock]:
        """List all active locks.

        Returns:
            List of active Lock objects
        """
        with self._lock:
            self._cleanup_expired()
            return list(self._locks.values())


# Global locker instance
locker = StationLocker()
