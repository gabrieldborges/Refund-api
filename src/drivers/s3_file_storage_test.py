"""Unit tests for S3FileStorage's presigned URL host — no MinIO involved.

boto3 signs a presigned URL locally, without any network round trip, so fake
credentials are enough to assert on the resulting host. That is what lets
these run in the mocked suite instead of the integration one.
"""
from urllib.parse import urlparse
from src.configs.settings import settings
from src.drivers.s3_file_storage import S3FileStorage


# Real AWS, a region other than us-east-1, no custom endpoint. Before the fix,
# boto3 signs for the region but addresses the global host
# (bucket.s3.amazonaws.com). S3 then answers a redirect to the regional host,
# and because the signature covers `host`, it no longer matches after the
# redirect — the object never loads. Asserting on the region appearing in the
# host (not the full string) keeps this from becoming a copy of the fix.
def test_real_aws_presigned_url_addresses_the_regional_host(monkeypatch):
    monkeypatch.setattr(settings, "s3_bucket", "refund-bucket")
    monkeypatch.setattr(settings, "s3_endpoint_url", "")
    monkeypatch.setattr(settings, "s3_region", "us-east-2")
    monkeypatch.setattr(settings, "s3_access_key_id", "fake-key")
    monkeypatch.setattr(
        settings, "s3_secret_access_key", type(settings.s3_secret_access_key)("fake-secret")
    )

    url = S3FileStorage("receipts").get_url("receipt.png")

    assert "us-east-2" in urlparse(url).netloc


# MinIO has no wildcard DNS, so the fix's virtual-addressing config must only
# apply when there is no custom endpoint. This is the guard that keeps the
# AWS fix from turning a working MinIO URL (localhost:9100/bucket/...) into
# one that does not resolve (bucket.localhost:9100).
def test_custom_endpoint_keeps_addressing_the_endpoint_host(monkeypatch):
    monkeypatch.setattr(settings, "s3_bucket", "receipts-bucket")
    monkeypatch.setattr(settings, "s3_endpoint_url", "http://localhost:9100")
    monkeypatch.setattr(settings, "s3_region", "us-east-1")
    monkeypatch.setattr(settings, "s3_access_key_id", "fake-key")
    monkeypatch.setattr(
        settings, "s3_secret_access_key", type(settings.s3_secret_access_key)("fake-secret")
    )

    url = S3FileStorage("receipts").get_url("receipt.png")

    host = urlparse(url).netloc
    assert host == "localhost:9100"
    assert not host.startswith("receipts-bucket.")
