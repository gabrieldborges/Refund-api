import os
import uuid
import boto3
from botocore.exceptions import ClientError
from src.configs.settings import settings
from .interfaces.file_storage_interface import FileStorageInterface


class S3FileStorage(FileStorageInterface):
    """The same three operations, against an S3-compatible bucket.

    Why this exists: local disk ties a file to the instance that received it.
    Most PaaS filesystems are ephemeral, so every receipt would evaporate on
    redeploy — silently, since the database row and its filename survive and
    the download route would answer a plain 404.

    One bucket, three prefixes. `name` ("receipts", "avatars", "payments") is
    the prefix, mirroring the three directories the local backend uses. S3 has
    no folders: the slash is just part of the key.
    """

    def __init__(self, name: str) -> None:
        self.__prefix = name
        self.__bucket = settings.s3_bucket

    def __client(self):
        # Built per call rather than held on the instance. boto3 clients are
        # not documented as thread-safe to share, and creating one is cheap
        # compared to the network round trip that follows it.
        return boto3.client(
            "s3",
            # Empty endpoint means real AWS; anything else points at MinIO or
            # another S3-compatible provider.
            endpoint_url=settings.s3_endpoint_url or None,
            region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key.get_secret_value(),
        )

    def __key(self, filename: str) -> str:
        return f"{self.__prefix}/{filename}"

    def save(self, original_filename: str, content: bytes) -> str:
        extension = os.path.splitext(original_filename)[1]
        unique_filename = f"{uuid.uuid4()}{extension}"

        self.__client().put_object(
            Bucket=self.__bucket, Key=self.__key(unique_filename), Body=content
        )

        # Returns the bare filename, not the key: the database column stores
        # what the local backend also stores, so switching backends does not
        # rewrite existing rows.
        return unique_filename

    def read(self, filename: str) -> bytes:
        try:
            response = self.__client().get_object(
                Bucket=self.__bucket, Key=self.__key(filename)
            )
        except ClientError as error:
            # Translated to the exception the local backend raises, because the
            # controllers already catch FileNotFoundError and turn it into the
            # same 404 they use for "does not exist" and "not yours". A second
            # storage backend must not mean a second error contract.
            if error.response["Error"]["Code"] in ("NoSuchKey", "404"):
                raise FileNotFoundError(filename) from error
            raise

        return response["Body"].read()

    def delete(self, filename: str) -> None:
        # S3 delete_object is idempotent: removing a key that is not there
        # succeeds. That matches the local backend, which checks os.path.exists
        # first, so callers see the same behaviour either way.
        self.__client().delete_object(Bucket=self.__bucket, Key=self.__key(filename))

    def get_url(self, filename: str) -> str:
        # The bucket stays private. A presigned URL carries the permission in
        # its signature and expires, so the browser fetches the object directly
        # without ever holding a credential.
        return self.__client().generate_presigned_url(
            "get_object",
            Params={"Bucket": self.__bucket, "Key": self.__key(filename)},
            ExpiresIn=settings.file_url_ttl_seconds,
        )
