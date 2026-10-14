"""
main.py — демонстрационный запуск блокчейн-реестра.
Запуск: python main.py
"""

from core.transaction import Transaction
from core.blockchain import Blockchain

def main():
    # 1. Инициализация — создаётся genesis-блок
    bc = Blockchain(storage_path="data/blockchain.json")
    print(f"Цепочка загружена: {len(bc.get_chain())} блок(ов)")
    print(f"Genesis hash: {bc.get_chain()[0].hash[:16]}...")

    # 2. Добавляем транзакцию в мемпул
    tx = Transaction(
        tx_id="tx-001",
        type="REGISTER_LAND",
        land_id="land-1",
        timestamp=1700000000,
        approved_by="REGISTRAR",
        extra={"owner": "Ivanov", "address": "Lenina 1", "area_sqm": 100.0},
    )
    print(bc.add_transaction(tx))

    # 3. Майним блок
    result = bc.mine_block("REGISTRAR")
    print(result)

    # 4. Проверяем целостность
    ok, msg = bc.is_valid()
    print(f"Валидность цепочки: {ok} — {msg}")

    # 5. Смотрим владельца участка
    print(f"Владелец land-1: {bc.get_land_owner('land-1')}")

    # 6. История участка
    print(f"История land-1: {bc.get_land_history('land-1')}")

if __name__ == "__main__":
    main()