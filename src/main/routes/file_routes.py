"""Serves files behind a locally-signed URL.

Only reachable with storage_backend="local". With S3 the browser fetches the
object straight from the provider using its presigned URL and this route is
never called.

The authorization decision does NOT happen here. It happened when the caller
asked for the URL — RefundFinder/ReceiptFinder checked owner-or-admin before
minting one. This route only verifies that the signature is valid, unexpired,
and issued for exactly this file. That is the trade Item 22 makes: permission
moves from "re-checked on every request" to "frozen in a link that expires in
FILE_URL_TTL_SECONDS".
"""
import mimetypes
import os
from fastapi import APIRouter, HTTPException, Query, Response
import jwt
from src.drivers.jwt_handler import JwtHandler
from src.drivers.storage_factory import LOCAL_DIRECTORIES, build_storage


file_routes = APIRouter(tags=["Files"])


@file_routes.get("/files/{storage}/{filename}")
async def serve_signed_file(storage: str, filename: str, token: str = Query(...)):
    try:
        claims = JwtHandler().decode_jwt_token(token)
    except jwt.PyJWTError as exception:
        # Expired and forged are answered identically. Saying "expired" would
        # confirm the file exists to someone holding a stale link.
        raise HTTPException(status_code=404, detail="File not found") from exception

    # The token must have been issued for THIS file. Without this check a valid
    # token for any file would read every file, which is the classic way a
    # signed URL scheme leaks everything at once.
    if claims.get("storage") != storage or claims.get("file") != filename:
        raise HTTPException(status_code=404, detail="File not found")

    # Belt and braces: `storage` already had to match a signed claim, and
    # build_storage only accepts known names. A filename containing a path
    # separator could still walk out of the directory, so it is refused
    # outright rather than sanitised.
    if storage not in LOCAL_DIRECTORIES or os.path.basename(filename) != filename:
        raise HTTPException(status_code=404, detail="File not found")

    try:
        content = build_storage(storage).read(filename)
    except FileNotFoundError as exception:
        raise HTTPException(status_code=404, detail="File not found") from exception

    media_type, _ = mimetypes.guess_type(filename)
    return Response(
        content=content,
        media_type=media_type or "application/octet-stream",
        # The URL already expires; letting a shared cache keep a copy longer
        # than the signature lives would quietly extend the grant.
        headers={"Cache-Control": "private, max-age=60"},
    )
