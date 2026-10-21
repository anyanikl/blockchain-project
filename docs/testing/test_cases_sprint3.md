# Test Cases — Спринт 3

**Проверка валидности цепочки: a, b, c.**

| ID    | Название                                   | Пункт | Требование | Ожидаемый результат                            | Статус |
| ----- | ------------------------------------------ | ----- | ---------- | ---------------------------------------------- | ------ |
| TC-01 | Валидная цепочка                           | a+b+c | FR-08      | `is_valid() == True`, `errors == []`           | PASS   |
| TC-02 | Цепочка доходит до genesis                 | b     | ТЗ п.10.3  | Все `previous_hash` валидны, genesis → 64 нуля | PASS   |
| TC-03 | Хэш блока детерминирован                   | a     | FR-06      | `b1.hash == b2.hash` для одинаковых данных     | PASS   |
| TC-04 | Изменение данных блока → другой хэш        | a     | NFR-01     | `b1.hash != b2.hash`                           | PASS   |
| TC-05 | Разный nonce → разный хэш                  | a     | ТЗ п.5     | `b1.hash != b2.hash`                           | PASS   |
| TC-06 | Хэш транзакции детерминирован              | c     | FR-14      | `tx1.tx_hash == tx2.tx_hash`                   | PASS   |
| TC-07 | Изменение land_id → другой tx_hash         | c     | FR-14      | `tx1.tx_hash != tx2.tx_hash`                   | PASS   |
| TC-08 | Изменение extra → другой tx_hash           | c     | FR-14      | `tx1.tx_hash != tx2.tx_hash`                   | PASS   |
| TC-09 | Пустой отчёт валиден                       | —     | FR-18      | `is_valid == True`                             | PASS   |
| TC-10 | Печать валидного отчёта                    | —     | NFR-08     | «Цепочка валидна»                              | PASS   |
| TC-11 | Подмена данных блока → BLOCK_HASH_MISMATCH | a     | FR-08      | `is_valid() == False`, `BLOCK_HASH_MISMATCH`   | PASS   |
| TC-12 | Разрыв previous_hash → PREV_HASH_MISMATCH  | b     | FR-08      | `is_valid() == False`, `PREV_HASH_MISMATCH`    | PASS   |
| TC-13 | Подмена tx_hash → TX_HASH_MISMATCH         | c     | FR-14      | `is_valid() == False`, `TX_HASH_MISMATCH`      | PASS   |
| TC-14 | Ошибка содержит block_index и tx_index     | c     | FR-15      | `block_index == 1`, `tx_index == 1`            | PASS   |
| TC-15 | Накопление ошибок                          | a+b+c | FR-08      | `len(errors) == 3`                             | PASS   |
| TC-16 | Одна ошибка → is_valid = False             | —     | FR-18      | `is_valid == False`                            | PASS   |
| TC-17 | Печать ошибки с локацией                   | —     | NFR-08     | «Блок #2», тип ошибки                          | PASS   |
| TC-18 | Печать с tx_index                          | —     | NFR-08     | «Транзакция #0»                                | PASS   |
| TC-19 | get_chain_as_dicts                         | —     | FR-13      | list[dict]                                     | PASS   |
| TC-20 | Мемпул: добавление                         | —     | FR-12      | `mempool_size += 1`                            | PASS   |
| TC-21 | Майнинг: успех                             | —     | FR-04      | `block_index` возвращён                        | PASS   |
| TC-22 | Майнинг: ошибки (роль, пусто)              | —     | FR-04      | `status == "error"`                            | PASS   |
| TC-23 | Аудит: owner и history                     | —     | FR-13      | Корректные значения                            | PASS   |
| TC-24 | Загрузка сохранённой цепочки               | —     | FR-10      | `len(chain) == 2`                              | PASS   |
| TC-25 | Миграция: добавление tx_hash               | —     | FR-17      | `tx_hash` присутствует                         | PASS   |
| TC-26 | Миграция: создание .bak                    | —     | NFR-09     | Файл `.bak` существует                         | PASS   |
| TC-27 | Миграция: обновление previous_hash         | —     | FR-17      | `chain[1].previous_hash == chain[0].hash`      | PASS   |
| TC-28 | Миграция: noop при готовых данных          | —     | FR-17      | `.bak` не создаётся                            | PASS   |
| TC-29 | Save с объектами                           | —     | FR-09      | JSON с `tx_hash`                               | PASS   |
| TC-30 | Ошибка: файл не найден                     | —     | FR-10      | `load() == []`                                 | PASS   |
| TC-31 | Ошибка: битый JSON                         | —     | NFR-02     | `load() == []`                                 | PASS   |
| TC-32 | Ошибка: нет ключа                          | —     | NFR-02     | `load() == []`                                 | PASS   |
| TC-33 | Миграция: backup failure                   | —     | NFR-09     | Цепочка без изменений                          | PASS   |
