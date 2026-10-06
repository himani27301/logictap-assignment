import json, sqlite3, tempfile, threading, unittest
from contextlib import closing
from pathlib import Path
from urllib.request import Request, urlopen
from app import make_server

class DuplicateTest(unittest.TestCase):
    def test_duplicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / 'calls.db')
            server = make_server(path, port=0)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            url = f'http://127.0.0.1:{server.server_port}'
            body = {'call_id': 'abc123', 'status': 'answered', 'duration_secs': 42}
            try:
                for duplicate in (False, True):
                    req = Request(url + '/call-ended', json.dumps(body).encode(),
                                  {'Content-Type': 'application/json'})
                    with urlopen(req, timeout=5) as response:
                        self.assertEqual(response.status, 200)
                        self.assertEqual(json.load(response)['duplicate'], duplicate)
                with closing(sqlite3.connect(path)) as db:
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM calls').fetchone()[0], 1)
                with urlopen(url + '/calls/abc123', timeout=5) as response:
                    self.assertEqual(json.load(response), body)
            finally:
                server.shutdown(); server.server_close(); thread.join()

if __name__ == '__main__':
    unittest.main()
