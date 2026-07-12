import os
import uuid
from src.configs.global_config import upload_info
from .interfaces.receipt_storage_interface import ReceiptStorageInterface


class ReceiptStorage(ReceiptStorageInterface):
    def save(self, original_filename: str, content: bytes) -> str:
        extension = os.path.splitext(original_filename)[1]
        unique_filename = f"{uuid.uuid4()}{extension}"
        path = os.path.join(upload_info["UPLOAD_DIR"], unique_filename)

        with open(path, "wb") as file:
            file.write(content)

        return unique_filename

    def delete(self, filename: str) -> None:
        path = os.path.join(upload_info["UPLOAD_DIR"], filename)
        if os.path.exists(path):
            os.remove(path)
