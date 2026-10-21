# Блокчейн-реестр земельных участков

Ссылка на доску: https://blockchain.yougile.com/team/212a272b7837/blockchain

## Спринт 2: хранение блоков и цепочки

### Структура

- `core/` — бизнес-логика (Block, Blockchain, Transaction)
- `storage/` — JSON-хранилище
- `services/` — сервисы (Processing Layer)
- `data/` — файл цепочки
- `tests/` — тесты (pytest)
- `docs/` — документация

### Запуск тестов

```bash
pip install -r requirements.txt
pytest

pytest tests/test_sprint3.py -v
```
