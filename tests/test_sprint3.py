"""
- поиск точки разрыва (ValidationReport)
- проверка внешнего файла (FileService)
"""

import hashlib
import pytest

from core.blockchain import Blockchain
from core.transaction import Transaction
from core.validation import ValidationReport
from services.file_service import FileService

# Фикстуры
@pytest.fixture
def tmp_storage_path(tmp_path):
    return str(tmp_path / "blockchain.json")


@pytest.fixture
def bc_with_two_blocks(tmp_storage_path):
    # Цепочка из 2 блоков (genesis + 1 с транзакцией)
    bc = Blockchain(storage_path=tmp_storage_path)
    tx = Transaction(
        tx_id="tx-001",
        type="REGISTER_LAND",
        land_id="land-1",
        timestamp=1700000000,
        approved_by="REGISTRAR",
        extra={"owner": "Ivanov", "address": "Lenina 1", "area_sqm": 100.0},
    )
    bc.add_transaction(tx)
    bc.mine_block("REGISTRAR")
    return bc


@pytest.fixture
def bc_with_three_blocks(tmp_storage_path):
    # Цепочка из 3 блоков
    bc = Blockchain(storage_path=tmp_storage_path)
    for i in range(2):
        tx = Transaction(
            tx_id=f"tx-{i}",
            type="REGISTER_LAND",
            land_id=f"land-{i}",
            timestamp=1700000000 + i,
            approved_by="REGISTRAR",
            extra={"owner": f"Owner{i}"},
        )
        bc.add_transaction(tx)
        bc.mine_block("REGISTRAR")
    return bc



# Поиск точки разрыва (FR-15, FR-18)
class TestBreakPointDetection:
    def test_tc02_tampered_transaction_detected(self, bc_with_two_blocks):
        # ТК-02: подмена данных в транзакции на TX_HASH_MISMATCH.
        bc_with_two_blocks.chain[1].transactions[0]["owner"] = "Hacker"
        report = bc_with_two_blocks.is_valid()

        assert report.is_valid is False
        assert len(report.errors) >= 1

        tx_errors = [e for e in report.errors if e.error_type == "TX_HASH_MISMATCH"]
        assert len(tx_errors) >= 1
        assert tx_errors[0].block_index == 1
        assert tx_errors[0].tx_index == 0

    def test_tc03_tampered_tx_hash_detected(self, bc_with_two_blocks):
        # ТК-03: подмена tx_hash на TX_HASH_MISMATCH.
        bc_with_two_blocks.chain[1].transactions[0]["tx_hash"] = "0" * 64
        report = bc_with_two_blocks.is_valid()

        assert report.is_valid is False
        assert any(
            e.error_type == "TX_HASH_MISMATCH" and e.block_index == 1
            for e in report.errors
        )

    def test_tc04_tampered_block_timestamp_detected(self, bc_with_two_blocks):
        # ТК-04: подмена timestamp блока на BLOCK_HASH_MISMATCH.
        bc_with_two_blocks.chain[1].timestamp = 0
        report = bc_with_two_blocks.is_valid()

        assert report.is_valid is False
        assert any(
            e.error_type == "BLOCK_HASH_MISMATCH" and e.block_index == 1
            for e in report.errors
        )

    def test_tc05_broken_previous_hash_detected(self, bc_with_three_blocks):
        # ТК-05: разрыв previous_hash на PREV_HASH_MISMATCH в блоке 2.
        bc_with_three_blocks.chain[2].previous_hash = "f" * 64
        report = bc_with_three_blocks.is_valid()

        assert report.is_valid is False
        assert any(
            e.error_type == "PREV_HASH_MISMATCH" and e.block_index == 2
            for e in report.errors
        )

    def test_tc06_multiple_errors_collected(self, bc_with_three_blocks):
        # ТК-06: несколько ошибок, все собираются в отчёт.
        bc_with_three_blocks.chain[1].transactions[0]["owner"] = "Hacker"
        bc_with_three_blocks.chain[2].previous_hash = "f" * 64

        report = bc_with_three_blocks.is_valid()

        assert report.is_valid is False
        assert len(report.errors) >= 2

        types = {e.error_type for e in report.errors}
        assert "TX_HASH_MISMATCH" in types
        assert "PREV_HASH_MISMATCH" in types

    def test_tc07_genesis_tampered_detected(self, bc_with_two_blocks):
        # ТК-07: подмена genesis-блока, ожидается ошибка в блоке 0.
        bc_with_two_blocks.chain[0].timestamp = 0
        report = bc_with_two_blocks.is_valid()

        assert report.is_valid is False
        assert any(e.block_index == 0 for e in report.errors)

    def test_report_print_does_not_crash(self, bc_with_two_blocks, capsys):
        # NFR-08: print_report() работает и для валидной, и для невалидной цепочки.
        bc_with_two_blocks.chain[1].transactions[0]["owner"] = "Hacker"
        report = bc_with_two_blocks.is_valid()
        report.print_report()

        captured = capsys.readouterr()
        assert "TX_HASH_MISMATCH" in captured.out
        assert "Блок #1" in captured.out



# Проверка внешнего файла (FR-16, NFR-07)
class TestExternalFileVerification:

    @staticmethod
    def _make_file(path: str, content: bytes) -> str:
        with open(path, "wb") as f:
            f.write(content)
        return hashlib.sha256(content).hexdigest()

    def test_tc08_matching_file(self, tmp_path):
        # ТК-08: файл совпадает с хэшем -> True.
        path = str(tmp_path / "doc.txt")
        expected = self._make_file(path, b"hello world")

        is_valid, msg = FileService.verify_external_file(path, expected)
        assert is_valid is True
        assert "совпадает" in msg.lower()

    def test_tc09_tampered_file(self, tmp_path):
        # ТК-09: содержимое изменено -> False.
        path = str(tmp_path / "doc.txt")
        expected = self._make_file(path, b"hello world")

        # Подмена содержимого
        with open(path, "wb") as f:
            f.write(b"hello hacked")

        is_valid, msg = FileService.verify_external_file(path, expected)
        assert is_valid is False
        assert "не совпадает" in msg.lower()

    def test_tc10_missing_file(self, tmp_path):
        # ТК-10: файла нет -> False.
        path = str(tmp_path / "nonexistent.txt")
        is_valid, msg = FileService.verify_external_file(path, "abc")
        assert is_valid is False
        assert "не найден" in msg.lower()

    def test_tc11_empty_file(self, tmp_path):
        # ТК-11: пустой файл, корректный хэш -> True
        path = str(tmp_path / "empty.txt")
        empty_hash = hashlib.sha256(b"").hexdigest()
        with open(path, "wb"):
            pass

        is_valid, _ = FileService.verify_external_file(path, empty_hash)
        assert is_valid is True

    def test_tc12_large_file_streaming(self, tmp_path):
        # ТК-12/NFR-07: большой файл проверяется потоково
        path = str(tmp_path / "big.bin")
        content = b"x" * (5 * 1024 * 1024)  # 5MB
        expected = self._make_file(path, content)

        is_valid, _ = FileService.verify_external_file(path, expected)
        assert is_valid is True
