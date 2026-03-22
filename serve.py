#!/usr/bin/env python3
"""
Simple HTTPS server for Clear Sky Viewer.
Generates a self-signed certificate so iOS Safari allows motion sensor access.

Usage:
  python3 serve.py

Then open on your phone:
  https://<your-computer-ip>:8443/fourthversion.html

Your phone will warn about the certificate — tap "Show Details" then "Visit this website".
"""

import http.server
import ssl
import os
import subprocess
import sys

PORT = 8443
DIR = os.path.dirname(os.path.abspath(__file__))
CERT_FILE = os.path.join(DIR, 'cert.pem')
KEY_FILE = os.path.join(DIR, 'key.pem')

def generate_cert():
    """Generate a self-signed certificate if one doesn't exist."""
    if os.path.exists(CERT_FILE) and os.path.exists(KEY_FILE):
        print(f"Using existing certificate: {CERT_FILE}")
        return

    print("Generating self-signed SSL certificate...")
    subprocess.run([
        'openssl', 'req', '-x509', '-newkey', 'rsa:2048',
        '-keyout', KEY_FILE, '-out', CERT_FILE,
        '-days', '365', '-nodes',
        '-subj', '/CN=SkyViewer/O=ClearSky/C=US'
    ], check=True, capture_output=True)
    print(f"Certificate created: {CERT_FILE}")

def get_local_ip():
    """Try to find the local network IP."""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return 'localhost'

if __name__ == '__main__':
    os.chdir(DIR)
    generate_cert()

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(CERT_FILE, KEY_FILE)

    server = http.server.HTTPServer(('0.0.0.0', PORT), http.server.SimpleHTTPRequestHandler)
    server.socket = context.wrap_socket(server.socket, server_side=True)

    ip = get_local_ip()
    print(f"\n{'='*50}")
    print(f"  Clear Sky Viewer — HTTPS Server")
    print(f"{'='*50}")
    print(f"\n  On this computer:")
    print(f"    https://localhost:{PORT}/fourthversion.html")
    print(f"\n  On your phone (same WiFi):")
    print(f"    https://{ip}:{PORT}/fourthversion.html")
    print(f"\n  First time on iPhone:")
    print(f"    1. Safari will warn about the certificate")
    print(f"    2. Tap 'Show Details'")
    print(f"    3. Tap 'visit this website'")
    print(f"    4. Tap 'Visit Website' to confirm")
    print(f"    5. Now Compass mode will work!")
    print(f"\n  Press Ctrl+C to stop\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()
