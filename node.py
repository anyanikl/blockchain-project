"""
node.py

Запуск ноды блокчейн-реестра (API-слой на Flask).
Раздел 4 ТЗ Архитектора.

Запуск: python node.py --port 8000 --peers http://localhost:8001
"""

import argparse
from flask import Flask, jsonify

from core.blockchain import Blockchain
from network.errors import error_response, ErrorCode

# Создаем Flask-приложение
app = Flask(__name__)

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


@app.route("/receive_block", methods=["POST"])
def receive_block():
    """
    Приём нового блока от другой ноды (Раздел 5).
    """
    from flask import request

    block_data = request.get_json()
    if not block_data:
        return jsonify(error_response(ErrorCode.INVALID_JSON, "Пустой запрос или неверный JSON")), 400

    success, code, message = blockchain.receive_block(block_data)

    if success:
        # Если блок уже есть, тоже возвращаем 200 (идемпотентность)
        if code == "ALREADY_EXISTS":
            return jsonify({"status": "success", "message": message}), 200
        return jsonify({"status": "success", "message": message}), 200
    else:
        return jsonify(error_response(code, message)), 400
# ------------------------------------------------------------------
# Запуск сервера
# ------------------------------------------------------------------

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
    blockchain = Blockchain(storage_path=storage_path)

    print(f"[{node_id}] Нода запущена на порту {port}")
    print(f"[{node_id}] Пиры: {peers if peers else 'нет'}")
    print(f"[{node_id}] Genesis hash: {blockchain.get_chain()[0].hash[:16]}...")

    # Запускаем Flask
    app.run(host="0.0.0.0", port=port, threaded=True)


if __name__ == "__main__":
    main()