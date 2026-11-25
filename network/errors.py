"""
network/errors.py

Коды ошибок и формат ответа об ошибке (Раздел 7 ТЗ).
Спринт 5: добавлены коды консенсуса и синхронизации.
"""


class ErrorCode:
    # --- Спринт 4 ---
    INVALID_JSON = "INVALID_JSON"
    BLOCK_HASH_MISMATCH = "BLOCK_HASH_MISMATCH"
    TX_HASH_MISMATCH = "TX_HASH_MISMATCH"
    PREV_HASH_MISMATCH = "PREV_HASH_MISMATCH"
    BLOCK_ALREADY_EXISTS = "BLOCK_ALREADY_EXISTS"
    INTERNAL_ERROR = "INTERNAL_ERROR"

    # --- Спринт 5: синхронизация ---
    CHAIN_BEHIND = "CHAIN_BEHIND"
    FORK_DETECTED = "FORK_DETECTED"
    BUSINESS_RULE_VIOLATION = "BUSINESS_RULE_VIOLATION"
    INVALID_PARAMS = "INVALID_PARAMS"
    CHAIN_CORRUPTED = "CHAIN_CORRUPTED"

    # --- Спринт 5: консенсус (дополнение преподавателя) ---
    BLOCK_NOT_CONFIRMED = "BLOCK_NOT_CONFIRMED"
    NOT_A_LEADER = "NOT_A_LEADER"
    PROPOSAL_NOT_FOUND = "PROPOSAL_NOT_FOUND"
    PROPOSAL_ALREADY_VOTED = "PROPOSAL_ALREADY_VOTED"
    DUPLICATE_BLOCK_POSITION = "DUPLICATE_BLOCK_POSITION"
    LEADER_UNAVAILABLE = "LEADER_UNAVAILABLE"
    NO_QUORUM = "NO_QUORUM"

    # --- API ---
    NOT_FOUND = "NOT_FOUND"
    MISSING_FIELDS = "MISSING_FIELDS"
    FORBIDDEN = "FORBIDDEN"


# HTTP-коды для каждого error_code (для единообразия ответов)
ERROR_HTTP_STATUS = {
    ErrorCode.INVALID_JSON: 400,
    ErrorCode.BLOCK_HASH_MISMATCH: 400,
    ErrorCode.TX_HASH_MISMATCH: 400,
    ErrorCode.PREV_HASH_MISMATCH: 400,
    ErrorCode.BLOCK_ALREADY_EXISTS: 200,
    ErrorCode.INTERNAL_ERROR: 500,
    ErrorCode.CHAIN_BEHIND: 409,
    ErrorCode.FORK_DETECTED: 409,
    ErrorCode.BUSINESS_RULE_VIOLATION: 400,
    ErrorCode.INVALID_PARAMS: 400,
    ErrorCode.CHAIN_CORRUPTED: 503,
    ErrorCode.BLOCK_NOT_CONFIRMED: 400,
    ErrorCode.NOT_A_LEADER: 403,
    ErrorCode.PROPOSAL_NOT_FOUND: 404,
    ErrorCode.PROPOSAL_ALREADY_VOTED: 409,
    ErrorCode.DUPLICATE_BLOCK_POSITION: 409,
    ErrorCode.LEADER_UNAVAILABLE: 503,
    ErrorCode.NO_QUORUM: 409,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.MISSING_FIELDS: 400,
    ErrorCode.FORBIDDEN: 403,
}


def error_response(error_code: str, message: str, **extra) -> dict:
    """
    Формирует стандартный JSON-ответ об ошибке.
    Пример: {"status": "error", "error_code": "PREV_HASH_MISMATCH", "message": "..."}
    Дополнительные поля (например, local_length) передаются через **extra.
    """
    response = {
        "status": "error",
        "error_code": error_code,
        "message": message,
    }
    response.update(extra)
    return response