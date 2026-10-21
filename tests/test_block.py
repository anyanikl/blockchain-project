"""
tests/test_block.py
Проверка хэша блока (пункт a).
"""

from core.block import Block


class TestBlockHash:
    def test_hash_deterministic(self):
        """a: одинаковые данные → одинаковый хэш."""
        b1 = Block(0, 1000, [{"type": "GENESIS"}], "0" * 64, 0)
        b2 = Block(0, 1000, [{"type": "GENESIS"}], "0" * 64, 0)
        assert b1.hash == b2.hash
        assert len(b1.hash) == 64

    def test_hash_changes_on_data(self):
        """a: изменение данных блока → другой хэш."""
        b1 = Block(1, 100, [{"a": 1}], "p", 0)
        b2 = Block(1, 100, [{"a": 2}], "p", 0)
        assert b1.hash != b2.hash

    def test_hash_changes_on_nonce(self):
        """a: nonce участвует в хэше."""
        b1 = Block(1, 100, [], "p", nonce=0)
        b2 = Block(1, 100, [], "p", nonce=1)
        assert b1.hash != b2.hash

    def test_repr(self):
        b = Block(0, 100, [], "0"*64)
        assert "Block" in repr(b)

    def test_normalize_non_dict_non_object(self):
        """45: транзакция — число (нестандартный кейс)."""
        b = Block(0, 100, [123], "0" * 64)
        assert 123 in b.to_dict()["transactions"]