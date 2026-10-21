"""
Проверка хэша содержимого транзакции (пункт c).
"""

from core.transaction import Transaction


class TestTransactionHash:
    def test_hash_deterministic(self):
        """c: одинаковые данные → одинаковый tx_hash."""
        tx1 = Transaction(tx_id="t1", type="REGISTER", land_id="l1", timestamp=100)
        tx2 = Transaction(tx_id="t1", type="REGISTER", land_id="l1", timestamp=100)
        assert tx1.tx_hash == tx2.tx_hash
        assert len(tx1.tx_hash) == 64

    def test_hash_changes_on_data(self):
        """c: изменение поля транзакции → другой tx_hash."""
        tx1 = Transaction(tx_id="t1", type="REGISTER", land_id="l1")
        tx2 = Transaction(tx_id="t1", type="REGISTER", land_id="l2")
        assert tx1.tx_hash != tx2.tx_hash

    def test_hash_changes_on_extra(self):
        """c: изменение extra (owner/buyer) → другой tx_hash."""
        tx1 = Transaction(tx_id="t1", type="SELL", extra={"buyer": "A"})
        tx2 = Transaction(tx_id="t1", type="SELL", extra={"buyer": "B"})
        assert tx1.tx_hash != tx2.tx_hash

    def test_repr(self):
        tx = Transaction(tx_id="t1", type="TEST")
        assert "Transaction" in repr(tx)
