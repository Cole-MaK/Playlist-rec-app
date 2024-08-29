from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse

# Create a handler to capture the authorization code
class SpotifyAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_path.query)
        if 'code' in query_params:
            self.server.auth_code = query_params['code'][0]
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'Authorization successful. You can close this window.')
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'Authorization failed. No code found.')
