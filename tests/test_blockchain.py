"""
tests/test_blockchain.py
Проверка валидности цепочки: a, b, c.
"""

import pytest

from core.blockchain import Blockchain
from core.transaction import Transaction
from core.validation import ValidationReport

@pytest.fixture
def tmp_path_bc(tmp_path):
    return str(tmp_path / "bc.json")

@pytest.fixture
def bc(tmp_path_bc):
    return Blockchain(storage_path=tmp_path_bc)

@pytest.fixture
def sample_tx():
    return Transaction(
        tx_id="tx-001",
        type="REGISTER_LAND",
        land_id="land-1",
        timestamp=1700000000,
        extra={"owner": "Ivanov"},
    )


class TestChainValidation:
    def test_valid_chain(self, bc, sample_tx):
        """a+b+c: корректная цепочка → is_valid True."""
        bc.add_transaction(sample_tx)
        bc.mine_block("REGISTRAR")
        report = bc.is_valid()
        assert isinstance(report, ValidationReport)
        assert report.is_valid is True
        assert report.errors == []

    def test_block_hash_mismatch(self, bc, sample_tx):
        """a: подмена содержимого блока → BLOCK_HASH_MISMATCH."""
        bc.add_transaction(sample_tx)
        bc.mine_block("REGISTRAR")
        bc.chain[1].transactions[0]["owner"] = "Hacker"
        report = bc.is_valid()
        assert report.is_valid is False
        assert any(e.error_type == "BLOCK_HASH_MISMATCH" for e in report.errors)

    def test_prev_hash_mismatch(self, bc):
        """b: разрыв previous_hash → PREV_HASH_MISMATCH."""
        for i in range(2):
            bc.add_transaction(Transaction(tx_id=f"t{i}", type="REGISTER", land_id=f"l{i}"))
            bc.mine_block("REGISTRAR")
        bc.chain[2].previous_hash = "f" * 64
        report = bc.is_valid()
        assert report.is_valid is False
        assert any(e.error_type == "PREV_HASH_MISMATCH" for e in report.errors)

    def test_chain_reaches_genesis(self, bc):
        """b: от конца цепочки доходим до genesis без разрывов."""
        for i in range(5):
            bc.add_transaction(Transaction(tx_id=f"t{i}", type="REGISTER", land_id=f"l{i}"))
            bc.mine_block("REGISTRAR")
        # каждая связь валидна
        for i in range(len(bc.chain) - 1, 0, -1):
            assert bc.chain[i].previous_hash == bc.chain[i - 1].hash
        # genesis ни на что не ссылается
        assert bc.chain[0].previous_hash == "0" * 64
        assert bc.is_valid().is_valid is True

    def test_tx_hash_mismatch(self, bc, sample_tx):
        """c: подмена tx_hash → TX_HASH_MISMATCH."""
        bc.add_transaction(sample_tx)
        bc.mine_block("REGISTRAR")
        tx = bc.chain[1].transactions[0]
        # подменяем данные, но оставляем старый tx_hash
        if isinstance(tx, dict):
            tx["land_id"] = "hacked"
            tx["tx_hash"] = "deadbeef" * 8
        else:
            tx.land_id = "hacked"
            tx.tx_hash = "deadbeef" * 8
        report = bc.is_valid()
        assert report.is_valid is False
        assert any(e.error_type == "TX_HASH_MISMATCH" for e in report.errors)

    def test_tx_error_has_index(self, bc):
        """c + FR-15: ошибка указывает индекс транзакции."""
        for i in range(3):
            bc.add_transaction(Transaction(tx_id=f"t{i}", type="REGISTER", land_id=f"l{i}"))
        bc.mine_block("REGISTRAR")
        bc.chain[1].transactions[1]["land_id"] = "hacked"
        report = bc.is_valid()
        tx_errors = [e for e in report.errors if e.error_type == "TX_HASH_MISMATCH"]
        assert len(tx_errors) == 1
        assert tx_errors[0].block_index == 1
        assert tx_errors[0].tx_index == 1


class TestMempoolAndMining:
    def test_mempool_operations(self, bc, sample_tx):
        """Покрывает add_transaction и get_pending_transactions."""
        assert len(bc.get_pending_transactions()) == 0
        bc.add_transaction(sample_tx)
        assert len(bc.get_pending_transactions()) == 1

    def test_mine_success_and_errors(self, bc, sample_tx):
        """Покрывает успешный майнинг и ошибки (роль, пустой мемпул)."""
        # Ошибка: не та роль
        assert bc.mine_block("USER")["status"] == "error"
        
        # Ошибка: пустой мемпул
        assert bc.mine_block("REGISTRAR")["status"] == "error"

        # Успех
        bc.add_transaction(sample_tx)
        result = bc.mine_block("REGISTRAR")
        assert result["status"] == "success"
        assert result["tx_count"] == 1


class TestAuditMethods:
    def test_get_land_owner_and_history(self, bc):
        """Покрывает get_land_history и get_land_owner (включая SELL_LAND)."""
        # 1. Регистрация
        bc.add_transaction(Transaction(tx_id="t1", type="REGISTER_LAND", land_id="l1", extra={"owner": "Ivanov"}))
        bc.mine_block("REGISTRAR")
        assert bc.get_land_owner("l1") == "Ivanov"
        
        # 2. Продажа
        bc.add_transaction(Transaction(tx_id="t2", type="SELL_LAND", land_id="l1", extra={"buyer": "Petrov"}))
        bc.mine_block("REGISTRAR")
        assert bc.get_land_owner("l1") == "Petrov"
        
        # 3. Неизвестный участок
        assert bc.get_land_owner("unknown") is None
        
        # 4. История
        history = bc.get_land_history("l1")
        assert len(history) == 2
        assert history[0]["block_index"] == 1
        assert history[1]["block_index"] == 2


class TestPersistence:
    def test_load_saved_chain(self, tmp_path):
        path = str(tmp_path / "bc.json")
        bc1 = Blockchain(storage_path=path)
        bc1.add_transaction(Transaction(tx_id="t1", type="REGISTER", land_id="l1"))
        bc1.mine_block("REGISTRAR")
        
        bc2 = Blockchain(storage_path=path)  # ← загрузка
        assert len(bc2.get_chain()) == 2

    def test_get_chain_as_dicts(self, bc, sample_tx):
        """170"""
        bc.add_transaction(sample_tx)
        bc.mine_block("REGISTRAR")
        dicts = bc.get_chain_as_dicts()
        assert isinstance(dicts[0], dict)
        assert dicts[0]["index"] == 0

    def test_audit_with_object_transactions(self, tmp_path):
        """222, 250, 267-271: транзакции после миграции — объекты."""
        import json
        path = str(tmp_path / "bc.json")
        # Старый JSON → после load() транзакции станут объектами
        legacy = [
            {"index": 0, "timestamp": 1,
            "transactions": [{"tx_id": "g", "type": "GENESIS"}],
            "previous_hash": "0"*64, "nonce": 0, "hash": "h0"},
            {"index": 1, "timestamp": 2,
            "transactions": [{"tx_id": "t1", "type": "REGISTER_LAND",
                            "land_id": "l1", "owner": "Ivanov"}],
            "previous_hash": "h0", "nonce": 0, "hash": "h1"},
        ]
        with open(path, "w") as f:
            json.dump(legacy, f)

        bc = Blockchain(storage_path=path)
        # Теперь транзакции — объекты. Проверяем ветки.
        assert bc.get_land_history("l1") is not None     # 222
        assert bc.get_land_owner("l1") is not None       # 250, 267-271