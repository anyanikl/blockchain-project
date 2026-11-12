"""
node.py

Запуск ноды блокчейн-реестра (API-слой на Flask).
Раздел 4 ТЗ Архитектора.

Запуск: python node.py --port 8000 --peers http://localhost:8001
"""

import argparse
from flask import Flask, jsonify
import uuid
from core.blockchain import Blockchain
from network.errors import error_response, ErrorCode
from network.node_network import NodeNetwork
from flask_cors import CORS

# Создаем Flask-приложение
app = Flask(__name__)
CORS(app)

# Глобальные переменные, которые инициализируются при запуске
blockchain: Blockchain = None
node_id: str = None
peers: list = []


# ------------------------------------------------------------------
# Эндпоинты (Раздел 4)
# ------------------------------------------------------------------

@app.route("/status", methods=["GET"])
def get_status():
    """
    Статус ноды: node_id, status, chain_length, latest_block_hash, genesis_hash
    """
    latest_block = blockchain.get_latest_block()
    genesis_block = blockchain.get_chain()[0]

    return jsonify({
        "node_id": node_id,
        "status": "online",
        "chain_length": len(blockchain.get_chain()),
        "latest_block_hash": latest_block.hash,
        "genesis_hash": genesis_block.hash,
    })


@app.route("/blocks", methods=["GET"])
def get_blocks():
    """
    Возвращает всю цепочку блоков.
    """
    return jsonify(blockchain.get_chain_as_dicts())


@app.route("/blocks/<int:index>", methods=["GET"])
def get_block_by_index(index):
    """
    Возвращает конкретный блок по его индексу (Раздел 4, 6).
    """
    # Проверка, что индекс в пределах цепочки
    if index < 0 or index >= len(blockchain.get_chain()):
        return jsonify(error_response("NOT_FOUND", "Блок не найден")), 404

    # Берем блок из цепочки и отдаем в JSON
    block = blockchain.get_chain()[index]
    return jsonify(block.to_dict()), 200

@app.route("/receive_block", methods=["POST"])
def receive_block():
    """
    Приём нового блока от другой ноды (Раздел 5).
    """
    from flask import request
    from werkzeug.exceptions import BadRequest  # <--- ДОБАВЬ ИМПОРТ

    try:
        block_data = request.get_json()
    except BadRequest:  # <--- ДОБАВЬ ОБРАБОТКУ
        return jsonify(error_response(ErrorCode.INVALID_JSON, "Невалидный JSON")), 400

    if not block_data:
        return jsonify(error_response(ErrorCode.INVALID_JSON, "Пустой запрос")), 400
    success, code, message = blockchain.receive_block(block_data)

    if success:
        if code == "BLOCK_ALREADY_EXISTS":
            return jsonify({"status": "success", "message": message}), 200
        return jsonify({"status": "success", "message": message}), 200
    else:
        return jsonify(error_response(code, message)), 400

@app.route("/submit_application", methods=["POST"])
def submit_application():
    """
    Принимает данные о регистрации участка от UI, создает транзакцию и майнит блок.
    """
    from flask import request
    from core.transaction import Transaction
    import time

    data = request.get_json()
    if not data:
        return jsonify(error_response(ErrorCode.INVALID_JSON, "Пустое тело запроса")), 400

    if not data.get("land_id") or not data.get("owner"):
        return jsonify(error_response("MISSING_FIELDS", "Обязательные поля: land_id, owner")), 400
    # ----------------------
    # Создаем транзакцию из данных UI
    tx = Transaction(
        tx_id=f"tx-{uuid.uuid4().hex[:8]}",
        type="REGISTER_LAND",
        land_id=data.get("land_id"),
        timestamp=int(time.time()),
        approved_by="REGISTRAR",
        extra={
            "owner": data.get("owner"),
            "address": data.get("address"),
            "area_sqm": data.get("area_sqm"),
        },
    )
    blockchain.add_transaction(tx)

    # Майним блок
    result = blockchain.mine_block("REGISTRAR")

    # Рассылка блока пирам
    if result.get("status") == "success":
        latest_block = blockchain.get_latest_block()
        current_peers = globals().get("peers", [])
        from network.node_network import NodeNetwork
        network = NodeNetwork(current_peers)
        broadcast_results = network.broadcast_block(latest_block.to_dict())
        result["broadcast"] = broadcast_results

    return jsonify(result)
@app.route("/mine", methods=["POST"])
def mine():
    """
    Создает блок из мемпула и рассылает его пирам (Раздел 4, 5).
    """
    from core.transaction import Transaction
    import time

    tx = Transaction(
        tx_id=f"tx-{int(time.time())}",
        type="REGISTER_LAND",
        land_id=f"land-{int(time.time())}",
        timestamp=int(time.time()),
        approved_by="REGISTRAR",
        extra={"owner": "DemoUser", "address": "Demo St", "area_sqm": 100.0},
    )
    blockchain.add_transaction(tx)

    result = blockchain.mine_block("REGISTRAR")

    if result.get("status") == "success":
        latest_block = blockchain.get_latest_block()

        # Берем пиры из глобальной переменной напрямую
        current_peers = globals().get("peers", [])

        from network.node_network import NodeNetwork
        network = NodeNetwork(current_peers)
        broadcast_results = network.broadcast_block(latest_block.to_dict())
        result["broadcast"] = broadcast_results

    return jsonify(result)

def main():
    global blockchain, node_id, peers

    # Парсим аргументы командной строки (Раздел 3)
    parser = argparse.ArgumentParser(description="Запуск ноды блокчейна")
    parser.add_argument("--port", type=int, required=True, help="Порт ноды")
    parser.add_argument("--peers", type=str, default="", help="Список пиров через запятую")
    args = parser.parse_args()

    # Инициализация
    port = args.port
    node_id = f"node_{port}"
    peers = [p.strip() for p in args.peers.split(",") if p.strip()]

    # Инициализация блокчейна с уникальным файлом для каждой ноды
    storage_path = f"data/blockchain_{port}.json"
    blockchain = Blockchain(storage_path=storage_path, peers=peers)

    print(f"[{node_id}] Нода запущена на порту {port}")
    print(f"[{node_id}] Пиры: {peers if peers else 'нет'}")
    print(f"[{node_id}] Genesis hash: {blockchain.get_chain()[0].hash[:16]}...")

    # Запускаем Flask
    app.run(host="0.0.0.0", port=port, threaded=True)


if __name__ == "__main__":
    main()