"""Internal HTTP request-security policy helpers for the local web UI.

This module intentionally exposes a small, pure policy function.  The handler
still owns when the policy runs (before mutation routing) and the server still
owns the configured host/origin sets.
"""

from __future__ import annotations

import os
from typing import Mapping
from urllib.parse import urlparse

from .errors import StoreError


class RequestError(StoreError):
    """A clean HTTP error raised while validating an incoming request."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def validate_request(
    headers: Mapping[str, str],
    allowed_hosts: set[str],
    allowed_origins: set[str],
) -> None:
    """Validate the pre-handler policy for **every** request.

    Header-absent local CLI/test clients remain valid.  When browser-oriented
    headers are present, their values must match the loopback server configured
    by :class:`WebAppServer`.  This function does not inspect routes or bodies;
    callers remain responsible for JSON/content-type checks where applicable.

    SEC-1: this policy is not about *mutations*.  Applying it only to
    POST/PATCH/PUT/DELETE left every read route open to a hostile web page --
    an attacker-controlled ``Host`` plus cross-site Fetch Metadata still
    returned GET /api/skills and the full GET /api/export archive, and the
    response was readable because the browser only enforces CORS on reads that
    are not "simple".  Reads leak the user's whole skill library, so they need
    exactly the same gate.
    """

    host_header = headers.get("Host", "")
    if host_header not in allowed_hosts:
        raise RequestError(403, "invalid Host header")

    # .strip() as well as .lower(): the policy must accept only the exact
    # token, and a trailing space is not a different policy decision.
    fetch_site = (headers.get("Sec-Fetch-Site") or "").strip().lower()
    if fetch_site == "cross-site":
        raise RequestError(403, "cross-origin request rejected")

    origin = headers.get("Origin")
    referer = headers.get("Referer")
    for value, label in ((origin, "Origin"), (referer, "Referer")):
        if not value:
            continue
        parsed = urlparse(value)
        if label == "Referer":
            actual = f"{parsed.scheme}://{parsed.netloc}"
        else:
            actual = value.rstrip("/")
        if not parsed.scheme or actual.rstrip("/") not in allowed_origins:
            raise RequestError(403, "cross-origin request rejected")


# ---------------------------------------------------------------- peer user

_PROC_NET = ("/proc/net/tcp", "/proc/net/tcp6")


def _proc_address(host: str, port: int) -> str | None:
    """``host:port`` in ``/proc/net/tcp[6]`` spelling, or ``None`` if unparsable.

    The kernel prints each address as the raw 32-bit words of the network-order
    address, each formatted in host byte order (little-endian on every Linux
    platform this runs on), followed by the port in hex.
    """
    import socket

    for family, width in ((socket.AF_INET, 4), (socket.AF_INET6, 16)):
        try:
            raw = socket.inet_pton(family, host)
        except (OSError, ValueError):
            continue
        words = "".join(
            f"{int.from_bytes(raw[i:i + 4], 'little'):08X}" for i in range(0, width, 4)
        )
        return f"{words}:{port:04X}"
    return None


def connection_owner_uid(
    client: tuple, server: tuple, *, tables: tuple[str, ...] = _PROC_NET
) -> int | None:
    """The uid that owns the *client* end of a loopback TCP connection.

    Linux only, stdlib only: the client's socket is the ``/proc/net/tcp[6]``
    row whose local address is the client endpoint and whose remote address is
    the server endpoint; column 8 is its owner's uid.  ``None`` when that cannot
    be determined (no ``/proc``, another OS, an unparsable address, the row not
    found) -- callers must treat ``None`` as "unknown", never as a match.
    """
    try:
        local = _proc_address(str(client[0]), int(client[1]))
        remote = _proc_address(str(server[0]), int(server[1]))
    except (IndexError, TypeError, ValueError):
        return None
    if local is None or remote is None:
        return None
    for table in tables:
        try:
            with open(table, encoding="ascii", errors="replace") as handle:
                next(handle, None)  # header
                for line in handle:
                    fields = line.split()
                    if len(fields) > 7 and fields[1] == local and fields[2] == remote:
                        return int(fields[7])
        except (OSError, ValueError):
            continue
    return None


def require_same_user(client: tuple, server: tuple, *, tables: tuple[str, ...] = _PROC_NET) -> None:
    """Reject a connection that another local OS user opened (ADR-001 update).

    Loopback is reachable by *every* account on the machine, and the API can
    read the whole library and run the configured install runner.  Where the
    kernel says which uid owns the client socket (Linux), a different uid is a
    ``403``.  Unknown ownership keeps the pre-existing behaviour, so other
    platforms and restricted ``/proc`` mounts are unaffected.
    """
    getuid = getattr(os, "getuid", None)
    if getuid is None:
        return
    owner = connection_owner_uid(client, server, tables=tables)
    if owner is not None and owner != getuid():
        raise RequestError(403, "connection belongs to another local user")
