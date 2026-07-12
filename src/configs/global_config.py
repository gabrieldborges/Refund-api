import os

database_info = {
    "DATABASE_URL": os.getenv("DATABASE_URL")
}

upload_info = {
    "UPLOAD_DIR": os.getenv("UPLOAD_DIR", "uploads/receipts"),
    "MAX_FILE_SIZE_BYTES": 2 * 1024 * 1024,
    "ALLOWED_CONTENT_TYPES": ["image/jpeg", "image/png", "application/pdf"]
}

jwt_info = {
    "KEY": os.getenv("JWT_SECRET"),
    "ALGORITHM": os.getenv("JWT_ALGORITHM", "HS256"),
    "EXPIRATION_TIME": int(os.getenv("JWT_EXPIRATION_HOURS", "8")),
}
