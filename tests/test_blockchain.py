"""
tests/test_blockchain.py

Тесты для блокчейн-реестра земельных участков.
Спринт 2: блоки, цепочка, хэши, JSON-хранение.

Покрытие:
- FR-01..FR-13
- NFR-01..NFR-05
- UC-10..UC-15
"""

import json
import os
import tempfile
import time
import hashlib

import pytest

from core.block import Block
from core.blockchain import Blockchain
from storage.json_storage import BlockchainStorage
from core.transaction import Transaction


# Фикстуры 

@pytest.fixture
def tmp_storage_path(tmp_path):
    """Временный путь к JSON-файлу, изолированный для каждого теста."""
    return str(tmp_path / "blockchain.json")


@pytest.fixture
def fresh_blockchain(tmp_storage_path):
    """Пустой блокчейн (только genesis)."""
    return Blockchain(storage_path=tmp_storage_path)


@pytest.fixture
def sample_transaction():
    return Transaction(
        tx_id="tx-001",
        type="REGISTER_LAND",
        land_id="land-1",
        timestamp=1700000000,
        created_at=1700000000,
        approved_by="REGISTRAR",
        extra={"owner": "Ivanov", "address": "Lenina 1", "area_sqm": 100.0},
    )


# TC-01: genesis 

class TestGenesis:
    def test_genesis_created_on_first_run(self, fresh_blockchain):
        """FR-01 / UC-10: создание genesis при отсутствии файла."""
        chain = fresh_blockchain.get_chain()
        assert len(chain) == 1
        genesis = chain[0]
        assert genesis.index == 0
        assert genesis.previous_hash == "0" * 64
        assert genesis.transactions[0]["type"] == "GENESIS"
        assert len(genesis.hash) == 64

    def test_genesis_not_recreated_on_second_run(self, tmp_storage_path):
        """ТЗ п.6.7: genesis не создаётся заново при повторном запуске."""
        bc1 = Blockchain(storage_path=tmp_storage_path)
        genesis_hash = bc1.get_chain()[0].hash
        bc2 = Blockchain(storage_path=tmp_storage_path)
        assert bc2.get_chain()[0].hash == genesis_hash
        assert len(bc2.get_chain()) == 1

    def test_genesis_hash_is_deterministic(self):
        """Хэш genesis должен быть воспроизводим при одинаковых полях."""
        b1 = Block(0, 1000, [{"type": "GENESIS"}], "0" * 64, 0)
        b2 = Block(0, 1000, [{"type": "GENESIS"}], "0" * 64, 0)
        assert b1.hash == b2.hash


# TC-03: расчёт хэша 

class TestHashCalculation:
    def test_calculate_hash_matches_manual(self):
        """FR-06: hash = SHA-256 от детерминированного JSON."""
        block = Block(1, 12345, [{"type": "TEST"}], "abc", 0)
        expected_data = {
            "index": 1,
            "timestamp": 12345,
            "transactions": [{"type": "TEST"}],
            "previous_hash": "abc",
            "nonce": 0,
        }
        expected = hashlib.sha256(
            json.dumps(expected_data, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        assert block.calculate_hash() == expected

    def test_hash_changes_on_data_change(self):
        """NFR-01: изменение любого поля меняет хэш."""
        b1 = Block(1, 100, [{"a": 1}], "prev", 0)
        b2 = Block(1, 100, [{"a": 2}], "prev", 0)
        assert b1.hash != b2.hash

    def test_nonce_affects_hash(self):
        """ТЗ п.5: nonce участвует в расчёте хэша."""
        b1 = Block(1, 100, [], "prev", nonce=0)
        b2 = Block(1, 100, [], "prev", nonce=1)
        assert b1.hash != b2.hash


#  TC-04, TC-05, TC-14, TC-17: целостность 

class TestIntegrity:
    def test_valid_chain(self, fresh_blockchain, sample_transaction):
        fresh_blockchain.add_transaction(sample_transaction)
        fresh_blockchain.mine_block("REGISTRAR")
        ok, msg = fresh_blockchain.is_valid()
        assert ok is True
        assert msg == "Chain is valid"

    def test_tampered_transaction_detected(self, fresh_blockchain, sample_transaction):
        """NFR-01 / FR-08: подмена данных ломает цепочку."""
        fresh_blockchain.add_transaction(sample_transaction)
        fresh_blockchain.mine_block("REGISTRAR")
        fresh_blockchain.chain[1].transactions[0]["land_id"] = "hacked"
        ok, msg = fresh_blockchain.is_valid()
        assert ok is False
        assert "hash mismatch" in msg

    def test_broken_previous_hash_detected(self, fresh_blockchain, sample_transaction):
        """FR-05 / FR-08: разрыв связи previous_hash."""
        fresh_blockchain.add_transaction(sample_transaction)
        fresh_blockchain.mine_block("REGISTRAR")
        fresh_blockchain.chain[1].previous_hash = "f" * 64
        ok, msg = fresh_blockchain.is_valid()
        assert ok is False

    def test_genesis_previous_hash_invariant(self, fresh_blockchain):
        """ТЗ п.6.4: previous_hash genesis = 64 нуля."""
        fresh_blockchain.chain[0].previous_hash = "abc"
        ok, msg = fresh_blockchain.is_valid()
        assert ok is False, "Ожидается провал проверки genesis-инварианта"

    def test_index_monotonicity(self, fresh_blockchain, sample_transaction):
        """ТЗ п.5: index определяет положение блока."""
        fresh_blockchain.add_transaction(sample_transaction)
        fresh_blockchain.mine_block("REGISTRAR")
        fresh_blockchain.chain[1].index = 99
        ok, msg = fresh_blockchain.is_valid()
        assert ok is False, "Ожидается провал проверки монотонности index"


# TC-06, TC-07, TC-08, TC-09: мемпул и майнинг 

class TestMempoolAndMining:
    def test_add_transaction_to_mempool(self, fresh_blockchain, sample_transaction):
        result = fresh_blockchain.add_transaction(sample_transaction)
        assert result["status"] == "success"
        assert result["mempool_size"] == 1
        assert fresh_blockchain.get_pending_transactions() == [sample_transaction]

    def test_mine_block_success(self, fresh_blockchain, sample_transaction):
        fresh_blockchain.add_transaction(sample_transaction)
        result = fresh_blockchain.mine_block("REGISTRAR")
        assert result["status"] == "success"
        assert len(fresh_blockchain.get_chain()) == 2
        assert fresh_blockchain.get_pending_transactions() == []
        assert fresh_blockchain.chain[1].previous_hash == fresh_blockchain.chain[0].hash

    def test_mine_block_forbidden_for_user(self, fresh_blockchain, sample_transaction):
        fresh_blockchain.add_transaction(sample_transaction)
        result = fresh_blockchain.mine_block("USER")
        assert result["status"] == "error"
        assert len(fresh_blockchain.get_chain()) == 1

    def test_mine_empty_mempool(self, fresh_blockchain):
        result = fresh_blockchain.mine_block("REGISTRAR")
        assert result["status"] == "error"
        assert "empty" in result["message"].lower()

    def test_mine_clears_mempool(self, fresh_blockchain):
        for i in range(3):
            fresh_blockchain.add_transaction(
                Transaction(tx_id=f"tx-{i}", type="REGISTER_LAND", land_id=f"land-{i}")
            )
        fresh_blockchain.mine_block("REGISTRAR")
        assert fresh_blockchain.get_pending_transactions() == []


#  TC-10, TC-11, TC-12: хранение 

class TestStorage:
    def test_round_trip(self, tmp_storage_path, sample_transaction):
        """FR-09 / FR-10: save → load без потерь."""
        bc1 = Blockchain(storage_path=tmp_storage_path)
        bc1.add_transaction(sample_transaction)
        bc1.mine_block("REGISTRAR")

        bc2 = Blockchain(storage_path=tmp_storage_path)
        assert len(bc2.get_chain()) == 2
        for i in range(2):
            assert bc2.chain[i].index == bc1.chain[i].index
            assert bc2.chain[i].hash == bc1.chain[i].hash
            assert bc2.chain[i].previous_hash == bc1.chain[i].previous_hash
            assert bc2.chain[i].transactions == bc1.chain[i].transactions
            assert bc2.chain[i].nonce == bc1.chain[i].nonce

    def test_corrupted_json_handling(self, tmp_storage_path):
        """NFR-02: поведение при повреждённом файле."""
        with open(tmp_storage_path, "w", encoding="utf-8") as f:
            f.write("{not valid json")
        bc = Blockchain(storage_path=tmp_storage_path)
        # Текущее поведение: создаётся новый genesis.
        # Идеальное: сообщение об ошибке + бэкап.
        assert len(bc.get_chain()) == 1
        assert bc.get_chain()[0].index == 0

    def test_block_from_dict_without_hash(self):
        """TC-12: отсутствие ключа hash."""
        data = {
            "index": 1,
            "timestamp": 100,
            "transactions": [],
            "previous_hash": "abc",
            "nonce": 0,
        }
        with pytest.raises(KeyError):
            Block.from_dict(data)

    def test_storage_file_created(self, tmp_storage_path):
        Blockchain(storage_path=tmp_storage_path)
        assert os.path.exists(tmp_storage_path)

    def test_storage_json_structure(self, tmp_storage_path):
        """NFR-03: структурированный JSON."""
        bc = Blockchain(storage_path=tmp_storage_path)
        bc.add_transaction(Transaction(tx_id="t1", type="REGISTER_LAND", land_id="l1"))
        bc.mine_block("REGISTRAR")
        with open(tmp_storage_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, list)
        assert len(data) == 2
        for block in data:
            for key in ("index", "timestamp", "transactions", "previous_hash", "nonce", "hash"):
                assert key in block


#  TC-13: Transaction 

class TestTransaction:
    def test_extra_does_not_override_known_fields(self):
        """Баг №6: extra не должен перезаписывать tx_id."""
        tx = Transaction(
            tx_id="real-id",
            type="REGISTER_LAND",
            extra={"tx_id": "fake-id", "owner": "Ivanov"},
        )
        d = tx.to_dict()
        assert d["tx_id"] == "real-id", "extra не должен перезаписывать tx_id"
        assert d["owner"] == "Ivanov"

    def test_from_dict_round_trip(self):
        tx = Transaction(
            tx_id="t1",
            type="SELL_LAND",
            land_id="l1",
            timestamp=100,
            extra={"seller": "A", "buyer": "B"},
        )
        d = tx.to_dict()
        tx2 = Transaction.from_dict(d)
        assert tx2.tx_id == tx.tx_id
        assert tx2.type == tx.type
        assert tx2.extra == tx.extra


#  TC-15, TC-16: аудит 

class TestAudit:
    def test_get_land_owner_after_sell(self, fresh_blockchain):
        fresh_blockchain.add_transaction(
            Transaction(tx_id="t1", type="REGISTER_LAND", land_id="l1", extra={"owner": "Ivanov"})
        )
        fresh_blockchain.mine_block("REGISTRAR")
        fresh_blockchain.add_transaction(
            Transaction(tx_id="t2", type="SELL_LAND", land_id="l1", extra={"seller": "Ivanov", "buyer": "Petrov"})
        )
        fresh_blockchain.mine_block("REGISTRAR")
        assert fresh_blockchain.get_land_owner("l1") == "Petrov"

    def test_get_land_history(self, fresh_blockchain):
        fresh_blockchain.add_transaction(
            Transaction(tx_id="t1", type="REGISTER_LAND", land_id="l1", extra={"owner": "Ivanov"})
        )
        fresh_blockchain.mine_block("REGISTRAR")
        history = fresh_blockchain.get_land_history("l1")
        assert len(history) == 1
        assert history[0]["transaction"]["type"] == "REGISTER_LAND"
        assert "block_index" in history[0]
        assert "block_hash" in history[0]

    def test_get_land_owner_returns_none_for_unknown(self, fresh_blockchain):
        assert fresh_blockchain.get_land_owner("unknown") is None


#  Интеграционный сценарий 

class TestIntegration:
    def test_full_scenario(self, tmp_storage_path):
        """UC-10 → UC-11 → UC-14 → UC-15: полный цикл."""
        # 1. Запуск → genesis
        bc = Blockchain(storage_path=tmp_storage_path)
        assert len(bc.get_chain()) == 1

        # 2. Подача и одобрение заявки → транзакция в мемпуле
        tx = Transaction(
            tx_id="tx-1",
            type="REGISTER_LAND",
            land_id="land-1",
            extra={"owner": "Ivanov"},
        )
        bc.add_transaction(tx)

        # 3. Майнинг
        result = bc.mine_block("REGISTRAR")
        assert result["status"] == "success"

        # 4. Проверка целостности
        ok, _ = bc.is_valid()
        assert ok

        # 5. Перезапуск → загрузка
        bc2 = Blockchain(storage_path=tmp_storage_path)
        assert len(bc2.get_chain()) == 2
        assert bc2.get_chain()[1].hash == bc.chain[1].hash

        # 6. Проверка целостности после загрузки
        ok2, _ = bc2.is_valid()
        assert ok2