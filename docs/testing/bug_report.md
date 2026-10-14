# Bug Report — Спринт 2

## BUG-001: extra перезаписывает известные поля Transaction

| Поле      | Значение                                            |
| --------- | --------------------------------------------------- |
| ID        | BUG-001                                             |
| Дата      | 2026-10-14                                          |
| Severity  | Medium                                              |
| Priority  | High                                                |
| Компонент | `core/transaction.py`, метод `to_dict()`            |
| Обнаружил | Тестировщик                                         |
| Тест      | TC-13 (`test_extra_does_not_override_known_fields`) |
| Статус    | **Исправлено**                                      |

### Описание

При передаче в `Transaction(extra={...})` ключей, совпадающих с известными полями (`tx_id`, `type`, `land_id` и т.д.), метод `to_dict()` перезаписывал оригинальные значения значениями из `extra`. Это нарушало целостность транзакции и могло привести к подмене данных в блокчейне.

### Шаги воспроизведения

1. Создать `Transaction(tx_id="real-id", type="REGISTER_LAND", extra={"tx_id": "fake-id"})`
2. Вызвать `tx.to_dict()`
3. Проверить поле `tx_id`

### Ожидаемый результат

`tx_id == "real-id"`

### Фактический результат (до фикса)

`tx_id == "fake-id"`

### Причина

В `to_dict()` использовался `base.update(self.extra)`, который позволяет `extra` перезаписать любые поля.

### Решение

Фильтровать `extra` по `_KNOWN_FIELDS`:

```python
for k, v in self.extra.items():
    if k not in self._KNOWN_FIELDS:
        base[k] = v
```
