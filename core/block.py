"""
core/block.py

Класс Block — единица хранения набора транзакций в блокчейне.
Реализует:
- FR-02: хранение обязательных полей блока
- FR-05: связь с предыдущим блоком через previous_hash
- FR-06: расчёт собственного hash
- NFR-01: изменение данных блока приводит к несоответствию hash
"""

import hashlib
import json
from typing import List, Dict, Any


class Block:
    def __init__(
        self,
        index: int,
        timestamp: int,
        transactions: List[Dict[str, Any]],
        previous_hash: str,
        nonce: int = 0,
    ):
        self.index = index
        self.timestamp = timestamp
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = self.calculate_hash()

    def _normalize_transactions(self) -> List[Dict[str, Any]]:
        """
        Приводит транзакции к списку словарей для корректного JSON-хэширования.
        Поддерживает как объекты Transaction (3 спринт), так и обычные dict.
        """
        result = []
        for tx in self.transactions:
            if hasattr(tx, "to_dict"):
                result.append(tx.to_dict())
            elif isinstance(tx, dict):
                result.append(tx)
            else:
                result.append(tx)
        return result

    def calculate_hash(self) -> str:
        block_data = {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": self._normalize_transactions(),
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
        }
        block_string = json.dumps(block_data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(block_string.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": self._normalize_transactions(),
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "hash": self.hash,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Block":
        block = Block(
            index=data["index"],
            timestamp=data["timestamp"],
            transactions=data["transactions"],
            previous_hash=data["previous_hash"],
            nonce=data.get("nonce", 0),
        )
        block.hash = data["hash"]
        return block

    def __repr__(self) -> str:
        return (
            f"Block(index={self.index}, "
            f"hash={self.hash[:8]}..., "
            f"previous_hash={self.previous_hash[:8]}..., "
            f"txs={len(self.transactions)})"
        )