import os

database_info = {
    "DATABASE_URL": os.getenv("DATABASE_URL")
}

upload_info = {
    "UPLOAD_DIR": os.getenv("UPLOAD_DIR", "uploads/receipts"),
    "AVATAR_DIR": os.getenv("AVATAR_DIR", "uploads/avatars"),
    "PAYMENT_DIR": os.getenv("PAYMENT_DIR", "uploads/payment_receipts"),
    "MAX_FILE_SIZE_BYTES": 4 * 1024 * 1024,
}

jwt_info = {
    "KEY": os.getenv("JWT_SECRET"),
    "ALGORITHM": os.getenv("JWT_ALGORITHM", "HS256"),
    "EXPIRATION_TIME": int(os.getenv("JWT_EXPIRATION_HOURS", "8")),
}
