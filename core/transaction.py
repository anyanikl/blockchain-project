"""
core/transaction.py

Класс Transaction — запись об операции с земельным участком.
Реализует:
- FR-03: хранение списка транзакций внутри блока
- ТЗ п.4: «данные участников операции» через extra-поля (owner, buyer, seller)
- Подготовка к 3 спринту: преобразование Application → Transaction

Соответствует ТЗ второго спринта, п.4 «Основные сущности».
"""

from typing import Dict, Any, Optional


class Transaction:
    """
    Транзакция — запись об операции с земельным участком.

    Известные поля:
        tx_id          — уникальный идентификатор транзакции
        application_id — ссылка на заявку, из которой создана (может быть None)
        type           — тип операции (REGISTER_LAND, SELL_LAND, GENESIS, ...)
        land_id        — идентификатор участка (для GENESIS — None)
        timestamp      — временная метка создания транзакции
        created_at     — время подачи заявки (для аудита)
        approved_by    — кто одобрил (для аудита)

    Дополнительные поля операции (owner, buyer, seller, bank и т.п.)
    хранятся в self.extra и попадают в JSON через to_dict().
    Это позволяет расширять структуру транзакции без изменения ядра.
    """

    # Поля, которые обрабатываются явно. Всё остальное уходит в extra.
    _KNOWN_FIELDS = {
        "tx_id",
        "application_id",
        "type",
        "land_id",
        "timestamp",
        "created_at",
        "approved_by",
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
        extra: Optional[Dict[str, Any]] = None,
    ):
        self.tx_id = tx_id
        self.application_id = application_id
        self.type = type
        self.land_id = land_id
        self.timestamp = timestamp
        self.created_at = created_at
        self.approved_by = approved_by
        # Дополнительные поля операции (owner, buyer, seller, ...)
        self.extra = extra or {}

    def to_dict(self) -> Dict[str, Any]:
        """
        Сериализация в dict для JSON (FR-09).
        Известные поля + extra (owner, buyer, seller) в одной плоскости.
        """
        base = {
            "tx_id": self.tx_id,
            "application_id": self.application_id,
            "type": self.type,
            "land_id": self.land_id,
            "timestamp": self.timestamp,
            "created_at": self.created_at,
            "approved_by": self.approved_by,
        }
        base.update(self.extra)
        return base

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Transaction":
        """
        Десериализация из dict (FR-10).
        Известные поля забираем явно, всё остальное — в extra.
        """
        extra = {k: v for k, v in data.items() if k not in Transaction._KNOWN_FIELDS}
        return Transaction(
            tx_id=data["tx_id"],
            type=data["type"],
            land_id=data.get("land_id"),
            timestamp=data.get("timestamp"),
            application_id=data.get("application_id"),
            created_at=data.get("created_at"),
            approved_by=data.get("approved_by"),
            extra=extra,
        )

    def __repr__(self) -> str:
        return (
            f"Transaction(tx_id={self.tx_id}, type={self.type}, "
            f"land_id={self.land_id}, extra={self.extra})"
        )