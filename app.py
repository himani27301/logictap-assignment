"""Local webhook exercise; Python standard library only."""
import json
import os
import sqlite3
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlsplit


def make_server(db_path='calls.db', port=8000):
    def connect():
        return sqlite3.connect(db_path, timeout=10)

    with closing(connect()) as db, db:
        db.execute('CREATE TABLE IF NOT EXISTS calls '
                   '(call_id TEXT PRIMARY KEY NOT NULL, payload TEXT NOT NULL)')

    class Handler(BaseHTTPRequestHandler):
        def reply(self, status, body):
            data = json.dumps(body).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            if urlsplit(self.path).path != '/call-ended':
                return self.reply(404, {'error': 'Not found'})
            if self.headers.get_content_type() != 'application/json':
                return self.reply(415, {'error': 'Use application/json'})
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 65536:
                    return self.reply(400, {'error': 'Body must be 1-65536 bytes'})
                body = json.loads(self.rfile.read(size))
            except (ValueError, UnicodeDecodeError):
                return self.reply(400, {'error': 'Invalid JSON or Content-Length'})
            if not isinstance(body, dict):
                return self.reply(400, {'error': 'JSON body must be an object'})
            call_id = body.get('call_id')
            if not isinstance(call_id, str) or not call_id.strip():
                return self.reply(400, {'error': 'call_id must be a non-empty string'})
            status = body.get('status')
            duration = body.get('duration_secs')
            if not isinstance(status, str) or not status.strip():
                return self.reply(400, {'error': 'status must be a non-empty string'})
            if type(duration) is not int or duration < 0:
                return self.reply(400, {'error': 'duration_secs must be a non-negative integer'})
            record = dict(call_id=call_id, status=status, duration_secs=duration)
            try:
                with closing(connect()) as db, db:
                    cursor = db.execute(
                        'INSERT INTO calls (call_id, payload) VALUES (?, ?) '
                        'ON CONFLICT(call_id) DO NOTHING',
                        (call_id, json.dumps(record)))
                    duplicate = cursor.rowcount == 0
            except sqlite3.Error:
                return self.reply(503, {'error': 'Storage unavailable; retry later'})
            self.reply(200, {'ok': True, 'duplicate': duplicate})

        def do_GET(self):
            path = urlsplit(self.path).path
            if not path.startswith('/calls/') or not path[7:]:
                return self.reply(404, {'error': 'Not found'})
            call_id = unquote(path[7:])
            try:
                with closing(connect()) as db, db:
                    row = db.execute('SELECT payload FROM calls WHERE call_id = ?',
                                     (call_id,)).fetchone()
            except sqlite3.Error:
                return self.reply(503, {'error': 'Storage unavailable; retry later'})
            if row is None:
                return self.reply(404, {'error': 'Call not found'})
            self.reply(200, json.loads(row[0]))

    return ThreadingHTTPServer(('127.0.0.1', port), Handler)


if __name__ == '__main__':
    server = make_server(os.environ.get('CALLS_DB', 'calls.db'))
    print('Listening on http://127.0.0.1:8000', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
