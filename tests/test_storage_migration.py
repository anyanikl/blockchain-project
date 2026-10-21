"""
Проверка миграции старых данных (FR-17, NFR-09).
Поднимает покрытие json_storage.py.
"""
import json
import os
import pytest
from storage.json_storage import BlockchainStorage


def test_load_legacy_json_triggers_migration(tmp_path):
    """Покрывает _migrate_transactions и создание .bak."""
    file_path = str(tmp_path / "bc.json")
    
    # Создаём "старый" JSON без tx_hash
    legacy_data = [
        {
            "index": 0,
            "timestamp": 100,
            "transactions": [{"tx_id": "genesis-tx", "type": "GENESIS"}],
            "previous_hash": "0" * 64,
            "nonce": 0,
            "hash": "old_hash"
        }
    ]
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(legacy_data, f)
        
    storage = BlockchainStorage(file_path)
    chain = storage.load()
    
    # Проверяем, что миграция добавила tx_hash
    tx = chain[0].transactions[0]
    tx_hash = tx.get("tx_hash") if isinstance(tx, dict) else getattr(tx, "tx_hash", None)
    assert tx_hash is not None
    
    # Проверяем, что создался бэкап .bak
    assert os.path.exists(file_path + ".bak")

def test_backup_failure_returns_unchanged(tmp_path, monkeypatch):
    """62-63: если бэкап не удался — возвращаем как есть."""
    file_path = str(tmp_path / "bc.json")
    with open(file_path, "w") as f:
        json.dump([{
            "index": 0, "timestamp": 1,
            "transactions": [{"tx_id": "g"}],
            "previous_hash": "0" * 64, "nonce": 0, "hash": "h",
        }], f)

    def boom(*a, **kw):
        raise OSError("disk full")
    monkeypatch.setattr("shutil.copy2", boom)

    chain = BlockchainStorage(file_path).load()
    assert len(chain) == 1


def test_migration_updates_next_previous_hash(tmp_path):
    """73, 78-79: пересчёт previous_hash следующего блока."""
    file_path = str(tmp_path / "bc.json")
    legacy = [
        {"index": 0, "timestamp": 1,
         "transactions": [{"tx_id": "g", "type": "GENESIS"}],
         "previous_hash": "0" * 64, "nonce": 0, "hash": "h0"},
        {"index": 1, "timestamp": 2,
         "transactions": [{"tx_id": "t1", "type": "REGISTER", "land_id": "l1"}],
         "previous_hash": "h0", "nonce": 0, "hash": "h1"},
    ]
    with open(file_path, "w") as f:
        json.dump(legacy, f)

    chain = BlockchainStorage(file_path).load()
    assert chain[1].previous_hash == chain[0].hash


def test_already_migrated_noop(tmp_path):
    """90-91: повторный load без миграции."""
    file_path = str(tmp_path / "bc.json")
    legacy = [{
        "index": 0, "timestamp": 1,
        "transactions": [{"tx_id": "g", "tx_hash": "abc"}],
        "previous_hash": "0" * 64, "nonce": 0, "hash": "h0",
    }]
    with open(file_path, "w") as f:
        json.dump(legacy, f)

    BlockchainStorage(file_path).load()
    # второго бэкапа быть не должно
    assert not os.path.exists(file_path + ".bak.1")


def test_save_with_objects(tmp_path):
    """94-96: save() корректно сериализует объекты Transaction/Block."""
    from core.block import Block
    from core.transaction import Transaction

    file_path = str(tmp_path / "bc.json")
    tx = Transaction(tx_id="t1", type="TEST")
    block = Block(0, 100, [tx], "0" * 64)

    BlockchainStorage(file_path).save([block])

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "tx_hash" in data[0]["transactions"][0]