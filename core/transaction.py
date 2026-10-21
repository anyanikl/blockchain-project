"""
core/transaction.py

Класс Transaction — запись об операции с земельным участком.
Реализует:
- FR-03: хранение списка транзакций внутри блока
- FR-14: проверка целостности транзакций (tx_hash)
- FR-16: проверка внешнего файла (file_hash)
- FR-17: миграция данных (автоматический расчёт tx_hash при загрузке)
- ТЗ п.4: «данные участников операции» через extra-поля (owner, buyer, seller)
- Подготовка к 3 спринту: преобразование Application → Transaction

Соответствует ТЗ третьего спринта, п.6 «Структура Транзакции».
"""

import hashlib
import json
from typing import Dict, Any, Optional


class Transaction:
    _KNOWN_FIELDS = {
        "tx_id",
        "application_id",
        "type",
        "land_id",
        "timestamp",
        "created_at",
        "approved_by",
        "tx_hash",
        "file_hash",
    }

    def __init__(
        self,
        tx_id: str,
        type: str,
        land_id: Optional[str] = None,
        timestamp: Optional[int] = None,
        application_id: Optional[str] = None,
        created_at: Optional[int] = None,
        approved_by: Optional[str] = None,
        tx_hash: Optional[str] = None,
        file_hash: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ):
        self.tx_id = tx_id
        self.application_id = application_id
        self.type = type
        self.land_id = land_id
        self.timestamp = timestamp
        self.created_at = created_at
        self.approved_by = approved_by
        self.file_hash = file_hash
        self.extra = extra or {}

        if tx_hash is None:
            self.tx_hash = self.calculate_hash()
        else:
            self.tx_hash = tx_hash

    def calculate_hash(self) -> str:
        data = {
            "tx_id": self.tx_id,
            "application_id": self.application_id,
            "type": self.type,
            "land_id": self.land_id,
            "timestamp": self.timestamp,
            "created_at": self.created_at,
            "approved_by": self.approved_by,
        }

        for k, v in self.extra.items():
            if k not in self._KNOWN_FIELDS:
                data[k] = v

        data_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(data_str.encode('utf-8')).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        base = {
            "tx_id": self.tx_id,
            "application_id": self.application_id,
            "type": self.type,
            "land_id": self.land_id,
            "timestamp": self.timestamp,
            "created_at": self.created_at,
            "approved_by": self.approved_by,
            "tx_hash": self.tx_hash,
        }

        if self.file_hash is not None:
            base["file_hash"] = self.file_hash

        for k, v in self.extra.items():
            if k not in self._KNOWN_FIELDS:
                base[k] = v
        return base

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Transaction":
        extra = {k: v for k, v in data.items() if k not in Transaction._KNOWN_FIELDS}
        return Transaction(
            tx_id=data["tx_id"],
            type=data["type"],
            land_id=data.get("land_id"),
            timestamp=data.get("timestamp"),
            application_id=data.get("application_id"),
            created_at=data.get("created_at"),
            approved_by=data.get("approved_by"),
            tx_hash=data.get("tx_hash"),
            file_hash=data.get("file_hash"),
            extra=extra,
        )

    def __repr__(self) -> str:
        return (
            f"Transaction(tx_id={self.tx_id}, type={self.type}, "
            f"land_id={self.land_id}, tx_hash={self.tx_hash[:16]}...)"
        )