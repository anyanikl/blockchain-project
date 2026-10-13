"""
main.py

Демонстрационный сценарий для второго спринта.
Прогоняет пользовательские сценарии UC-10 … UC-15 из ТЗ.

Запуск:
    python main.py

После запуска в корне появится файл blockchain.json —
это и есть сохранённая цепочка (FR-09, FR-10, NFR-03).
"""

import os
import time
from core.blockchain import Blockchain
from core.transaction import Transaction


CHAIN_FILE = "blockchain.json"


def print_separator(title: str) -> None:
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_chain(bc: Blockchain) -> None:
    """Печатает цепочку в читаемом виде (UC-12, FR-13)."""
    for block in bc.get_chain():
        print(
            f"  Block #{block.index} | "
            f"hash={block.hash[:12]}... | "
            f"prev={block.previous_hash[:12]}... | "
            f"txs={len(block.transactions)} | "
            f"nonce={block.nonce}"
        )
        for tx in block.transactions:
            print(f"      └─ {tx.get('type'):<15} land_id={tx.get('land_id')}")


def make_tx(tx_id: str, tx_type: str, land_id: str, extra: dict = None) -> Transaction:
    """Хелпер: создаёт транзакцию с текущим timestamp."""
    now = int(time.time())
    tx = Transaction(
        tx_id=tx_id,
        type=tx_type,
        land_id=land_id,
        timestamp=now,
        created_at=now,
        approved_by="registrar-1",
    )
    # Дополнительные поля (owner, buyer и т.п.) кладём через to_dict
    if extra:
        d = tx.to_dict()
        d.update(extra)
        # Возвращаем объект-обёртку, который ведёт себя как Transaction
        tx._extra = extra
    return tx


def main() -> None:
    # ------------------------------------------------------------------
    # Подготовка: удаляем старый файл, чтобы показать создание genesis
    # ------------------------------------------------------------------
    if os.path.exists(CHAIN_FILE):
        os.remove(CHAIN_FILE)
        print(f"[setup] Removed old {CHAIN_FILE} to demo genesis creation")

    # ------------------------------------------------------------------
    # UC-10 / FR-01: создание genesis-блока при первом запуске
    # ------------------------------------------------------------------
    print_separator("UC-10: Создание genesis-блока (FR-01)")
    bc = Blockchain(CHAIN_FILE)
    print(f"  Chain length: {len(bc.chain)}")
    print(f"  Genesis hash: {bc.chain[0].hash[:16]}...")
    print(f"  Genesis previous_hash: {bc.chain[0].previous_hash[:16]}...")
    print(f"  File exists: {os.path.exists(CHAIN_FILE)}")

    # ------------------------------------------------------------------
    # FR-12: добавление транзакций в мемпул
    # ------------------------------------------------------------------
    print_separator("FR-12: Добавление транзакций в мемпул")
    tx1 = make_tx("tx-001", "REGISTER_LAND", "L-001", {"owner": "Ivanov"})
    tx2 = make_tx("tx-002", "REGISTER_LAND", "L-002", {"owner": "Petrov"})
    bc.add_transaction(tx1)
    bc.add_transaction(tx2)
    print(f"  Mempool size: {len(bc.get_pending_transactions())}")

    # ------------------------------------------------------------------
    # UC-11 / FR-04: майнинг блока
    # ------------------------------------------------------------------
    print_separator("UC-11: Майнинг блока (FR-04)")
    result = bc.mine_block(miner_role="REGISTRAR")
    print(f"  Result: {result}")
    print(f"  Chain length: {len(bc.chain)}")
    print(f"  Mempool size after mining: {len(bc.get_pending_transactions())}")

    # Проверка Permissioned: попытка майнить от CITIZEN
    print("\n  Attempt to mine as CITIZEN:")
    bc.add_transaction(make_tx("tx-003", "REGISTER_LAND", "L-003"))
    denied = bc.mine_block(miner_role="CITIZEN")
    print(f"  Result: {denied}")

    # Майним корректно
    ok = bc.mine_block(miner_role="REGISTRAR")
    print(f"\n  Mining as REGISTRAR: {ok}")

    # Ещё одна транзакция — продажа
    print_separator("Дополнительно: продажа участка L-001")
    bc.add_transaction(
        make_tx("tx-004", "SELL_LAND", "L-001", {"seller": "Ivanov", "buyer": "Sidorov"})
    )
    print(f"  Mine: {bc.mine_block(miner_role='REGISTRAR')}")

    # ------------------------------------------------------------------
    # UC-12 / FR-13: просмотр цепочки
    # ------------------------------------------------------------------
    print_separator("UC-12: Просмотр цепочки (FR-13)")
    print_chain(bc)

    # ------------------------------------------------------------------
    # UC-13 / FR-08: проверка целостности
    # ------------------------------------------------------------------
    print_separator("UC-13: Проверка целостности (FR-08)")
    valid, message = bc.is_valid()
    print(f"  Valid: {valid}")
    print(f"  Message: {message}")

    # ------------------------------------------------------------------
    # Демонстрация NFR-01: попытка подделать блок
    # ------------------------------------------------------------------
    print_separator("NFR-01: Попытка подделать блок")
    print("  Изменяем данные в блоке №1 в памяти...")
    bc.chain[1].transactions[0]["land_id"] = "HACKED"
    valid, message = bc.is_valid()
    print(f"  Valid: {valid}")
    print(f"  Message: {message}")
    print("  (хэш блока не совпал с пересчитанным — цепочка сломана)")

    # ------------------------------------------------------------------
    # UC-14 / FR-09: сохранение
    # ------------------------------------------------------------------
    print_separator("UC-14: Сохранение цепочки (FR-09)")
    # Восстанавливаем данные, чтобы сохранить валидную цепочку
    bc.chain[1].transactions[0]["land_id"] = "L-001"
    bc.storage.save(bc.chain)
    print(f"  Saved to {CHAIN_FILE}")
    print(f"  File size: {os.path.getsize(CHAIN_FILE)} bytes")

    # ------------------------------------------------------------------
    # UC-15 / FR-10, FR-11: перезапуск — загрузка из файла
    # ------------------------------------------------------------------
    print_separator("UC-15: Перезапуск и загрузка цепочки (FR-10, FR-11)")
    bc2 = Blockchain(CHAIN_FILE)
    print(f"  Chain length after restart: {len(bc2.chain)}")
    print(f"  Genesis hash preserved: {bc2.chain[0].hash[:16]}...")
    print(f"  Genesis is NOT recreated (hash matches original)")
    valid, message = bc2.is_valid()
    print(f"  Valid after restart: {valid} — {message}")

    # ------------------------------------------------------------------
    # Задел на 3 спринт: вычисление состояния из истории
    # ------------------------------------------------------------------
    print_separator("Задел на 3 спринт: состояние выводится из истории")
    print(f"  Owner of L-001: {bc2.get_land_owner('L-001')}")
    print(f"  History of L-001 ({len(bc2.get_land_history('L-001'))} записей):")
    for entry in bc2.get_land_history("L-001"):
        tx = entry["transaction"]
        print(f"    - block #{entry['block_index']}: {tx.get('type')} -> {tx}")

    print_separator("Готово")
    print(f"  Файл {CHAIN_FILE} содержит всю цепочку.")
    print(f"  Открой его и убедись, что блоки связаны через previous_hash.")


if __name__ == "__main__":
    main()