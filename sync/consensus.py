"""
sync/consensus.py

Механизм консенсуса с фиксированным лидером и кворумом (Дополнение к Спринту 5).
Управляет предложениями блоков, голосами и подсчетом кворума.
"""

import json
import os
import time
from typing import Dict, List, Any, Optional


CONSENSUS_FILE = "pending_proposals.json"
QUORUM_SIZE = 2  # Минимум 2 из 3


class Proposal:
    """Одно предложение блока на голосование."""
    def __init__(
        self,
        proposal_id: str,
        block_data: dict,
        leader_id: str,
        created_at: int,
        votes: Dict[str, str] = None,  # node_id -> "accept" / "reject"
        status: str = "pending",  # pending, confirmed, rejected
    ):
        self.proposal_id = proposal_id
        self.block_data = block_data
        self.leader_id = leader_id
        self.created_at = created_at
        self.votes = votes or {}
        self.status = status

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "block_data": self.block_data,
            "leader_id": self.leader_id,
            "created_at": self.created_at,
            "votes": self.votes,
            "status": self.status,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Proposal":
        return Proposal(
            proposal_id=data["proposal_id"],
            block_data=data["block_data"],
            leader_id=data["leader_id"],
            created_at=data.get("created_at", 0),
            votes=data.get("votes", {}),
            status=data.get("status", "pending"),
        )


class ConsensusManager:
    def __init__(self, node_id: str, is_leader: bool = False):
        self.node_id = node_id
        self.is_leader = is_leader
        self.proposals: Dict[str, Proposal] = {}
        self._load()

    def _load(self) -> None:
        """Загружает незавершенные предложения из файла."""
        if not os.path.exists(CONSENSUS_FILE):
            return
        try:
            with open(CONSENSUS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for p_data in data:
                    proposal = Proposal.from_dict(p_data)
                    if proposal.status == "pending":
                        self.proposals[proposal.proposal_id] = proposal
        except (json.JSONDecodeError, KeyError):
            self.proposals = {}

    def _save(self) -> None:
        """Сохраняет незавершенные предложения в файл."""
        data = [p.to_dict() for p in self.proposals.values() if p.status == "pending"]
        with open(CONSENSUS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def create_proposal(self, block_data: dict, leader_id: str) -> Proposal:
        """Лидер создает новое предложение блока."""
        proposal_id = f"prop-{int(time.time())}-{self.node_id}"
        proposal = Proposal(
            proposal_id=proposal_id,
            block_data=block_data,
            leader_id=leader_id,
            created_at=int(time.time()),
        )
        self.proposals[proposal_id] = proposal
        self._save()
        return proposal

    def add_vote(self, proposal_id: str, voter_id: str, vote: str) -> Optional[Proposal]:
        """
        Добавляет голос за предложение.
        Возвращает обновленное предложение или None, если предложение не найдено.
        """
        proposal = self.proposals.get(proposal_id)
        if not proposal:
            return None

        proposal.votes[voter_id] = vote

        # Проверяем кворум
        accept_count = sum(1 for v in proposal.votes.values() if v == "accept")
        reject_count = sum(1 for v in proposal.votes.values() if v == "reject")

        if accept_count >= QUORUM_SIZE:
            proposal.status = "confirmed"
        elif reject_count >= QUORUM_SIZE:
            proposal.status = "rejected"

        self._save()
        return proposal

    def get_proposal(self, proposal_id: str) -> Optional[Proposal]:
        return self.proposals.get(proposal_id)

    def get_pending_proposals(self) -> List[Proposal]:
        return [p for p in self.proposals.values() if p.status == "pending"]

    def clear_confirmed(self) -> None:
        """Удаляет подтвержденные предложения (после фиксации в цепочке)."""
        self.proposals = {k: v for k, v in self.proposals.items() if v.status == "pending"}
        self._save()