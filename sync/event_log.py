"""
sync/event_log.py

Журнал событий (Раздел 3.3 ТЗ Архитектора).
Кольцевой буфер на EVENT_LOG_SIZE=200 записей.
"""

import time
from collections import deque
from typing import List, Dict, Any, Optional


class EventLog:
    """
    Хранит последние EVENT_LOG_SIZE событий в памяти.
    При переполнении старые события автоматически удаляются.
    """
    def __init__(self, max_size: int = 200):
        self.max_size = max_size
        self._events = deque(maxlen=max_size)
        self._next_id = 1

    def add(
        self,
        level: str,
        category: str,
        code: str,
        message: str,
        source_node: Optional[str] = None,
        block_index: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Добавляет событие в журнал.
        :param level: INFO, WARNING, ERROR
        :param category: SYNC, NETWORK, VALIDATION, API
        :param code: PEER_UNREACHABLE, SYNC_COMPLETED, BLOCK_HASH_MISMATCH и т.д.
        :param message: Человекочитаемое описание
        :param source_node: ID ноды-источника (если применимо)
        :param block_index: Индекс блока (если применимо)
        """
        event = {
            "id": self._next_id,
            "timestamp": int(time.time()),
            "level": level,
            "category": category,
            "code": code,
            "message": message,
            "source_node": source_node,
            "block_index": block_index,
        }
        self._events.append(event)
        self._next_id += 1
        return event

    def get_events(
        self,
        limit: int = 50,
        level: Optional[str] = None,
        since_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Возвращает список событий с фильтрацией.
        :param limit: Максимальное количество событий (по умолчанию 50)
        :param level: Фильтр по уровню (INFO, WARNING, ERROR)
        :param since_id: Вернуть события с id > since_id
        """
        events = list(self._events)

        # Фильтр по level
        if level:
            events = [e for e in events if e["level"] == level]

        # Фильтр по since_id
        if since_id is not None:
            events = [e for e in events if e["id"] > since_id]

        # Ограничение по количеству (берем последние limit штук)
        return events[-limit:] if limit else events

    def clear(self) -> None:
        """Очищает журнал (для тестов)."""
        self._events.clear()
        self._next_id = 1