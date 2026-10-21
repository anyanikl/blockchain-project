"""
tests/test_validation.py
Проверка ValidationReport — нужен для is_valid().
"""

from core.validation import ValidationError, ValidationReport


class TestValidationReport:
    def test_empty_is_valid(self):
        """Пустой отчёт → цепочка валидна."""
        report = ValidationReport()
        assert report.is_valid is True
        assert report.errors == []

    def test_add_error_makes_invalid(self):
        """Одна ошибка → is_valid = False."""
        report = ValidationReport()
        report.add_error(ValidationError(1, "TEST", "a", "b"))
        assert report.is_valid is False
        assert len(report.errors) == 1

    def test_multiple_errors(self):
        """FR-08: собираем все ошибки, не падаем на первой."""
        report = ValidationReport()
        report.add_error(ValidationError(1, "BLOCK_HASH_MISMATCH", "a", "b"))
        report.add_error(ValidationError(2, "PREV_HASH_MISMATCH", "c", "d"))
        report.add_error(ValidationError(3, 0, "TX_HASH_MISMATCH", "e", "f"))
        assert len(report.errors) == 3

    def test_print_report(self, capsys):
        """NFR-08: отчёт печатается читаемо."""
        report = ValidationReport()
        report.add_error(ValidationError(2, "BLOCK_HASH_MISMATCH", "abc123", "xyz789"))
        report.print_report()
        out = capsys.readouterr().out
        assert "Блок #2" in out
        assert "BLOCK_HASH_MISMATCH" in out

    def test_error_repr(self):
        err = ValidationError(1, "TEST", "aaa", "bbb")
        assert "block=1" in repr(err)

    def test_print_with_tx_index(self, capsys):
        report = ValidationReport()
        report.add_error(ValidationError(
            block_index=1,
            error_type="TX_HASH_MISMATCH",
            expected="a",
            actual="b",
            tx_index=0,
        ))
        report.print_report()
        out = capsys.readouterr().out
        assert "Блок #1" in out
        assert "Транзакция #0" in out