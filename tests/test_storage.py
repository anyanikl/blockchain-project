import json
import pytest
from storage.json_storage import BlockchainStorage

def test_load_legacy_json(tmp_path):
    """Покрывает _migrate_transactions (добавление tx_hash)."""
    file_path = str(tmp_path / "bc.json")
    legacy_data = [{
        "index": 0, "timestamp": 100, "previous_hash": "0"*64, "nonce": 0, "hash": "old",
        "transactions": [{"tx_id": "genesis-tx", "type": "GENESIS"}] # нет tx_hash
    }]
    with open(file_path, "w") as f:
        json.dump(legacy_data, f)
    
    storage = BlockchainStorage(file_path)
    chain = storage.load()
    
    # Проверяем, что миграция прошла
    tx = chain[0].transactions[0]
    tx_hash = tx.get("tx_hash") if isinstance(tx, dict) else getattr(tx, "tx_hash", None)
    assert tx_hash is not None