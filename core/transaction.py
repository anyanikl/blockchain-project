"""
core/transaction.py

Класс Transaction — запись об операции с земельным участком.
Реализует FR-03: хранение списка транзакций внутри блока.
"""

from typing import Dict, Any, Optional


class Transaction:
    def __init__(
        self,
        tx_id: str,
        type: str,
        land_id: Optional[str] = None,
        timestamp: Optional[int] = None,
        application_id: Optional[str] = None,
        created_at: Optional[int] = None,
        approved_by: Optional[str] = None,
    ):
        self.tx_id = tx_id
        self.application_id = application_id
        self.type = type
        self.land_id = land_id
        self.timestamp = timestamp
        self.created_at = created_at
        self.approved_by = approved_by

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tx_id": self.tx_id,
            "application_id": self.application_id,
            "type": self.type,
            "land_id": self.land_id,
            "timestamp": self.timestamp,
            "created_at": self.created_at,
            "approved_by": self.approved_by,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Transaction":
        return Transaction(
            tx_id=data["tx_id"],
            type=data["type"],
            land_id=data.get("land_id"),
            timestamp=data.get("timestamp"),
            application_id=data.get("application_id"),
            created_at=data.get("created_at"),
            approved_by=data.get("approved_by"),
        )

    def __repr__(self) -> str:
        return f"Transaction(tx_id={self.tx_id}, type={self.type}, land_id={self.land_id})"