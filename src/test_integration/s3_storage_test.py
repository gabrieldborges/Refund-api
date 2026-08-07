# pylint: disable=w0621
# w0621: expected with pytest fixtures — a test parameter shares its name with
# the fixture function. Same disable, same reason, as the repository tests.
"""S3FileStorage against a real S3-compatible server (MinIO).

A mocked boto3 would prove we call put_object with the arguments we intended,
which is the same half-truth the mocked repository tests give for SQL. These
prove the object really lands in the bucket, that a presigned URL really works
without a credential, and that a missing key really becomes the
FileNotFoundError the controllers already catch.

Requires `docker compose up -d`.
"""
import os
import time
import urllib.error
import urllib.request
import boto3
import pytest
from src.configs.settings import settings
from src.drivers.s3_file_storage import S3FileStorage


BUCKET = "refund-integration"
ENDPOINT = os.getenv("TEST_S3_ENDPOINT", "http://localhost:9100")


@pytest.fixture
def s3_settings(monkeypatch):
    """Point the process-wide settings at MinIO for the duration of a test.

    S3FileStorage reads settings at call time, not at construction, so patching
    the attributes is enough — and monkeypatch puts them back afterwards, which
    keeps this from leaking into the tests that expect the local backend.
    """
    monkeypatch.setattr(settings, "storage_backend", "s3")
    monkeypatch.setattr(settings, "s3_bucket", BUCKET)
    monkeypatch.setattr(settings, "s3_endpoint_url", ENDPOINT)
    monkeypatch.setattr(settings, "s3_access_key_id", "refund_test")
    monkeypatch.setattr(
        settings, "s3_secret_access_key", type(settings.s3_secret_access_key)("refund_test_secret")
    )

    client = boto3.client(
        "s3",
        endpoint_url=ENDPOINT,
        region_name=settings.s3_region,
        aws_access_key_id="refund_test",
        aws_secret_access_key="refund_test_secret",
    )
    try:
        client.create_bucket(Bucket=BUCKET)
    except client.exceptions.BucketAlreadyOwnedByYou:
        pass
    except client.exceptions.BucketAlreadyExists:
        pass

    yield client

    # Buckets cannot be emptied in one call; a leftover object would leak into
    # the next test's listing assertions.
    objects = client.list_objects_v2(Bucket=BUCKET).get("Contents", [])
    for stored in objects:
        client.delete_object(Bucket=BUCKET, Key=stored["Key"])


@pytest.mark.integration
def test_save_puts_the_object_in_the_bucket_under_its_prefix(s3_settings):
    storage = S3FileStorage("receipts")

    filename = storage.save("receipt.png", b"real bytes")

    stored = s3_settings.get_object(Bucket=BUCKET, Key=f"receipts/{filename}")
    assert stored["Body"].read() == b"real bytes"


# The database column stores the bare filename in both backends, so switching
# one for the other must not require rewriting existing rows.
@pytest.mark.integration
def test_save_returns_a_bare_filename_not_a_key(s3_settings):  # pylint: disable=unused-argument
    storage = S3FileStorage("receipts")

    filename = storage.save("receipt.png", b"x")

    assert "/" not in filename
    assert filename.endswith(".png")


@pytest.mark.integration
def test_read_returns_what_save_wrote(s3_settings):  # pylint: disable=unused-argument
    storage = S3FileStorage("avatars")
    filename = storage.save("foto.jpg", b"avatar bytes")

    assert storage.read(filename) == b"avatar bytes"


# The controllers catch FileNotFoundError and turn it into their 404. A second
# backend raising botocore's ClientError instead would break that contract
# silently — the error would escape as a 500.
@pytest.mark.integration
def test_reading_a_missing_key_raises_file_not_found(s3_settings):  # pylint: disable=unused-argument
    storage = S3FileStorage("receipts")

    with pytest.raises(FileNotFoundError):
        storage.read("nao-existe.png")


@pytest.mark.integration
def test_delete_removes_the_object(s3_settings):
    storage = S3FileStorage("receipts")
    filename = storage.save("receipt.png", b"x")

    storage.delete(filename)

    assert s3_settings.list_objects_v2(Bucket=BUCKET).get("Contents", []) == []


# Matches the local backend, which checks os.path.exists first. Item 21's
# delete_quietly relies on deletion being forgiving.
@pytest.mark.integration
def test_deleting_a_missing_object_is_silent(s3_settings):  # pylint: disable=unused-argument
    S3FileStorage("receipts").delete("nunca-existiu.png")


# THE POINT OF THE ITEM: a browser fetches this with no credential and no
# header. Downloaded here with urllib precisely because urllib knows nothing
# about AWS — if it works there, an <img> tag works.
@pytest.mark.integration
def test_a_presigned_url_downloads_without_any_credential(s3_settings):  # pylint: disable=unused-argument
    storage = S3FileStorage("receipts")
    filename = storage.save("receipt.png", b"downloaded anonymously")

    url = storage.get_url(filename)

    with urllib.request.urlopen(url) as response:
        assert response.read() == b"downloaded anonymously"


# The bucket stays private. Without the signature the same object is refused,
# which is what separates this from the public URLs ADR-003 removed.
@pytest.mark.integration
def test_the_object_is_not_readable_without_the_signature(s3_settings):  # pylint: disable=unused-argument
    storage = S3FileStorage("receipts")
    filename = storage.save("receipt.png", b"secret")

    unsigned = f"{ENDPOINT}/{BUCKET}/receipts/{filename}"

    with pytest.raises(urllib.error.HTTPError) as error:
        with urllib.request.urlopen(unsigned):
            pass
    assert error.value.code in (401, 403)


# The permission must expire, or the signed URL is the permanent capability
# link this project already decided against once.
@pytest.mark.integration
def test_a_presigned_url_expires(s3_settings, monkeypatch):  # pylint: disable=unused-argument
    monkeypatch.setattr(settings, "file_url_ttl_seconds", 1)
    storage = S3FileStorage("receipts")
    filename = storage.save("receipt.png", b"x")

    url = storage.get_url(filename)
    time.sleep(2)

    with pytest.raises(urllib.error.HTTPError) as error:
        with urllib.request.urlopen(url):
            pass
    assert error.value.code == 403
