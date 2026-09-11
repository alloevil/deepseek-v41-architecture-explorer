#!/usr/bin/env python3
"""Static server for the V4.1 architecture viewer.

python -m http.server lets browsers reuse a cached copy of index.html, which made
iterations look stale. Send no-store for text assets so a plain reload always wins.
"""
import http.server
import socketserver
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8741
NOCACHE = ('.html', '.js', '.css', '.json')


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        if self.path.endswith(NOCACHE) or '?' in self.path:
            self.send_header('Cache-Control', 'no-store, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
        super().end_headers()

    def log_message(self, fmt, *args):  # quiet by default
        pass


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


with Server(('0.0.0.0', PORT), Handler) as httpd:
    print(f'serving on :{PORT} (no-store for text assets)')
    httpd.serve_forever()
