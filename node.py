"""
node.py

Запуск ноды блокчейн-реестра (API-слой на Flask).
Спринт 5: синхронизация, события, консенсус (лидер + кворум).

Запуск лидера:
    python node.py --port 8000 --leader --peers http://127.0.0.1:8001,http://127.0.0.1:8002
Запуск участника:
    python node.py --port 8001 --peers http://127.0.0.1:8000,http://127.0.0.1:8002
"""

import argparse
import time
import uuid
import threading

from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.exceptions import BadRequest

from core.blockchain import Blockchain
from core.block import Block
from core.transaction import Transaction
from network.errors import ErrorCode, error_response, ERROR_HTTP_STATUS
from network.node_network import NodeNetwork
from sync.peer_registry import PeerRegistry, Peer
from sync.event_log import EventLog
from sync.consensus import ConsensusManager
from sync.sync_manager import SyncManager


app = Flask(__name__)
CORS(app)

# Глобальные объекты (инициализируются в main)
blockchain: Blockchain = None
node_id: str = None
peers: list = []
peer_registry: PeerRegistry = None
event_log: EventLog = None
consensus_manager: ConsensusManager = None
sync_manager: SyncManager = None
is_leader: bool = False
self_url: str = ""


# ==================================================================
# Вспомогательные функции
# ==================================================================

def _err(code: str, message: str, **extra):
    """Единый ответ об ошибке + запись в EventLog."""
    http_status = ERROR_HTTP_STATUS.get(code, 400)
    event_log.add(
        level="ERROR" if http_status >= 400 else "INFO",
        category="API" if http_status < 500 else "INTEGRITY",
        code=code,
        message=message,
    )
    return jsonify(error_response(code, message, **extra)), http_status


_leader_cache = {"url": "", "expires_at": 0}

def _find_leader_url() -> str:
    """
    Ищет URL лидера среди известных пиров.
    Fallback: если peer_registry пуст — перебираем peers (из --peers).
    Кеш на 5 секунд.
    """
    import time as _time
    now = _time.time()
    if _leader_cache["url"] and _leader_cache["expires_at"] > now:
        return _leader_cache["url"]

    # 1. peer_registry
    for peer in peer_registry.get_all_peers():
        status = NodeNetwork([peer.url]).get_peer_status(peer.url)
        if status.get("is_leader"):
            _leader_cache["url"] = peer.url
            _leader_cache["expires_at"] = now + 5
            return peer.url

    # 2. Fallback: peers из --peers
    for peer_url in peers:
        status = NodeNetwork([peer_url]).get_peer_status(peer_url)
        if status.get("is_leader"):
            _leader_cache["url"] = peer_url
            _leader_cache["expires_at"] = now + 5
            return peer_url

    return ""


def _trigger_pull_from(peer_url: str):
    """Асинхронно запускает pull от указанного пира (для CHAIN_BEHIND)."""
    def _run():
        peer = Peer(node_id="", url=peer_url)
        try:
            sync_manager.sync_from_peer(peer)
        except Exception as e:
            event_log.add("ERROR", "SYNC", "PULL_ERROR", f"Ошибка pull от {peer_url}: {e}")
    threading.Thread(target=_run, daemon=True).start()


# ==================================================================
# СЕТЬ: status, blocks, receive_block
# ==================================================================

@app.route("/status", methods=["GET"])
def get_status():
    """Расширенный GET /status (п. 6.1)."""
    latest = blockchain.get_latest_block()
    genesis = blockchain.get_chain()[0]
    peers_all = peer_registry.get_all_peers()
    peers_online = [p for p in peers_all if p.status == "online"]

    return jsonify({
        "node_id": node_id,
        "status": "online",
        "node_state": sync_manager.get_node_state(),
        "chain_length": len(blockchain.get_chain()),
        "latest_block_hash": latest.hash,
        "genesis_hash": genesis.hash,
        "peers_total": len(peers_all),
        "peers_online": len(peers_online),
        "last_sync_at": sync_manager.get_last_sync_at(),
        "is_leader": is_leader,
        "role": "leader" if is_leader else "follower",
    })


@app.route("/blocks", methods=["GET"])
def get_blocks():
    """
    GET /blocks (п. 6.2):
      - без параметров — вся цепочка
      - ?from_index=&limit= — пагинация
      - ?include_pending=true — включая pending (для отладки)
    """
    if sync_manager.get_node_state() == "corrupted":
        return _err(ErrorCode.CHAIN_CORRUPTED, "Локальная цепочка повреждена")

    from_index = request.args.get("from_index", type=int)
    limit = request.args.get("limit", type=int)
    include_pending = request.args.get("include_pending", "false").lower() == "true"

    # Валидация параметров
    if from_index is not None and from_index < 0:
        return _err(ErrorCode.INVALID_PARAMS, "from_index должен быть >= 0")
    if limit is not None and (limit < 1 or limit > 1000):
        return _err(ErrorCode.INVALID_PARAMS, "limit должен быть в диапазоне 1..1000")

    chain = blockchain.get_chain()
    blocks = [b for b in chain if include_pending or b.status == "confirmed"]

    if from_index is not None:
        blocks = [b for b in blocks if b.index >= from_index]
    if limit is not None:
        blocks = blocks[:limit]

    return jsonify([b.to_dict() for b in blocks])


@app.route("/blocks/<int:index>", methods=["GET"])
def get_block_by_index(index):
    if sync_manager.get_node_state() == "corrupted":
        return _err(ErrorCode.CHAIN_CORRUPTED, "Локальная цепочка повреждена")
    chain = blockchain.get_chain()
    if index < 0 or index >= len(chain):
        return _err(ErrorCode.NOT_FOUND, f"Блок #{index} не найден")
    return jsonify(chain[index].to_dict())


@app.route("/receive_block", methods=["POST"])
def receive_block():
    """
    POST /receive_block (п. 6.3, 6.4).
    Принимает только confirmed-блоки.
    """
    try:
        block_data = request.get_json()
    except BadRequest:
        return _err(ErrorCode.INVALID_JSON, "Невалидный JSON")

    if not block_data:
        return _err(ErrorCode.INVALID_JSON, "Пустой запрос")

    success, code, message = blockchain.receive_block(block_data)

    if success:
        if code == "BLOCK_ALREADY_EXISTS":
            return jsonify({"status": "success", "result": "already_known", "message": message}), 200
        event_log.add("INFO", "SYNC", "BLOCK_ACCEPTED", message,
                      block_index=block_data.get("index"))
        return jsonify({"status": "success", "result": "accepted", "message": message}), 200

    # Ошибки
    if code == ErrorCode.CHAIN_BEHIND:
        local_len = len(blockchain.get_chain())
        _trigger_pull_from(request.remote_addr and f"http://{request.remote_addr}" or "")
        return _err(ErrorCode.CHAIN_BEHIND, message, local_length=local_len)
    if code == ErrorCode.FORK_DETECTED:
        # Фиксируем форк
        event_log.add("ERROR", "INTEGRITY", "FORK_DETECTED", message,
                      block_index=block_data.get("index"))
        return _err(ErrorCode.FORK_DETECTED, message)
    if code in (ErrorCode.BLOCK_HASH_MISMATCH, ErrorCode.TX_HASH_MISMATCH):
        # integrity-категория
        event_log.add("ERROR", "INTEGRITY", code, message,
                      block_index=block_data.get("index"))
    return _err(code, message)


# ==================================================================
# КОНСЕНСУС: proposals / vote / commit
# ==================================================================

@app.route("/proposals", methods=["POST"])
def receive_proposal():
    """
    POST /proposals — участник получает предложение блока от лидера.
    Валидирует блок и возвращает свой голос.
    """
    data = request.get_json() or {}
    proposal_id = data.get("proposal_id")
    block_data = data.get("block_data")
    leader_id = data.get("leader_id")

    if not proposal_id or not block_data:
        return _err(ErrorCode.MISSING_FIELDS, "Нужны proposal_id и block_data")

    # Защита от двойного голоса
    if consensus_manager.has_voted(proposal_id, node_id):
        return _err(ErrorCode.PROPOSAL_ALREADY_VOTED,
                    f"Уже голосовали за {proposal_id}")

    # Защита от двух блоков на одну позицию
    block_index = block_data.get("index")
    chain = blockchain.get_chain()
    if block_index is not None and block_index < len(chain):
        existing = chain[block_index]
        if existing.hash != block_data.get("hash"):
            event_log.add("ERROR", "CONSENSUS", "DUPLICATE_BLOCK_POSITION",
                          f"Блок #{block_index} уже есть с другим хэшем")
            vote, reason = "reject", ErrorCode.DUPLICATE_BLOCK_POSITION
        else:
            vote, reason = "accept", None
    else:
        # Валидируем (require_confirmed=False — блок ещё pending)
        is_valid, code, msg = blockchain.validate_incoming_block(
            block_data, require_confirmed=False
        )
        if is_valid:
            vote, reason = "accept", None
        else:
            vote, reason = "reject", code
            event_log.add("WARNING", "CONSENSUS", "VOTE_REJECTED",
                          f"Блок #{block_index} отклонён: {code} — {msg}")

    # Сохраняем предложение локально (чтобы потом commit применить)
    from sync.consensus import Proposal
    proposal = Proposal(
        proposal_id=proposal_id,
        block_data=block_data,
        leader_id=leader_id or "",
        created_at=int(time.time()),
        votes={node_id: vote},
        status="pending",
    )
    consensus_manager.proposals[proposal_id] = proposal
    consensus_manager._save()

    # Отправляем голос лидеру
    leader_url = next(
        (p.url for p in peer_registry.get_all_peers() if p.node_id == leader_id),
        None,
    )
    if leader_url:
        NodeNetwork([leader_url]).send_vote(leader_url, proposal_id, node_id, vote, reason)

    event_log.add("INFO", "CONSENSUS", "PROPOSAL_RECEIVED",
                  f"Предложение {proposal_id} от {leader_id}: {vote}")

    return jsonify({"status": "success", "vote": vote, "reason": reason}), 200


@app.route("/proposals/<proposal_id>/vote", methods=["POST"])
def receive_vote(proposal_id):
    """
    POST /proposals/{id}/vote — лидер получает голос от участника.
    При кворуме 2/3 — фиксирует блок и рассылает commit.
    """
    if not is_leader:
        return _err(ErrorCode.NOT_A_LEADER, "Только лидер принимает голоса")

    data = request.get_json() or {}
    voter_id = data.get("voter_id")
    vote = data.get("vote")
    reason = data.get("reason")

    if not voter_id or vote not in ("accept", "reject"):
        return _err(ErrorCode.MISSING_FIELDS, "Нужны voter_id и vote=accept|reject")

    # Делегируем в SyncManager.process_vote — он уже умеет фиксить при кворуме
    result = sync_manager.process_vote(proposal_id, voter_id, vote)

    if result.get("status") == "success" and result.get("message") == "Block confirmed and added":
        # Кворум достигнут — рассылаем commit всем пирам
        proposal = consensus_manager.get_proposal(proposal_id)
        if proposal:
            NodeNetwork(peers).broadcast_commit(proposal_id, proposal.block_data)
            event_log.add("INFO", "CONSENSUS", "QUORUM_REACHED",
                          f"Блок #{proposal.block_data.get('index')} подтверждён (кворум)")

    return jsonify(result), 200


@app.route("/proposals/<proposal_id>/commit", methods=["POST"])
def commit_proposal(proposal_id):
    """
    POST /proposals/{id}/commit — участник получает уведомление о кворуме.
    Фиксирует блок в своей цепочке.
    """
    data = request.get_json() or {}
    block_data = data.get("block_data")

    if not block_data:
        return _err(ErrorCode.MISSING_FIELDS, "Нужен block_data")

    # Фиксируем proposal локально
    consensus_manager.commit_proposal(proposal_id, block_data)

    # Добавляем блок в цепочку (если ещё не добавлен)
    block_index = block_data.get("index")
    chain = blockchain.get_chain()
    if block_index is not None and block_index == len(chain):
        # Проверяем, что блок валиден как confirmed
        block_data["status"] = "confirmed"
        is_valid, code, msg = blockchain.validate_incoming_block(block_data)
        if not is_valid:
            return _err(code, f"Commit-блок невалиден: {msg}")
        new_block = Block.from_dict(block_data)
        with blockchain.lock:
            blockchain.chain.append(new_block)
            blockchain.storage.save(blockchain.chain)
        event_log.add("INFO", "CONSENSUS", "BLOCK_COMMITTED",
                      f"Блок #{block_index} зафиксирован после commit",
                      block_index=block_index)

    return jsonify({"status": "success", "message": "Block committed"}), 200


@app.route("/proposals/<proposal_id>", methods=["GET"])
def get_proposal(proposal_id):
    proposal = consensus_manager.get_proposal(proposal_id)
    if not proposal:
        return _err(ErrorCode.PROPOSAL_NOT_FOUND, f"Предложение {proposal_id} не найдено")
    return jsonify(proposal.to_dict())


# ==================================================================
# ЛОКАЛЬНЫЙ API ДЛЯ UI (п. 7)
# ==================================================================

@app.route("/nodes", methods=["GET"])
def get_nodes():
    return jsonify(sync_manager.get_peers_snapshot())


@app.route("/nodes", methods=["POST"])
def add_node():
    """Should: добавить пира вручную."""
    data = request.get_json() or {}
    node_id_ = data.get("node_id")
    url = data.get("url")
    if not node_id_ or not url:
        return _err(ErrorCode.MISSING_FIELDS, "Нужны node_id и url")
    peer_registry.add_peer(Peer(node_id=node_id_, url=url))
    event_log.add("INFO", "NETWORK", "PEER_ADDED", f"Добавлен пир {node_id_} ({url})")
    return jsonify({"status": "success", "message": "Peer added"}), 201


@app.route("/events", methods=["GET"])
def get_events():
    limit = request.args.get("limit", default=50, type=int)
    level = request.args.get("level")
    since_id = request.args.get("since_id", type=int)
    events = event_log.get_events(limit=limit, level=level, since_id=since_id)
    return jsonify(events)


@app.route("/sync", methods=["POST"])
def trigger_sync():
    result = sync_manager.trigger_sync()
    return jsonify(result), 200


# ==================================================================
# ТРАНЗАКЦИИ И МАЙНИНГ
# ==================================================================

@app.route("/transactions", methods=["POST"])
def submit_transaction():
    """
    POST /transactions:
      - если мы лидер: кладём в мемпул
      - если не лидер: пересылаем лидеру
    """
    data = request.get_json() or {}
    if not data.get("land_id") or not data.get("owner"):
        return _err(ErrorCode.MISSING_FIELDS, "Нужны land_id и owner")

    tx_data = {
        "tx_id": f"tx-{uuid.uuid4().hex[:8]}",
        "type": data.get("type", "REGISTER_LAND"),
        "land_id": data.get("land_id"),
        "timestamp": int(time.time()),
        "approved_by": "REGISTRAR",
        "owner": data.get("owner"),
        "address": data.get("address"),
        "area_sqm": data.get("area_sqm"),
    }

    if is_leader:
        tx = Transaction(
            tx_id=tx_data["tx_id"],
            type=tx_data["type"],
            land_id=tx_data["land_id"],
            timestamp=tx_data["timestamp"],
            approved_by=tx_data["approved_by"],
            extra={"owner": tx_data["owner"], "address": tx_data["address"],
                   "area_sqm": tx_data["area_sqm"]},
        )
        blockchain.add_transaction(tx)
        event_log.add("INFO", "API", "TX_ADDED", f"Транзакция {tx_data['tx_id']} в мемпул")
        return jsonify({"status": "success", "tx_hash": tx.tx_hash,
                        "message": "Transaction added to mempool"}), 201

    # Не лидер — пересылаем лидеру
    leader_url = _find_leader_url()
    if not leader_url:
        return _err(ErrorCode.LEADER_UNAVAILABLE, "Лидер недоступен, транзакция не принята")

    result = NodeNetwork([leader_url]).forward_transaction(leader_url, tx_data)
    if not result["success"]:
        return _err(ErrorCode.LEADER_UNAVAILABLE,
                    f"Не удалось переслать транзакцию лидеру: {result['response']}")
    return jsonify({"status": "success", "result": "forwarded",
                    "leader": leader_url,
                    "tx_hash": tx_data["tx_id"]}), 201


@app.route("/submit_application", methods=["POST"])
def submit_application():
    """Совместимость со спринтом 3–4: алиас POST /transactions."""
    return submit_transaction()


@app.route("/blocks/mine", methods=["POST"])
@app.route("/mine", methods=["POST"])
def mine_block():
    """
    POST /blocks/mine — создаёт предложение блока (только лидер).
    После создания — рассылает proposal пирам.
    """
    if not is_leader:
        return _err(ErrorCode.NOT_A_LEADER, "Только лидер может создавать блоки")

    result = blockchain.mine_block(
        miner_role="REGISTRAR",
        is_leader=True,
        consensus_manager=consensus_manager,
    )

    if result.get("status") != "success":
        return _err(result.get("error_code", ErrorCode.INTERNAL_ERROR), result.get("message", ""))

    # Получаем proposal и рассылаем пирам
    proposal_id = result.get("proposal_id")
    proposal = consensus_manager.get_proposal(proposal_id)
    if proposal:
        # Сохраняем block_data ДО того, как process_vote удалит proposal
        proposal_block_data = proposal.block_data

        # Лидер голосует сам (1 из 3)
        consensus_manager.add_vote(proposal_id, node_id, "accept")

        # Рассылаем proposal пирам
        broadcast = NodeNetwork(peers).broadcast_proposal(proposal.to_dict())
        result["broadcast"] = broadcast

        # Обрабатываем ответы (пиры возвращают vote в ответе)
        for br in broadcast:
            if br.get("success"):
                resp = br.get("response", {})
                if resp.get("vote"):
                    sync_manager.process_vote(proposal_id, br["peer"], resp["vote"])

        # ✅ Если кворум достигнут — commit (используем сохранённый block_data)
        # process_vote мог удалить proposal из consensus_manager — проверяем по-другому
        # Признак кворума: блок с таким hash уже в цепочке
        chain = blockchain.get_chain()
        block_already_added = any(b.hash == proposal_block_data.get("hash") for b in chain)

        if block_already_added:
            NodeNetwork(peers).broadcast_commit(proposal_id, proposal_block_data)
            event_log.add("INFO", "CONSENSUS", "COMMIT_BROADCAST",
                          f"Commit разослан пирам для блока #{proposal_block_data.get('index')}")

    return jsonify(result), 201


# ==================================================================
# ЗАПУСК
# ==================================================================

def main():
    global blockchain, node_id, peers, peer_registry, event_log
    global consensus_manager, sync_manager, is_leader, self_url

    parser = argparse.ArgumentParser(description="Запуск ноды блокчейна")
    parser.add_argument("--port", type=int, required=True, help="Порт ноды")
    parser.add_argument("--peers", type=str, default="", help="URL пиров через запятую")
    parser.add_argument("--leader", action="store_true", help="Нода — лидер")
    parser.add_argument("--data-dir", type=str, default="data", help="Каталог данных")
    args = parser.parse_args()

    node_id = f"node_{args.port}"
    peers = [p.strip() for p in args.peers.split(",") if p.strip()]
    is_leader = args.leader
    self_url = f"http://127.0.0.1:{args.port}"

    # Инициализация
    storage_path = f"{args.data_dir}/blockchain_{args.port}.json"
    blockchain = Blockchain(storage_path=storage_path, peers=peers)
    peer_registry = PeerRegistry(file_path=f"{args.data_dir}/peers_{args.port}.json")
    event_log = EventLog(max_size=200)
    consensus_manager = ConsensusManager(node_id=node_id, is_leader=is_leader, data_dir=args.data_dir)

    # Заполняем реестр из --peers (если ещё не заполнен)
    for url in peers:
        p_node_id = f"node_{url.rstrip('/').split(':')[-1]}"
        peer_registry.add_peer(Peer(node_id=p_node_id, url=url))

    sync_manager = SyncManager(
        peer_registry=peer_registry,
        event_log=event_log,
        node_network=NodeNetwork(peers),
        blockchain=blockchain,
        node_id=node_id,
        consensus_manager=consensus_manager,
    )

    # Нода может быть corrupted при старте — событие
    report = blockchain.is_valid()
    if not report.is_valid:
        event_log.add("ERROR", "INTEGRITY", "CHAIN_CORRUPTED",
                      f"Цепочка невалидна при старте: {len(report.errors)} ошибок")

    # Запускаем фоновый pull-цикл
    sync_manager.start()

    print(f"[{node_id}] Нода запущена на порту {args.port} (leader={is_leader})")
    print(f"[{node_id}] Пиры: {peers if peers else 'нет'}")
    print(f"[{node_id}] Genesis: {blockchain.get_chain()[0].hash[:16]}...")

    # Немедленный цикл синхронизации (п. 5.1)
    threading.Thread(target=sync_manager._poll_peers_once, daemon=True).start()

    # Отключаем access-лог Werkzeug (спам GET /status каждые 5 сек)
    import logging
    logging.getLogger("werkzeug").setLevel(logging.ERROR)

    app.run(host="0.0.0.0", port=args.port, threaded=True)


if __name__ == "__main__":
    main()