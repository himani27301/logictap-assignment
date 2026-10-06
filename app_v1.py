import json
from http.server import BaseHTTPRequestHandler, HTTPServer

calls = {}

class Handler(BaseHTTPRequestHandler):
    def reply(self, status, body):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if self.path != '/call-ended':
            return self.reply(404, {'error': 'Not found'})
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if not body.get('call_id'):
            return self.reply(400, {'error': 'call_id is required'})
        calls.setdefault(body['call_id'], body)
        self.reply(200, {'ok': True})

    def do_GET(self):
        call_id = self.path.removeprefix('/calls/')
        if self.path.startswith('/calls/') and call_id in calls:
            return self.reply(200, calls[call_id])
        self.reply(404, {'error': 'Call not found'})

if __name__ == '__main__':
    HTTPServer(('127.0.0.1', 8000), Handler).serve_forever()
