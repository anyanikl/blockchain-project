"""
core/validation.py

Классы для отчётов о валидации цепочки.
Реализует:
- FR-15: Поиск точки разрыва (детализация)
- FR-18: Формат отчета (ValidationReport, ValidationError)
- NFR-08: Читаемость логов (print_report)
"""

from typing import List, Optional


class ValidationError:
    """
    Одна ошибка валидации (FR-15, FR-18).
    Хранит точную локацию (блок, транзакция) и суть несоответствия.
    """

    def __init__(
        self,
        block_index: int,
        error_type: str,
        expected: str,
        actual: str,
        tx_index: Optional[int] = None,
        description: str = "",
    ):
        self.block_index = block_index
        self.tx_index = tx_index
        self.error_type = error_type  # "BLOCK_HASH_MISMATCH", "PREV_HASH_MISMATCH", "TX_HASH_MISMATCH"
        self.expected = expected
        self.actual = actual
        self.description = description

    def __repr__(self) -> str:
        return (
            f"ValidationError(block={self.block_index}, tx={self.tx_index}, "
            f"type={self.error_type}, expected={self.expected[:12]}..., actual={self.actual[:12]}...)"
        )


class ValidationReport:
    """
    Полный отчёт о проверке целостности (FR-18, NFR-08).
    Содержит флаг is_valid и список всех найденных ошибок.
    """

    def __init__(self):
        self.errors: List[ValidationError] = []

    @property
    def is_valid(self) -> bool:
        """Цепочка валидна, только если нет ни одной ошибки."""
        return len(self.errors) == 0

    def add_error(self, error: ValidationError) -> None:
        """Добавляет ошибку в отчёт."""
        self.errors.append(error)

    def print_report(self) -> None:
        """
        Красивый вывод в консоль (NFR-08).
        Пример: 'Ошибка в блоке #2: [BLOCK_HASH_MISMATCH]. Ожидалось abc123..., получено def456...'
        """
        if self.is_valid:
            print("Цепочка валидна. Ошибок не найдено.")
            return

        print(f"Обнаружено ошибок: {len(self.errors)}")
        for err in self.errors:
            location = f"Блок #{err.block_index}"
            if err.tx_index is not None:
                location += f", Транзакция #{err.tx_index}"
            print(
                f"  - {location}: [{err.error_type}]. "
                f"Ожидалось {err.expected[:16]}..., получено {err.actual[:16]}..."
            )