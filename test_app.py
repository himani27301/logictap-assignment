import json
import sqlite3
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from app import make_server

PAYLOAD = {'call_id': 'abc123', 'status': 'answered', 'duration_secs': 42}


class CallServiceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.directory.name) / 'calls.db')
        self.start_server()

    def start_server(self):
        self.server = make_server(self.db_path, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f'http://127.0.0.1:{self.server.server_port}'

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def tearDown(self):
        self.stop_server()
        self.directory.cleanup()

    def request(self, path, body=None, raw=None):
        data = raw if raw is not None else (
            json.dumps(body).encode() if body is not None else None)
        req = Request(self.url + path, data=data,
                      headers={'Content-Type': 'application/json'})
        try:
            response = urlopen(req, timeout=15)
        except HTTPError as error:
            response = error
        with response:
            return response.status, json.load(response)

    def count(self):
        with closing(sqlite3.connect(self.db_path)) as db:
            return db.execute('SELECT COUNT(*) FROM calls').fetchone()[0]

    def test_repeated_request_stores_one_record(self):
        for duplicate in (False, True):
            self.assertEqual(self.request('/call-ended', PAYLOAD),
                             (200, {'ok': True, 'duplicate': duplicate}))
        self.assertEqual(self.count(), 1)
        self.assertEqual(self.request('/calls/abc123'), (200, PAYLOAD))

    def test_concurrent_deliveries_store_one_record(self):
        barrier = threading.Barrier(12)
        def send(_):
            barrier.wait(timeout=10)
            return self.request('/call-ended', PAYLOAD)
        with ThreadPoolExecutor(max_workers=12) as pool:
            results = list(pool.map(send, range(12)))
        self.assertTrue(all(status == 200 for status, _ in results))
        self.assertEqual(sum(not body['duplicate'] for _, body in results), 1)
        self.assertEqual(self.count(), 1)

    def test_restart_preserves_record_and_deduplication(self):
        self.request('/call-ended', PAYLOAD)
        self.stop_server()
        self.start_server()
        self.assertEqual(self.request('/call-ended', PAYLOAD),
                         (200, {'ok': True, 'duplicate': True}))
        self.assertEqual(self.request('/calls/abc123'), (200, PAYLOAD))
        self.assertEqual(self.count(), 1)

    def test_changed_duplicate_keeps_first_record(self):
        self.request('/call-ended', PAYLOAD)
        self.assertEqual(self.request('/call-ended', dict(PAYLOAD, duration_secs=99)),
                         (200, {'ok': True, 'duplicate': True}))
        self.assertEqual(self.request('/calls/abc123'), (200, PAYLOAD))
        self.assertEqual(self.count(), 1)

    def test_missing_call_id_is_rejected_without_insert(self):
        self.assertEqual(self.request('/call-ended', {'status': 'answered'}),
                         (400, {'error': 'call_id must be a non-empty string'}))
        self.assertEqual(self.count(), 0)

    def test_malformed_json_returns_clear_error(self):
        self.assertEqual(self.request('/call-ended', raw=b'{'),
                         (400, {'error': 'Invalid JSON or Content-Length'}))
        self.assertEqual(self.count(), 0)

    def test_invalid_fields_do_not_create_records(self):
        for body in [[], dict(PAYLOAD, call_id=' '), dict(PAYLOAD, call_id=123),
                     dict(PAYLOAD, duration_secs=True), dict(PAYLOAD, duration_secs=-1),
                     dict(PAYLOAD, status='')]:
            with self.subTest(body=body):
                self.assertEqual(self.request('/call-ended', body)[0], 400)
        self.assertEqual(self.count(), 0)

    def test_unknown_call_returns_404(self):
        self.assertEqual(self.request('/calls/missing'),
                         (404, {'error': 'Call not found'}))


if __name__ == '__main__':
    unittest.main(verbosity=2)
