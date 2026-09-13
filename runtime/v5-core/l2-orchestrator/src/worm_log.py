import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

_GENESIS_HASH = "0" * 64

class WORMAuditLog:
    """
    Simulates hardware-locked WORM (Write Once, Read Many) storage.
    Optimized for Intel P5800X Optane NVMe performance.
    """
    def __init__(self, log_dir: str = "/var/valo/audit/"):
        self.log_dir = Path(log_dir)
        # In simulation: create the directory if it does not exist
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.current_session_id = hashlib.sha256(str(datetime.now()).encode()).hexdigest()[:8]

    def append_event(self, role: str, action: str, metadata: dict):
        """
        Appends an immutable entry to the audit log.
        Each entry is chained to the previous one via a hash.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        log_file = self._log_file_for_today()
        previous_hash, sequence = self._read_tail_state(log_file)
        entry = {
            "sequence": sequence,
            "timestamp": timestamp,
            "session": self.current_session_id,
            "role": role,
            "action": action,
            "previous_hash": previous_hash,
            "data": metadata,
        }

        # Generate integrity hash for this entry
        entry_string = json.dumps(entry, sort_keys=True)
        entry_hash = hashlib.sha256(entry_string.encode()).hexdigest()

        log_line = f"{entry_hash} | {entry_string}\n"

        # Write to file (in production: hardware-locked NVMe)
        with open(log_file, "a") as f:
            f.write(log_line)

        print(f"[WORM] Event locked: {action} ({entry_hash[:12]})")
        return entry_hash

    def verify_integrity(self, log_file_path: str):
        """
        Verifies that no entries in the log file have been tampered with.
        """
        path = Path(log_file_path)
        if not path.exists():
            return False

        previous_hash = _GENESIS_HASH
        expected_sequence = 1
        try:
            for raw_line in path.read_text(encoding="utf-8").splitlines():
                if not raw_line.strip():
                    continue
                stored_hash, entry_json = raw_line.split(" | ", 1)
                entry = json.loads(entry_json)
                if entry.get("previous_hash", _GENESIS_HASH) != previous_hash:
                    return False
                if entry.get("sequence") != expected_sequence:
                    return False
                recomputed = hashlib.sha256(
                    json.dumps(entry, sort_keys=True).encode()
                ).hexdigest()
                if recomputed != stored_hash:
                    return False
                previous_hash = stored_hash
                expected_sequence += 1
        except Exception:
            return False
        return True

    def _log_file_for_today(self) -> Path:
        return self.log_dir / f"valo_audit_{datetime.now().strftime('%Y%m%d')}.log"

    def _read_tail_state(self, log_file: Path) -> tuple[str, int]:
        if not log_file.exists():
            return _GENESIS_HASH, 1

        lines = [line for line in log_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not lines:
            return _GENESIS_HASH, 1

        last_line = lines[-1]
        try:
            last_hash, last_json = last_line.split(" | ", 1)
            last_entry = json.loads(last_json)
        except Exception:
            return _GENESIS_HASH, len(lines) + 1

        sequence = int(last_entry.get("sequence", len(lines))) + 1
        return last_hash, sequence
