"""The receipt agent's HTTP gate: the key check, the request size limit and no-store answers (ASGI middleware).

Infrastructure of the receipt agent, wrapped around every route by the composition root (server.py). The SDK
declares the card's security scheme but doesn't check it (D197), so this does, before the JSON-RPC route reads
anything: a request without "Authorization: Bearer <RECEIPT_AGENT_KEY>" gets a 401, one without a Content-Length or
larger than MAX_REQUEST_BYTES a 411 or 413. Only the Agent Card is open. Every answer carries
Cache-Control: no-store, because it may hold what a receipt says.
"""

import hmac
from http import HTTPStatus

from pydantic import SecretStr
from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from receipt.contract import MAX_RECEIPT_BYTES

# A JSON-RPC request carries the file as base64 (4 bytes for every 3), plus the request's data and the envelope.
BASE64_GROWTH = 4 / 3
ENVELOPE_BYTES = 64 * 1024
MAX_REQUEST_BYTES = int(MAX_RECEIPT_BYTES * BASE64_GROWTH) + ENVELOPE_BYTES

NO_STORE = "no-store"
# Why a request was refused (English, for the client's log; never shown to a person).
NO_KEY = "a valid bearer key is required"
NO_LENGTH = "Content-Length is required"
TOO_LARGE = f"the request is over {MAX_REQUEST_BYTES} bytes"
ASK_FOR_BEARER = {"WWW-Authenticate": "Bearer"}


class AgentGate:
    """Checks the key and the size of every request but those to `open_paths`, and marks every answer no-store."""

    def __init__(self, app: ASGIApp, key: SecretStr, open_paths: frozenset[str]) -> None:
        """Wrap `app`; `key` is the shared key, `open_paths` the paths anyone may read (the Agent Card)."""
        self._app = app
        self._expected = f"Bearer {key.get_secret_value()}".encode()
        self._open_paths = open_paths

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Answer 401, 411 or 413 at once if the request may not go on; otherwise pass it on, marked no-store."""
        if scope["type"] != "http":  # lifespan events pass through
            await self._app(scope, receive, send)
            return
        refusal = None if scope["path"] in self._open_paths else self._refusal(Headers(scope=scope))
        if refusal is not None:
            await refusal(scope, receive, _no_store(send))
            return
        await self._app(scope, receive, _no_store(send))

    def _refusal(self, headers: Headers) -> JSONResponse | None:
        """The answer that refuses this request, or None if it may go on."""
        # compare_digest takes the same time wherever the first difference is, so the key can't be guessed by timing.
        if not hmac.compare_digest(headers.get("authorization", "").encode(), self._expected):
            return JSONResponse({"error": NO_KEY}, HTTPStatus.UNAUTHORIZED, ASK_FOR_BEARER)
        length = headers.get("content-length")
        if length is None or not length.isdigit():
            return JSONResponse({"error": NO_LENGTH}, HTTPStatus.LENGTH_REQUIRED)
        if int(length) > MAX_REQUEST_BYTES:
            return JSONResponse({"error": TOO_LARGE}, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
        return None


def _no_store(send: Send) -> Send:
    """`send`, with Cache-Control: no-store added to the answer's headers."""

    async def sending(message: Message) -> None:
        """Pass `message` on, adding the header to the start of the answer."""
        if message["type"] == "http.response.start":
            MutableHeaders(scope=message)["Cache-Control"] = NO_STORE
        await send(message)

    return sending
