"""
core/storage.py

Класс BlockchainStorage — слой хранения цепочки в JSON.
Реализует:
- FR-09: сохранение цепочки в JSON
- FR-10: загрузка цепочки при запуске
- FR-11: сохранение после перезапуска
- NFR-03: структурированный JSON

Соответствует компонентной диаграмме: JSON Serializer + File Manager.
"""

import json
import os
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from core.block import Block


class BlockchainStorage:
    """
    Отвечает за сериализацию цепочки в JSON и обратно.
    Не знает про бизнес-логику — только читает/пишет файл.
    """

    def __init__(self, file_path: str = "blockchain.json"):
        self.file_path = file_path

    def exists(self) -> bool:
        """Проверяет, есть ли файл цепочки (FR-10, шаг 24)."""
        return os.path.exists(self.file_path)

    def save(self, chain: List["Block"]) -> None:
        """
        Перезаписывает файл актуальным состоянием цепочки (FR-09).
        Использует overwrite — ТЗ (п.10, шаг 23) требует актуальное состояние.
        """
        data = [block.to_dict() for block in chain]
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load(self) -> List["Block"]:
        """
        Загружает цепочку из файла (FR-10).
        Возвращает пустой список, если файла нет или JSON повреждён —
        это даёт Blockchain возможность создать genesis-блок.
        """
        from core.block import Block  # локальный импорт — избегаем цикла

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [Block.from_dict(b) for b in data]
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return []