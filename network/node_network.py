"""
network/node_network.py

Сетевой слой ноды: исходящие запросы к пирам (Раздел 5, 6 ТЗ Архитектора).
"""

import requests
from concurrent.futures import ThreadPoolExecutor, as_completed


class NodeNetwork:
    def __init__(self, peers: list):
        """
        :param peers: список адресов пиров (например, ['http://localhost:8001'])
        """
        self.peers = peers
        # Таймауты по ТЗ: 2с на соединение, 5с на ответ
        self.timeout = (2, 5)

    def _send_block_to_peer(self, peer_url: str, block_data: dict) -> dict:
        """
        Отправляет один блок одному пиру.
        Возвращает результат в виде словаря.
        """
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
            # Если пир недоступен (timeout, connection error)
            return {
                "peer": peer_url,
                "status_code": None,
                "response": str(e),
                "success": False,
            }

    def broadcast_block(self, block_data: dict) -> list:
        """
        Рассылает блок всем пирам ПАРАЛЛЕЛЬНО (Раздел 5).
        Возвращает список отчетов по каждому пиру.
        """
        if not self.peers:
            return []

        results = []
        # Используем ThreadPoolExecutor для параллельной отправки
        with ThreadPoolExecutor(max_workers=len(self.peers)) as executor:
            # Запускаем задачи
            future_to_peer = {
                executor.submit(self._send_block_to_peer, peer, block_data): peer
                for peer in self.peers
            }

            # Собираем результаты по мере завершения
            for future in as_completed(future_to_peer):
                results.append(future.result())

        return results

    def get_peer_status(self, peer_url: str) -> dict:
        """
        Запрашивает статус пира (Раздел 6, pull-модель).
        """
        url = f"{peer_url}/status"
        try:
            response = requests.get(url, timeout=self.timeout)
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

    def get_peer_block(self, peer_url: str, index: int) -> dict:
        """
        Запрашивает у пира конкретный блок по индексу (Раздел 6).
        """
        url = f"{peer_url}/blocks/{index}"
        try:
            response = requests.get(url, timeout=self.timeout)
            if response.status_code == 200:
                return response.json()
            return {"error": f"HTTP {response.status_code}"}
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}