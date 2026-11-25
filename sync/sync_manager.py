"""
sync/sync_manager.py

Менеджер синхронизации (Раздел 5.4, 5.5 ТЗ Архитектора).
Периодически опрашивает пиров, обновляет их статус и вычисляет node_state.
"""

import time
import threading
from typing import List, Dict, Any, Optional

from sync.peer_registry import PeerRegistry, Peer
from sync.event_log import EventLog
from network.node_network import NodeNetwork


SYNC_INTERVAL_SEC = 5
MAX_FAIL_COUNT = 3
SYNC_BATCH_LIMIT = 10


class SyncManager:
    def __init__(
        self,
        peer_registry: PeerRegistry,
        event_log: EventLog,
        node_network: NodeNetwork,
        blockchain,  # ссылка на Blockchain, чтобы брать chain_length и genesis_hash
        node_id: str,
        consensus_manager=None,
    ):
        self.peer_registry = peer_registry
        self.event_log = event_log
        self.node_network = node_network
        self.blockchain = blockchain
        self.node_id = node_id

        self._fail_counts: Dict[str, int] = {}  # url -> количество неудач
        self._last_sync_at: int = 0
        self._node_state: str = "synced"
        self._syncing: bool = False
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.consensus_manager = consensus_manager

    # Запуск / остановка фонового потока

    def start(self) -> None:
        """Запускает фоновый поток опроса пиров."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._sync_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Останавливает фоновый поток."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)

    def _sync_loop(self) -> None:
        """Бесконечный цикл опроса пиров."""
        while not self._stop_event.is_set():
            try:
                self._poll_peers_once()
            except Exception as e:
                self.event_log.add(
                    level="ERROR",
                    category="SYNC",
                    code="SYNC_LOOP_ERROR",
                    message=f"Ошибка в цикле синхронизации: {e}",
                )
            # Ждем SYNC_INTERVAL_SEC или пока не попросят остановиться
            self._stop_event.wait(SYNC_INTERVAL_SEC)

    # Один цикл опроса пиров

    def _poll_peers_once(self) -> None:
        """Опрашивает всех пиров и, если отстаём — запускает догон."""
        peers = self.peer_registry.get_all_peers()
        if not peers:
            self._node_state = "synced"
            return

        best_chain_length = len(self.blockchain.get_chain())
        best_peer = None

        for peer in peers:
            status = self.node_network.get_peer_status(peer.url)

            if "error" in status:
                # Пир недоступен
                self._fail_counts[peer.url] = self._fail_counts.get(peer.url, 0) + 1
                if self._fail_counts[peer.url] >= MAX_FAIL_COUNT and peer.status != "offline":
                    self.peer_registry.update_status(peer.url, "offline")
                    self.event_log.add(
                        level="WARNING", category="NETWORK", code="PEER_UNREACHABLE",
                        message=f"Пир {peer.url} недоступен (3 неудачи)",
                        source_node=peer.node_id,
                    )
            else:
                # Пир ответил
                if peer.status == "offline":
                    self.event_log.add(
                        level="INFO", category="NETWORK", code="PEER_RECOVERED",
                        message=f"Пир {peer.url} снова онлайн",
                        source_node=peer.node_id,
                    )
                self._fail_counts[peer.url] = 0
                peer_chain_length = status.get("chain_length", 0)
                self.peer_registry.update_status(
                    peer.url, "online",
                    last_seen=int(time.time()),
                    chain_length=peer_chain_length,
                )

                if peer_chain_length > best_chain_length:
                    best_chain_length = peer_chain_length
                    best_peer = peer

        # Определяем node_state
        our_length = len(self.blockchain.get_chain())
        if best_chain_length > our_length:
            self._node_state = "behind"
            if best_peer:
                self.event_log.add(
                    level="INFO", category="SYNC", code="SYNC_TRIGGERED",
                    message=f"Отстаём от {best_peer.url} (у нас {our_length}, у пира {best_chain_length}). Запуск pull.",
                    source_node=best_peer.node_id,
                )
                self.sync_from_peer(best_peer)
        else:
            self._node_state = "synced"
            self._last_sync_at = int(time.time())

    # Публичные методы (контракт для node.py)

    def get_node_state(self) -> str:
        """
        Вычисляет состояние БЕЗ сетевых запросов (чтобы не было рекурсии).
        Приоритет: corrupted > fork_detected > syncing > behind > synced.
        """
        # 1. corrupted
        report = self.blockchain.is_valid()
        if not report.is_valid:
            return "corrupted"

        # 2. syncing
        if self._syncing:
            return "syncing"

        # 3. fork_detected
        if self._node_state == "fork_detected":
            return "fork_detected"

        # 4. behind — по ДАННЫМ ИЗ peer_registry (без HTTP!)
        our_length = len(self.blockchain.get_chain())
        for peer in self.peer_registry.get_all_peers():
            # Используем chain_length, сохранённый pull-циклом
            peer_length = getattr(peer, "chain_length", 0) or 0
            if peer.status == "online" and peer_length > our_length:
                return "behind"

        # 5. consensus_pending
        if self.consensus_manager and self.consensus_manager.get_pending_proposals():
            return "consensus_pending"

        return "synced"

    def get_last_sync_at(self) -> int:
        """Возвращает время последней успешной синхронизации."""
        return self._last_sync_at

    def get_peers_snapshot(self) -> List[Dict[str, Any]]:
        """Возвращает снимок пиров для GET /nodes."""
        result = []
        for peer in self.peer_registry.get_all_peers():
            result.append({
                "node_id": peer.node_id,
                "url": peer.url,
                "status": peer.status,
                "last_seen": peer.last_seen,
                "is_self": False,
            })
        # Добавляем себя первым
        result.insert(0, {
            "node_id": self.node_id,
            "url": f"http://localhost:{self._get_self_port()}",
            "status": "online",
            "last_seen": int(time.time()),
            "is_self": True,
        })
        return result

    def trigger_sync(self) -> Dict[str, Any]:
        """
        Запускает синхронизацию вручную (для POST /sync).
        Находит самого длинного пира и догоняет его.
        """
        peers = self.peer_registry.get_online_peers()
        if not peers:
            return {
                "status": "error",
                "result": "no_peers",
                "blocks_added": 0,
                "message": "Нет доступных пиров для синхронизации"
            }

        self._syncing = True

        # Находим пира с самой длинной цепочкой
        best_peer = None
        best_length = len(self.blockchain.get_chain())

        for peer in peers:
            status = self.node_network.get_peer_status(peer.url)
            if "error" in status:
                continue
            peer_length = status.get("chain_length", 0)
            if peer_length > best_length:
                best_length = peer_length
                best_peer = peer

        if not best_peer:
            self._syncing = False
            return {
                "status": "success",
                "result": "already_synced",
                "blocks_added": 0,
                "message": "Наша цепочка уже самая длинная"
            }

        # Запускаем догоняющую синхронизацию
        return self.sync_from_peer(best_peer)

    def process_vote(self, proposal_id: str, voter_id: str, vote: str) -> Dict[str, Any]:
        """Обрабатывает голос от другой ноды."""
        if not self.consensus_manager:
            return {"status": "error", "message": "ConsensusManager не инициализирован"}

        proposal = self.consensus_manager.add_vote(proposal_id, voter_id, vote)
        if not proposal:
            return {"status": "error", "message": "Предложение не найдено"}

        if proposal.status == "confirmed":
            from core.block import Block
            new_block = Block.from_dict(proposal.block_data)
            new_block.status = "confirmed"  # <--- ВАЖНО: ставим статус confirmed
            with self.blockchain.lock:
                self.blockchain.chain.append(new_block)
                self.blockchain.storage.save(self.blockchain.chain)
            self.consensus_manager.clear_confirmed()
            self.event_log.add(level="INFO", category="CONSENSUS", code="QUORUM_REACHED",
                               message=f"Блок #{new_block.index} подтвержден кворумом")
            return {"status": "success", "message": "Block confirmed and added", "block_index": new_block.index}

        return {"status": "success", "message": f"Vote added. Status: {proposal.status}", "votes": proposal.votes}

    def check_timeouts(self):
        """Проверяет и откатывает просроченные предложения."""
        if not self.consensus_manager:
            return
        now = int(time.time())
        for proposal in self.consensus_manager.get_pending_proposals():
            if now - proposal.created_at > 30:  # 30 секунд
                proposal.status = "rejected"
                self.consensus_manager._save()
                self.event_log.add(level="WARNING", category="CONSENSUS", code="CONSENSUS_TIMEOUT", message=f"Предложение {proposal.proposal_id} отклонено по тайм-ауту")

    def sync_from_peer(self, peer: Peer) -> Dict[str, Any]:
        """
        Догоняет конкретного пира, запрашивая блоки по одному.
        Атомарность: если блок невалиден — откатываем все изменения.
        """
        our_length = len(self.blockchain.get_chain())
        added_blocks = []

        self._node_state = "syncing"
        self.event_log.add(
            level="INFO",
            category="SYNC",
            code="SYNC_STARTED",
            message=f"Начинаем синхронизацию с {peer.url} (у нас {our_length} блоков)",
            source_node=peer.node_id,
        )

        try:
            # Запрашиваем блоки по одному, начиная с нашего текущего индекса
            for index in range(our_length, our_length + SYNC_BATCH_LIMIT):
                block_data = self.node_network.get_peer_block(peer.url, index)

                if "error" in block_data:
                    # Блок не найден (пир закончился) — выходим
                    break

                if block_data.get("status") != "confirmed":
                    continue

                # Валидируем блок
                is_valid, code, message = self.blockchain.validate_incoming_block(block_data)

                if not is_valid:
                    # Откатываем все добавленные блоки
                    self._rollback_blocks(added_blocks)
                    self._node_state = "fork_detected"
                    self.event_log.add(
                        level="ERROR",
                        category="SYNC",
                        code="SYNC_BATCH_REJECTED",
                        message=f"Блок #{index} отклонен: {code} — {message}",
                        source_node=peer.node_id,
                        block_index=index,
                    )
                    return {
                        "status": "error",
                        "result": "rejected",
                        "blocks_added": 0,
                        "message": f"Синхронизация прервана на блоке #{index}: {code}"
                    }

                # ✅ Если блок уже есть — пропускаем (не добавляем повторно)
                if code == "BLOCK_ALREADY_EXISTS":
                    continue

                # Добавляем блок
                from core.block import Block
                new_block = Block.from_dict(block_data)
                with self.blockchain.lock:
                    self.blockchain.chain.append(new_block)
                    self.blockchain.storage.save(self.blockchain.chain)

                added_blocks.append(new_block)

            # Успешно догнали
            self._node_state = "synced"
            self._last_sync_at = int(time.time())
            self._syncing = False
            self.event_log.add(
                level="INFO",
                category="SYNC",
                code="SYNC_COMPLETED",
                message=f"Синхронизация завершена. Добавлено блоков: {len(added_blocks)}",
                source_node=peer.node_id,
            )
            return {
                "status": "success",
                "result": "synced",
                "blocks_added": len(added_blocks),
                "message": f"Добавлено блоков: {len(added_blocks)}"
            }

        except Exception as e:
            self._rollback_blocks(added_blocks)
            self._node_state = "corrupted"
            self._syncing = False
            self.event_log.add(
                level="ERROR",
                category="SYNC",
                code="SYNC_ERROR",
                message=f"Ошибка синхронизации: {e}",
                source_node=peer.node_id,
            )
            return {
                "status": "error",
                "result": "failed",
                "blocks_added": 0,
                "message": str(e)
            }

    def _rollback_blocks(self, blocks_to_remove: List) -> None:
        """Откатывает добавленные блоки (атомарность)."""
        if not blocks_to_remove:
            return
        with self.blockchain.lock:
            for block in reversed(blocks_to_remove):
                if self.blockchain.chain and self.blockchain.chain[-1].hash == block.hash:
                    self.blockchain.chain.pop()
            self.blockchain.storage.save(self.blockchain.chain)

    def _get_self_port(self) -> int:
        """Пытается вытащить порт из node_id (node_8000 -> 8000)."""
        try:
            return int(self.node_id.split("_")[1])
        except (IndexError, ValueError):
            return 0