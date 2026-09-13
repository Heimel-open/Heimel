"""
ACS Attestation Store v0.1
Immutable hash-chained log of all receipts.
"""

import json
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Any

class ACSHashLog:
    """Immutable hash-chained log for attestation receipts."""

    def __init__(self):
        self.chain = []
        self.previous_hash = "0" * 64

    def append(self, receipt: Dict[str, Any]) -> Dict[str, Any]:
        entry = {
            "receipt": receipt,
            "previous_hash": self.previous_hash,
            "block_timestamp": datetime.now(timezone.utc).isoformat()
        }

        entry_data = json.dumps(entry, sort_keys=True, ensure_ascii=False)
        entry_hash = hashlib.sha256(entry_data.encode()).hexdigest()

        entry["entry_hash"] = entry_hash
        self.chain.append(entry)
        self.previous_hash = entry_hash

        return entry

    def verify_chain(self) -> bool:
        for i in range(1, len(self.chain)):
            if self.chain[i]["previous_hash"] != self.chain[i - 1]["entry_hash"]:
                return False
        return True

    def get_chain(self) -> List[Dict]:
        return self.chain

    def get_length(self) -> int:
        return len(self.chain)
