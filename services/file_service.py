import hashlib
import os


class FileService:
    """
    Сервис для проверки внешних файлов (FR-16, NFR-07).
    Читает файл потоково, чтобы не загружать в память целиком.
    """

    @staticmethod
    def verify_external_file(file_path: str, expected_hash: str) -> tuple:
        """
        Проверяет соответствие файла сохранённому хэшу.

        Args:
            file_path: путь к файлу на диске
            expected_hash: ожидаемый SHA-256 хэш (из транзакции)
        """
        if not os.path.exists(file_path):
            return False, f"Файл не найден: {file_path}"

        sha256 = hashlib.sha256()

        with open(file_path, 'rb') as f:
            while chunk := f.read(65536):
                sha256.update(chunk)

        actual_hash = sha256.hexdigest()

        if actual_hash == expected_hash:
            return True, "Хэш файла совпадает"
        else:
            return False, (
                f"Хэш не совпадает. "
                f"Ожидалось: {expected_hash}, "
                f"получено: {actual_hash}"
            )