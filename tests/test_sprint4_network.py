"""
tests/test_sprint4_network.py

Автотесты сетевого взаимодействия нод (Спринт 4).
Перед запуском должны быть запущены две ноды:
  python node.py --port 8000 --peers http://localhost:8001
  python node.py --port 8001 --peers http://localhost:8000
  pytest tests/test_sprint4_network.py -v
"""

import pytest
import requests
import copy
import time

URL_A = "http://127.0.0.1:8000"
URL_B = "http://127.0.0.1:8001"
TIMEOUT = 5


class TestNetworkPositive:
    def test_tc01_node_a_is_get(self):
        """TC-01: Нода А отвечает на GET /status с кодом 200."""
        resp = requests.get(f"{URL_A}/status", timeout=TIMEOUT)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "online"
        assert data["node_id"] == "node_8000"
        assert "chain_length" in data
        assert "genesis_hash" in data
    def test_tc02_node_b_is_get(self):
        """TC-02: Нода Б отвечает на GET /status с кодом 200."""
        resp = requests.get(f"{URL_B}/status", timeout=TIMEOUT)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "online"
        assert data["node_id"] == "node_8001"
    def test_tc03_genesis_hash_is_same(self):
        """TC-03: У обеих нод одинаковый genesis_hash."""
        status_a = requests.get(f"{URL_A}/status", timeout=TIMEOUT).json()
        status_b = requests.get(f"{URL_B}/status", timeout=TIMEOUT).json()
        assert status_a["genesis_hash"] == status_b["genesis_hash"], (
            "Genesis-блоки отличаются!")
    def test_tc04_get_blocks(self):
        """TC-04: GET /blocks возвращает массив блоков."""
        resp = requests.get(f"{URL_A}/blocks", timeout=TIMEOUT)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert "index" in data[0]
        assert "hash" in data[0]
        assert "previous_hash" in data[0]
    def test_tc05_get_block_by_index(self):
        """TC-05: GET /blocks/0 возвращает genesis-блок.
        Ожидается падение из-за отсутствия эндпоинта (BUG-006).
        """
        resp = requests.get(f"{URL_A}/blocks/0", timeout=TIMEOUT)
        assert resp.status_code == 200

    def test_tc06_mine_and_peer(self):
        """TC-06: POST /mine создаёт блок и рассылает его пирам."""
        len_b_before = requests.get(f"{URL_B}/status", timeout=TIMEOUT).json()["chain_length"]

        resp = requests.post(f"{URL_A}/mine", timeout=TIMEOUT)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "broadcast" in data

        time.sleep(0.5)
        len_b_after = requests.get(f"{URL_B}/status", timeout=TIMEOUT).json()["chain_length"]
        assert len_b_after == len_b_before + 1, (
            f"Блок не дошёл до ноды Б: было {len_b_before}, стало {len_b_after}"
        )


class TestNetworkNegative:

    def test_tc07_invalid_json(self):
        """TC-07: Битый JSON - 400 INVALID_JSON."""
        resp = requests.post(
            f"{URL_A}/receive_block",
            json={"foo": "bar"},
            timeout=TIMEOUT
        )
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "INVALID_JSON"

    def test_tc08_block_hash_mismatch(self):
        """TC-08: Подмена данных в блоке - 400 BLOCK_HASH_MISMATCH."""
        chain = requests.get(f"{URL_A}/blocks", timeout=TIMEOUT).json()
        block = copy.deepcopy(chain[0])
        block["timestamp"] = 99999  #hash старый
        resp = requests.post(f"{URL_A}/receive_block", json=block, timeout=TIMEOUT)
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "BLOCK_HASH_MISMATCH"

    def test_tc09_tx_hash_mismatch(self):
        """TC-09: Подмена tx_hash внутри транзакции - 400 TX_HASH_MISMATCH.
        Чтобы дойти до проверки транзакции, нужно пересчитать hash блока,
        иначе сработает BLOCK_HASH_MISMATCH (проверка блока идёт первой).
        """
        requests.post(f"{URL_A}/mine", timeout=TIMEOUT)
        time.sleep(0.3)

        chain = requests.get(f"{URL_A}/blocks", timeout=TIMEOUT).json()
        block = copy.deepcopy(chain[-1])

        block["transactions"][0]["tx_hash"] = "0" * 64

        import hashlib, json
        block_data_for_hash = {
            "index": block["index"],
            "timestamp": block["timestamp"],
            "transactions": block["transactions"],
            "previous_hash": block["previous_hash"],
            "nonce": block["nonce"]}
        block_str = json.dumps(block_data_for_hash, sort_keys=True, ensure_ascii=False)
        block["hash"] = hashlib.sha256(block_str.encode("utf-8")).hexdigest()

        resp = requests.post(f"{URL_A}/receive_block", json=block, timeout=TIMEOUT)
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "TX_HASH_MISMATCH"

    def test_tc10_prev_hash_mismatch(self):
        """TC-10: Неверный previous_hash - 400 PREV_HASH_MISMATCH."""
        chain = requests.get(f"{URL_A}/blocks", timeout=TIMEOUT).json()
        block = copy.deepcopy(chain[-1])
        block["previous_hash"] = "f" * 64

        # Пересчитываем hash блока
        import hashlib, json
        block_data_for_hash = {
            "index": block["index"],
            "timestamp": block["timestamp"],
            "transactions": block["transactions"],
            "previous_hash": block["previous_hash"],
            "nonce": block["nonce"]}
        block_str = json.dumps(block_data_for_hash, sort_keys=True, ensure_ascii=False)
        block["hash"] = hashlib.sha256(block_str.encode("utf-8")).hexdigest()

        resp = requests.post(f"{URL_A}/receive_block", json=block, timeout=TIMEOUT)
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "PREV_HASH_MISMATCH"

    def test_tc11_already_exists(self):
        """TC-11: Повторный приём существующего блока возвращает 200"""
        chain = requests.get(f"{URL_A}/blocks", timeout=TIMEOUT).json()
        genesis = chain[0]

        resp = requests.post(f"{URL_A}/receive_block", json=genesis, timeout=TIMEOUT)
        assert resp.status_code == 200
        msg = resp.json()["message"].lower()
        assert "already exists" in msg or "уже есть" in msg

    def test_tc12_strict_type_check(self):
        """TC-12: Неверный тип данных (index: строка вместо int) - 400."""
        chain = requests.get(f"{URL_A}/blocks", timeout=TIMEOUT).json()
        block = copy.deepcopy(chain[0])
        block["index"] = "0"

        resp = requests.post(f"{URL_A}/receive_block", json=block, timeout=TIMEOUT)
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "INVALID_JSON"