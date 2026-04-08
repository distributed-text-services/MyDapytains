"""
Parallel-worker tests for the Flask app.

Strategy: spawn 2 Flask server subprocesses on separate ports (simulating 2
gunicorn prefork workers — each has its own Python process and JVM instance),
then hammer both with concurrent HTTP requests via requests + ThreadPoolExecutor.

NOTE: Saxon's C/JVM bindings are NOT thread-safe; concurrent Saxon calls from
the *same* process will crash.  The safe parallelism model is one OS process per
concurrent client, which is exactly what prefork servers (gunicorn, uwsgi) use.
These tests exercise that model directly.
"""
import concurrent.futures
import os
import socket
import sys
import tempfile
import time
import urllib.parse

import pytest
import requests

_basedir = os.path.abspath(os.path.dirname(__file__))
_project_root = os.path.dirname(_basedir)
_catalog = os.path.join(_basedir, "catalog", "example-collection.xml")

# Resources present in the test catalog
_RESOURCE_TEXT    = "https://foo.bar/text"            # base_tei.xml  (Luke/Mark)
_RESOURCE_MULTI   = "https://example.org/resource1"   # multiple_tree.xml

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


_SERVER_SCRIPT = """\
import sys, os
sys.path.insert(0, sys.argv[1])          # project root
port     = int(sys.argv[2])
db_path  = sys.argv[3]
catalog  = sys.argv[4]

from flask import Flask
from dapytains.app.app import create_app
from dapytains.app.ingest import store_catalog
from dapytains.metadata.xml_parser import parse

app = Flask(__name__)
app, db = create_app(app)
app.config["SQLALCHEMY_DATABASE_URI"]      = f"sqlite:///{db_path}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

with app.app_context():
    db.create_all()
    catalog_data, _ = parse(catalog)
    store_catalog(catalog_data)

# threaded=False: one request at a time per process — safe with Saxon
app.run(host="127.0.0.1", port=port, threaded=False, use_reloader=False)
"""


def _start_server(port: int, db_path: str):
    """Spawn a Flask server subprocess and return the Popen handle."""
    import subprocess
    return subprocess.Popen(
        [sys.executable, "-c", _SERVER_SCRIPT,
         _project_root, str(port), db_path, _catalog],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _wait_ready(port: int, retries: int = 30, delay: float = 0.3) -> None:
    """Poll until the server accepts connections or raise TimeoutError."""
    for _ in range(retries):
        try:
            requests.get(f"http://127.0.0.1:{port}/", timeout=1)
            return
        except requests.exceptions.ConnectionError:
            time.sleep(delay)
    raise TimeoutError(f"Server on port {port} did not start in time")


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def two_workers():
    """Start 2 Flask worker processes and yield their base URLs."""
    import subprocess

    tmpdir = tempfile.mkdtemp()
    port1, port2 = _free_port(), _free_port()
    db1 = os.path.join(tmpdir, "worker1.db")
    db2 = os.path.join(tmpdir, "worker2.db")

    proc1 = _start_server(port1, db1)
    proc2 = _start_server(port2, db2)

    try:
        _wait_ready(port1)
        _wait_ready(port2)
        yield [f"http://127.0.0.1:{port1}", f"http://127.0.0.1:{port2}"]
    finally:
        proc1.terminate()
        proc2.terminate()
        proc1.wait(timeout=10)
        proc2.wait(timeout=10)


# ─────────────────────────────────────────────────────────────────────────────
# Reference responses (computed against a single worker during setup)
# ─────────────────────────────────────────────────────────────────────────────

def _doc_url(base: str, resource: str, **kwargs) -> str:
    params = {"resource": resource, **kwargs}
    return f"{base}/document/?{urllib.parse.urlencode(params)}"


def _nav_url(base: str, resource: str, **kwargs) -> str:
    params = {"resource": resource, **kwargs}
    return f"{base}/navigation/?{urllib.parse.urlencode(params)}"


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestTwoWorkersParallel:

    def test_workers_are_up(self, two_workers):
        """Both workers answer the entry-point."""
        for base in two_workers:
            r = requests.get(f"{base}/")
            assert r.status_code == 200
            assert "collection" in r.json()

    def test_sequential_passages_per_worker(self, two_workers):
        """Each worker handles N sequential document requests correctly."""
        refs = ["Luke 1:1", "Luke 1:2", "Mark 1:1"]
        for base in two_workers:
            responses = [
                requests.get(_doc_url(base, _RESOURCE_TEXT, ref=ref))
                for ref in refs
            ]
            for r in responses:
                assert r.status_code == 200
                assert r.content  # non-empty XML

    def test_parallel_requests_to_both_workers(self, two_workers):
        """Send 20 document requests distributed across both workers in parallel.

        Requests use threads only for HTTP I/O; Saxon runs inside separate server
        processes so there is no intra-process concurrency on the JVM.
        """
        resource = _RESOURCE_TEXT
        ref      = "Luke 1:1"
        urls = [_doc_url(base, resource, ref=ref) for base in two_workers] * 10

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(requests.get, urls))

        assert all(r.status_code == 200 for r in results), [
            r.text for r in results if r.status_code != 200
        ]
        # All responses must be identical XML
        bodies = [r.text for r in results]
        assert all(b == bodies[0] for b in bodies), "inconsistent XML across workers"

    def test_parallel_range_requests(self, two_workers):
        """Range passages delivered in parallel from both workers are consistent."""
        urls = [
            _doc_url(base, _RESOURCE_TEXT, start="Luke 1:1", end="Luke 1#1")
            for base in two_workers
        ] * 8

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(requests.get, urls))

        assert all(r.status_code == 200 for r in results)
        bodies = [r.text for r in results]
        assert all(b == bodies[0] for b in bodies), "range XML must be identical across workers"

    def test_parallel_navigation_requests(self, two_workers):
        """Navigation endpoint delivers consistent results in parallel from both workers."""
        urls = [_nav_url(base, _RESOURCE_TEXT, down=1) for base in two_workers] * 8

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(requests.get, urls))

        assert all(r.status_code == 200 for r in results)
        # member identifiers must be identical across workers
        member_sets = [
            {m["identifier"] for m in r.json().get("member", [])}
            for r in results
        ]
        assert all(m == member_sets[0] for m in member_sets)

    def test_parallel_mixed_requests(self, two_workers):
        """Mix of single-passage, range, and navigation requests in parallel."""
        base1, base2 = two_workers
        urls = (
            [_doc_url(base1, _RESOURCE_TEXT, ref="Luke 1:1")] * 4
            + [_doc_url(base2, _RESOURCE_TEXT, ref="Luke 1:2")] * 4
            + [_doc_url(base1, _RESOURCE_TEXT, start="Luke 1:1", end="Luke 1#1")] * 4
            + [_nav_url(base2, _RESOURCE_TEXT, down=1)] * 4
        )

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(requests.get, urls))

        assert all(r.status_code == 200 for r in results), [
            (r.url, r.status_code, r.text[:120]) for r in results if r.status_code != 200
        ]

    def test_repeated_parallel_bursts(self, two_workers):
        """Run several bursts of parallel requests; state must stay consistent between bursts."""
        resource = _RESOURCE_TEXT
        ref      = "Luke 1:1"
        urls = [_doc_url(base, resource, ref=ref) for base in two_workers] * 5

        reference_body = None
        for burst in range(3):
            with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
                results = list(pool.map(requests.get, urls))
            assert all(r.status_code == 200 for r in results), f"burst {burst} had failures"
            burst_body = results[0].text
            if reference_body is None:
                reference_body = burst_body
            assert all(r.text == reference_body for r in results), (
                f"burst {burst}: response drifted from the reference"
            )
