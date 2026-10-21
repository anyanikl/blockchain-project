"""
core/blockchain.py

Класс Blockchain — цепочка связанных блоков.
Реализует:
- FR-01: создание genesis-блока при первом запуске
- FR-04: добавление блока в конец цепочки
- FR-07: хранение последовательности блоков
- FR-08: проверка целостности цепочки
- FR-12: работа с мемпулом (одобренные транзакции)
- FR-13: просмотр цепочки

Соответствует ТЗ второго спринта, п.6, п.7, п.9.
"""

import time
from typing import List, Dict, Any, Optional, Tuple

from core.block import Block
from core.transaction import Transaction
from storage.json_storage import BlockchainStorage
from core.validation import ValidationReport, ValidationError

class Blockchain:
    """
    Цепочка блоков + мемпул + слой хранения.

    Мемпул — in-memory список (решение для 2 спринта).
    На 3 спринте будет заменён на SQLite-репозиторий.
    """

    # Служебная константа: 64 нуля — previous_hash для genesis-блока
    GENESIS_PREVIOUS_HASH = "0" * 64

    def __init__(self, storage_path: str = "blockchain.json"):
        self.storage = BlockchainStorage(storage_path)
        self.pending_transactions: List[Transaction] = []  # мемпул

        # UC-15 / FR-10: пробуем загрузить сохранённую цепочку
        if self.storage.exists():
            loaded = self.storage.load()
            if loaded:
                self.chain: List[Block] = loaded
                return

        # FR-01 / UC-10: если файла нет или он пуст/повреждён —
        # создаём genesis-блок
        self.chain = [self._create_genesis_block()]
        self.storage.save(self.chain)

    # ------------------------------------------------------------------
    # Genesis
    # ------------------------------------------------------------------

    def _create_genesis_block(self) -> Block:
        """
        Создаёт первый блок цепочки (FR-01, ТЗ п.6).
        - index = 0
        - previous_hash = 64 нуля (не ссылается на другой блок)
        - содержит служебную транзакцию GENESIS
        - hash рассчитывается автоматически
        """
        now = int(time.time())

        genesis_tx = Transaction(
            tx_id="genesis-tx",
            type="GENESIS",
            land_id=None,
            timestamp=now,
            application_id=None,
            created_at=now,
            approved_by="SYSTEM",
        )

        return Block(
            index=0,
            timestamp=now,
            transactions=[genesis_tx.to_dict()],
            previous_hash=self.GENESIS_PREVIOUS_HASH,
            nonce=0,
        )

    # ------------------------------------------------------------------
    # Мемпул (FR-12)
    # ------------------------------------------------------------------

    def add_transaction(self, tx: Transaction) -> Dict[str, Any]:
        """
        Кладёт одобренную транзакцию в мемпул.
        ТЗ п.11: заявки хранятся отдельно, после одобрения
        преобразуются в транзакцию и попадают в мемпул.
        """
        self.pending_transactions.append(tx)
        return {
            "status": "success",
            "message": "Transaction added to mempool",
            "mempool_size": len(self.pending_transactions),
        }

    def get_pending_transactions(self) -> List[Transaction]:
        """Возвращает копию мемпула (FR-12)."""
        return self.pending_transactions.copy()

    # ------------------------------------------------------------------
    # Майнинг (UC-11, FR-04)
    # ------------------------------------------------------------------

    def mine_block(self, miner_role: str = "REGISTRAR") -> Dict[str, Any]:
        """
        Формирует новый блок из транзакций мемпула и добавляет в цепочку.
        ТЗ п.7, шаги 8–16.

        Только REGISTRAR может майнить (Permissioned-логика).
        """
        # Шаг 1: проверка роли
        if miner_role != "REGISTRAR":
            return {
                "status": "error",
                "message": "Only REGISTRAR can mine blocks",
            }

        # Шаг 2: проверка мемпула
        if not self.pending_transactions:
            return {
                "status": "error",
                "message": "Mempool is empty, nothing to mine",
            }

        # Шаг 3: создаём новый блок
        previous_block = self.get_latest_block()
        new_block = Block(
            index=len(self.chain),
            timestamp=int(time.time()),
            transactions=[tx.to_dict() for tx in self.pending_transactions],
            previous_hash=previous_block.hash,
            nonce=0,
        )

        # Шаг 4: добавляем в цепочку
        self.chain.append(new_block)

        # Шаг 5: очищаем мемпул
        self.pending_transactions.clear()

        # Шаг 6: сохраняем цепочку (UC-14, FR-09)
        self.storage.save(self.chain)

        return {
            "status": "success",
            "message": "Block mined and added to chain",
            "block_index": new_block.index,
            "block_hash": new_block.hash,
            "tx_count": len(new_block.transactions),
        }

    # ------------------------------------------------------------------
    # Просмотр цепочки (FR-13, UC-12)
    # ------------------------------------------------------------------

    def get_latest_block(self) -> Block:
        """Последний блок цепочки."""
        return self.chain[-1]

    def get_chain(self) -> List[Block]:
        """Возвращает всю цепочку (FR-13)."""
        return self.chain

    def get_chain_as_dicts(self) -> List[Dict[str, Any]]:
        """Цепочка в виде списка dict — для API/вывода (UC-12)."""
        return [block.to_dict() for block in self.chain]

    # ------------------------------------------------------------------
    # Проверка целостности (FR-08, UC-13, NFR-01)
    # ------------------------------------------------------------------



    def is_valid(self) -> ValidationReport:
        """
        Проверяет целостность всей цепочки (ТЗ п.9, FR-08, FR-14).

        Порядок проверки строго по ТЗ:
        1) Пересчет hash блока
        2) Сверка previous_hash с предыдущим блоком
        3) Пересчет tx_hash внутри блока (напишет напарник)

        НЕ падает на первой ошибке — собирает ВСЕ ошибки (FR-08).
        """
        report = ValidationReport()

        for i, block in enumerate(self.chain):
            # --- Шаг 1: Пересчёт хэша блока (4а) ---
            recalculated = block.calculate_hash()
            if recalculated != block.hash:
                report.add_error(ValidationError(
                    block_index=i,
                    error_type="BLOCK_HASH_MISMATCH",
                    expected=recalculated,
                    actual=block.hash,
                    description="Хэш блока не совпадает с пересчитанным",
                ))

            # --- Шаг 2: Проверка связи с предыдущим блоком (4б) ---
            if i > 0:
                previous_block = self.chain[i - 1]
                if block.previous_hash != previous_block.hash:
                    report.add_error(ValidationError(
                        block_index=i,
                        error_type="PREV_HASH_MISMATCH",
                        expected=previous_block.hash,
                        actual=block.previous_hash,
                        description="previous_hash не совпадает с хэшем предыдущего блока",
                    ))

            # --- Шаг 3: Проверка транзакций (FR-14) ---
            # TODO: Напарник напишет метод check_transactions_hashes(block) -> List[ValidationError]
            # Когда напишет, мы раскомментируем эти строки:
            # tx_errors = self.check_transactions_hashes(block)
            # for tx_err in tx_errors:
            #     report.add_error(tx_err)

        return report

    # ------------------------------------------------------------------
    # Вспомогательные методы (для 3 спринта — вычисление состояния)
    # ------------------------------------------------------------------

    def get_land_history(self, land_id: str) -> List[Dict[str, Any]]:
        """
        История всех транзакций по участку (ТЗ п.4, идея «история участка»).
        Проходит всю цепочку и фильтрует по land_id.
        """
        history = []
        for block in self.chain:
            for tx in block.transactions:
                if tx.get("land_id") == land_id:
                    history.append({
                        "block_index": block.index,
                        "block_hash": block.hash,
                        "transaction": tx,
                    })
        return history

    def get_land_owner(self, land_id: str) -> Optional[str]:
        """
        Текущий владелец участка — вычисляется из последней транзакции
        по этому участку (REGISTER_LAND или SELL_LAND).
        В блокчейне состояние выводится из истории, а не хранится.
        """
        owner = None
        for block in self.chain:
            for tx in block.transactions:
                if tx.get("land_id") != land_id:
                    continue
                if tx.get("type") == "REGISTER_LAND":
                    owner = tx.get("owner")
                elif tx.get("type") == "SELL_LAND":
                    owner = tx.get("buyer")
        return owner

    def __repr__(self) -> str:
        return (
            f"Blockchain(blocks={len(self.chain)}, "
            f"mempool={len(self.pending_transactions)}, "
            f"latest={self.get_latest_block().hash[:8]}...)"
        )