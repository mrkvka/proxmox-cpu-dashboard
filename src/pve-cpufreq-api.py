#!/usr/bin/env python3
"""Tiny HTTP API for Proxmox CPU frequency control. Runs on port 8087."""
import http.server
import json
import subprocess
import urllib.parse

class CPUFreqHandler(http.server.BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.send_header('Content-Length', '0')
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode() if length > 0 else ''
        params = urllib.parse.parse_qs(body)
        # Also check query string
        if '?' in self.path:
            params.update(urllib.parse.parse_qs(self.path.split('?', 1)[1]))

        gov = params.get('governor', [''])[0]
        freq = params.get('max_freq', [''])[0]

        try:
            result = subprocess.run(
                ['/usr/local/bin/pve-cpufreq-set.sh', gov, freq],
                capture_output=True, text=True, timeout=5
            )
            resp = json.dumps({"success": True, "message": result.stdout.strip()})
            self.send_response(200)
        except Exception as e:
            resp = json.dumps({"success": False, "error": str(e)})
            self.send_response(500)

        self._cors()
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(resp)))
        self.end_headers()
        self.wfile.write(resp.encode())

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def log_message(self, format, *args):
        pass  # silent

if __name__ == '__main__':
    server = http.server.HTTPServer(('0.0.0.0', 8087), CPUFreqHandler)
    print("CPU Freq API listening on 127.0.0.1:8087")
    server.serve_forever()
