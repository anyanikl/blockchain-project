"""
network/errors.py

Коды ошибок и формат ответа об ошибке (Раздел 7 ТЗ).
"""


class ErrorCode:
    INVALID_JSON = "INVALID_JSON"
    BLOCK_HASH_MISMATCH = "BLOCK_HASH_MISMATCH"
    TX_HASH_MISMATCH = "TX_HASH_MISMATCH"
    PREV_HASH_MISMATCH = "PREV_HASH_MISMATCH"
    BLOCK_ALREADY_EXISTS = "BLOCK_ALREADY_EXISTS"
    INTERNAL_ERROR = "INTERNAL_ERROR"


def error_response(error_code: str, message: str) -> dict:
    """
    Формирует стандартный JSON-ответ об ошибке.
    Пример: {"status": "error", "error_code": "PREV_HASH_MISMATCH", "message": "..."}
    """
    return {
        "status": "error",
        "error_code": error_code,
        "message": message,
    }