"""ADR-001 update: a loopback connection owned by another OS user is refused.

The lookup reads /proc/net/tcp[6]; these tests feed it fabricated tables so
the "different user" branch runs without creating a second account.
"""
from __future__ import annotations

import os
import socket
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

from skillsmgr import web_security
from skillsmgr.web_security import RequestError, connection_owner_uid, require_same_user

HEADER = "  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode\n"


def _row(local: str, remote: str, uid: int) -> str:
    return f"   0: {local} {remote} 01 00000000:00000000 00:00000000 00000000  {uid}        0 1 1 0\n"


class PeerUserTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def _table(self, *rows: str) -> tuple[str, ...]:
        path = self.dir / "tcp"
        path.write_text(HEADER + "".join(rows), encoding="ascii")
        return (str(path),)

    def test_address_spelling_matches_the_kernel(self):
        self.assertEqual(web_security._proc_address("127.0.0.1", 8765), "0100007F:223D")
        self.assertEqual(
            web_security._proc_address("::1", 80), "00000000000000000000000001000000:0050"
        )
        self.assertIsNone(web_security._proc_address("not-an-ip", 1))

    def test_the_client_row_is_matched_not_the_servers(self):
        client, server = ("127.0.0.1", 40000), ("127.0.0.1", 8765)
        tables = self._table(
            _row("0100007F:223D", "0100007F:9C40", 1000),  # the server's accepted end
            _row("0100007F:9C40", "0100007F:223D", 4242),  # the client's end
        )
        self.assertEqual(connection_owner_uid(client, server, tables=tables), 4242)

    @unittest.skipUnless(hasattr(os, "getuid"), "POSIX uid")
    def test_another_users_connection_is_refused_and_unknown_is_allowed(self):
        client, server = ("127.0.0.1", 40000), ("127.0.0.1", 8765)
        other = self._table(_row("0100007F:9C40", "0100007F:223D", os.getuid() + 1))
        with self.assertRaises(RequestError) as caught:
            require_same_user(client, server, tables=other)
        self.assertEqual(caught.exception.status, 403)
        same = self._table(_row("0100007F:9C40", "0100007F:223D", os.getuid()))
        require_same_user(client, server, tables=same)
        require_same_user(client, server, tables=self._table())  # row not found
        require_same_user(client, server, tables=(str(self.dir / "missing"),))
        require_same_user(("garbage",), server, tables=same)

    @unittest.skipUnless(Path("/proc/net/tcp").exists(), "Linux /proc")
    def test_a_real_loopback_connection_belongs_to_this_user(self):
        listener = socket.socket()
        self.addCleanup(listener.close)
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        client = socket.create_connection(listener.getsockname())
        self.addCleanup(client.close)
        accepted, peer = listener.accept()
        self.addCleanup(accepted.close)
        self.assertEqual(connection_owner_uid(peer, accepted.getsockname()), os.getuid())

    def test_the_server_refuses_a_foreign_owner_and_serves_its_own(self):
        from smoke_fixtures import start_server, stop_server
        from skillsmgr.store import Store

        store = Store(self.dir / "data" / "skills-manager")
        store.init_db()
        server, thread = start_server(store)
        self.addCleanup(stop_server, server, thread)
        base = server.url.rstrip("/")
        with urllib.request.urlopen(base + "/api/scopes", timeout=10) as response:
            self.assertEqual(response.status, 200)
        with mock.patch.object(web_security, "connection_owner_uid", return_value=-7), \
                mock.patch.object(web_security.os, "getuid", return_value=1, create=True):
            with self.assertRaises(urllib.error.HTTPError) as caught:
                urllib.request.urlopen(base + "/api/scopes", timeout=10)
        self.assertEqual(caught.exception.code, 403)


if __name__ == "__main__":
    unittest.main()
