"""
storage/json_storage.py

Класс BlockchainStorage — слой хранения цепочки в JSON.
Реализует:
- FR-09: сохранение цепочки в JSON
- FR-10: загрузка цепочки при запуске
- FR-11: сохранение после перезапуска
- FR-17: миграция данных (добавление tx_hash)
- NFR-03: структурированный JSON
- NFR-09: резервная копия перед миграцией
"""

import json
import os
import shutil
from typing import List, TYPE_CHECKING

from core.transaction import Transaction

if TYPE_CHECKING:
    from core.block import Block


class BlockchainStorage:
    def __init__(self, file_path: str = "blockchain.json"):
        self.file_path = file_path

    def exists(self) -> bool:
        return os.path.exists(self.file_path)

    def save(self, chain: List["Block"]) -> None:
        """
        Перезаписывает файл актуальным состоянием цепочки (FR-09).
        Использует overwrite — ТЗ (п.10, шаг 23) требует актуальное состояние.
        """
        data = []
        for block in chain:
            block_dict = block.to_dict()
            # Гарантируем, что транзакции — это словари, а не объекты
            if "transactions" in block_dict:
                block_dict["transactions"] = [
                    tx.to_dict() if hasattr(tx, "to_dict") else tx
                    for tx in block_dict["transactions"]
                ]
            data.append(block_dict)

        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load(self) -> List["Block"]:
        from core.block import Block

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            chain = [Block.from_dict(b) for b in data]

            chain = self._migrate_transactions(chain)

            return chain
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return []

    def _migrate_transactions(self, chain: List["Block"]) -> List["Block"]:
        needs_migration = any(
            not getattr(tx, "tx_hash", None)
            for block in chain
            for tx in block.transactions
        )

        if not needs_migration:
            return chain

        backup_path = self.file_path + ".bak"
        try:
            shutil.copy2(self.file_path, backup_path)
        except OSError:
            return chain

        for i, block in enumerate(chain):
            block_changed = False

            for j, tx in enumerate(block.transactions):
                if isinstance(tx, dict):
                    tx = Transaction.from_dict(tx)
                    block.transactions[j] = tx

                if not getattr(tx, "tx_hash", None):
                    tx.tx_hash = tx.calculate_hash()
                    block_changed = True

            if block_changed:
                block.hash = block.calculate_hash()
                if i + 1 < len(chain):
                    chain[i + 1].previous_hash = block.hash

        self.save(chain)
        return chain