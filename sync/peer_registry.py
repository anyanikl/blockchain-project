"""
sync/peer_registry.py

Реестр пиров (Раздел 3.1 ТЗ Архитектора).
Сохраняет информацию о других нодах в peers.json.
"""

import json
import os
from typing import List, Dict, Any


# sync/peer_registry.py
class Peer:
    def __init__(self, node_id: str, url: str, last_seen: int = 0,
                 status: str = "unknown", chain_length: int = 0):
        self.node_id = node_id
        self.url = url
        self.last_seen = last_seen
        self.status = status
        self.chain_length = chain_length   # ← новое

    def to_dict(self):
        return {
            "node_id": self.node_id,
            "url": self.url,
            "last_seen": self.last_seen,
            "status": self.status,
            "chain_length": self.chain_length,
        }

    @staticmethod
    def from_dict(data):
        return Peer(
            node_id=data.get("node_id", ""),
            url=data.get("url", ""),
            last_seen=data.get("last_seen", 0),
            status=data.get("status", "unknown"),
            chain_length=data.get("chain_length", 0),
        )


class PeerRegistry:
    """
    Управляет списком пиров и сохраняет его в JSON-файл.
    """
    def __init__(self, file_path: str = "peers.json"):
        self.file_path = file_path
        self.peers: List[Peer] = []
        self._load()

    def _load(self) -> None:
        """Загружает пиров из файла, если он есть."""
        if not os.path.exists(self.file_path):
            return
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.peers = [Peer.from_dict(p) for p in data]
        except (json.JSONDecodeError, KeyError):
            self.peers = []

    def save(self) -> None:
        """Сохраняет пиров в файл."""
        data = [p.to_dict() for p in self.peers]
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def add_peer(self, peer: Peer) -> None:
        """Добавляет нового пира (если такого URL еще нет)."""
        for existing in self.peers:
            if existing.url == peer.url:
                return
        self.peers.append(peer)
        self.save()

    def update_status(self, url: str, status: str, last_seen: int = None,
                      chain_length: int = None) -> None:
        for peer in self.peers:
            if peer.url == url:
                peer.status = status
                if last_seen is not None:
                    peer.last_seen = last_seen
                if chain_length is not None:
                    peer.chain_length = chain_length
                self.save()
                return

    def get_online_peers(self) -> List[Peer]:
        """Возвращает список пиров со статусом online."""
        return [p for p in self.peers if p.status == "online"]

    def get_all_peers(self) -> List[Peer]:
        """Возвращает всех пиров."""
        return self.peers