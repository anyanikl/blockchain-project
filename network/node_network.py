"""
network/node_network.py

Сетевой слой ноды: исходящие запросы к пирам.
Спринт 5: добавлены методы консенсуса (proposals / votes / commit).
"""

import requests
from concurrent.futures import ThreadPoolExecutor, as_completed


class NodeNetwork:
    def __init__(self, peers: list):
        self.peers = peers
        self.timeout = (2, 5)  # (connect, read)

    # ------------------------------------------------------------------
    # Спринт 4 (без изменений)
    # ------------------------------------------------------------------

    def _send_block_to_peer(self, peer_url: str, block_data: dict) -> dict:
        url = f"{peer_url}/receive_block"
        try:
            response = requests.post(url, json=block_data, timeout=self.timeout)
            return {
                "peer": peer_url,
                "status_code": response.status_code,
                "response": response.json(),
                "success": response.status_code == 200,
            }
        except requests.exceptions.RequestException as e:
            return {
                "peer": peer_url,
                "status_code": None,
                "response": str(e),
                "success": False,
            }

    def broadcast_block(self, block_data: dict) -> list:
        if not self.peers:
            return []
        results = []
        with ThreadPoolExecutor(max_workers=len(self.peers)) as executor:
            future_to_peer = {
                executor.submit(self._send_block_to_peer, peer, block_data): peer
                for peer in self.peers
            }
            for future in as_completed(future_to_peer):
                results.append(future.result())
        return results

    def get_peer_status(self, peer_url: str) -> dict:
        url = f"{peer_url}/status"
        try:
            response = requests.get(url, timeout=self.timeout)
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

    def get_peer_block(self, peer_url: str, index: int) -> dict:
        url = f"{peer_url}/blocks/{index}"
        try:
            response = requests.get(url, timeout=self.timeout)
            if response.status_code == 200:
                return response.json()
            return {"error": f"HTTP {response.status_code}"}
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

    # ------------------------------------------------------------------
    # Спринт 5: pull-синхронизация (пакет блоков)
    # ------------------------------------------------------------------

    def get_peer_blocks_batch(self, peer_url: str, from_index: int, limit: int = 100) -> list:
        """
        GET /blocks?from_index=&limit= — пакет блоков для догоняющей синхронизации.
        Возвращает список блоков (может быть пустым).
        """
        url = f"{peer_url}/blocks"
        params = {"from_index": from_index, "limit": limit}
        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            if response.status_code == 200:
                data = response.json()
                return data if isinstance(data, list) else []
            return []
        except requests.exceptions.RequestException:
            return []

    # ------------------------------------------------------------------
    # Спринт 5: консенсус (лидер <-> участники)
    # ------------------------------------------------------------------

    def send_proposal(self, peer_url: str, proposal_data: dict) -> dict:
        """
        POST /proposals — лидер отправляет предложение блока пиру.
        Возвращает ответ пира (в нём может быть vote: accept/reject).
        """
        url = f"{peer_url}/proposals"
        try:
            response = requests.post(url, json=proposal_data, timeout=self.timeout)
            return {
                "peer": peer_url,
                "status_code": response.status_code,
                "response": response.json() if response.content else {},
                "success": response.status_code in (200, 201),
            }
        except requests.exceptions.RequestException as e:
            return {"peer": peer_url, "status_code": None, "response": str(e), "success": False}

    def send_vote(self, leader_url: str, proposal_id: str, voter_id: str,
                  vote: str, reason: str = None) -> dict:
        """
        POST /proposals/{id}/vote — участник отправляет свой голос лидеру.
        """
        url = f"{leader_url}/proposals/{proposal_id}/vote"
        payload = {"voter_id": voter_id, "vote": vote}
        if reason:
            payload["reason"] = reason
        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            return {
                "status_code": response.status_code,
                "response": response.json() if response.content else {},
                "success": response.status_code == 200,
            }
        except requests.exceptions.RequestException as e:
            return {"status_code": None, "response": str(e), "success": False}

    def send_commit(self, peer_url: str, proposal_id: str, block_data: dict) -> dict:
        """
        POST /proposals/{id}/commit — лидер уведомляет о кворуме.
        """
        url = f"{peer_url}/proposals/{proposal_id}/commit"
        try:
            response = requests.post(url, json={"block_data": block_data}, timeout=self.timeout)
            return {
                "peer": peer_url,
                "status_code": response.status_code,
                "response": response.json() if response.content else {},
                "success": response.status_code == 200,
            }
        except requests.exceptions.RequestException as e:
            return {"peer": peer_url, "status_code": None, "response": str(e), "success": False}

    def broadcast_proposal(self, proposal_data: dict) -> list:
        """Рассылает предложение всем пирам параллельно."""
        if not self.peers:
            return []
        results = []
        with ThreadPoolExecutor(max_workers=len(self.peers)) as executor:
            future_to_peer = {
                executor.submit(self.send_proposal, peer, proposal_data): peer
                for peer in self.peers
            }
            for future in as_completed(future_to_peer):
                results.append(future.result())
        return results

    def broadcast_commit(self, proposal_id: str, block_data: dict) -> list:
        """Рассылает commit всем пирам параллельно."""
        if not self.peers:
            return []
        results = []
        with ThreadPoolExecutor(max_workers=len(self.peers)) as executor:
            future_to_peer = {
                executor.submit(self.send_commit, peer, proposal_id, block_data): peer
                for peer in self.peers
            }
            for future in as_completed(future_to_peer):
                results.append(future.result())
        return results

    # ------------------------------------------------------------------
    # Спринт 5: пересылка транзакции лидеру
    # ------------------------------------------------------------------

    def forward_transaction(self, leader_url: str, tx_data: dict) -> dict:
        """
        POST /transactions — не-лидер пересылает транзакцию лидеру.
        """
        url = f"{leader_url}/transactions"
        try:
            response = requests.post(url, json=tx_data, timeout=self.timeout)
            return {
                "status_code": response.status_code,
                "response": response.json() if response.content else {},
                "success": response.status_code in (200, 201),
            }
        except requests.exceptions.RequestException as e:
            return {"status_code": None, "response": str(e), "success": False}