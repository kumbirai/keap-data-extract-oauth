"""Interactive CLI tool for OAuth2 authorization."""
import logging
import sys
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from threading import Thread
import time

from src.auth.oauth2_client import OAuth2Client, OAuth2Error
from src.auth.token_manager import TokenManager
from src.database.config import SessionLocal
from src.utils.config import validate_config, get_config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class CallbackHandler(BaseHTTPRequestHandler):
    """HTTP request handler for OAuth2 callback."""
    
    def __init__(self, *args, authorization_code=None, **kwargs):
        self.authorization_code = authorization_code
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET request from OAuth2 callback."""
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        
        if 'code' in params:
            code = params['code'][0]
            self.authorization_code.append(code)
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'''
                <html>
                <head><title>Authorization Successful</title></head>
                <body>
                    <h1>Authorization Successful!</h1>
                    <p>You can close this window and return to the terminal.</p>
                </body>
                </html>
            ''')
        elif 'error' in params:
            error = params['error'][0]
            error_description = params.get('error_description', [''])[0]
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(f'''
                <html>
                <head><title>Authorization Failed</title></head>
                <body>
                    <h1>Authorization Failed</h1>
                    <p>Error: {error}</p>
                    <p>Description: {error_description}</p>
                </body>
                </html>
            '''.encode())
            self.authorization_code.append(None)
        else:
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<html><body><h1>Invalid callback</h1></body></html>')
            self.authorization_code.append(None)
    
    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


def create_callback_handler(authorization_code):
    """Create callback handler factory."""
    def handler(*args, **kwargs):
        return CallbackHandler(*args, authorization_code=authorization_code, **kwargs)
    return handler


def start_callback_server(port: int, authorization_code: list) -> HTTPServer:
    """Start temporary HTTP server for OAuth2 callback.
    
    Args:
        port: Port number to listen on
        authorization_code: List to store authorization code
        
    Returns:
        HTTPServer instance
    """
    handler = create_callback_handler(authorization_code)
    server = HTTPServer(('localhost', port), handler)
    
    def run_server():
        server.serve_forever()
    
    thread = Thread(target=run_server, daemon=True)
    thread.start()
    
    return server


def main():
    """Main authorization flow."""
    try:
        # Validate configuration
        logger.info("Validating configuration...")
        validate_config()
        config = get_config()
        
        # Extract redirect URI and parse port
        redirect_uri = config['keap_redirect_uri']
        parsed_uri = urlparse(redirect_uri)
        
        # Determine port from redirect URI
        if parsed_uri.port:
            port = parsed_uri.port
        elif parsed_uri.scheme == 'https':
            port = 443
        else:
            port = 80
        
        # For localhost, use a specific port (e.g., 8080)
        if 'localhost' in parsed_uri.netloc or '127.0.0.1' in parsed_uri.netloc:
            # Extract port from redirect URI or use default
            if ':' in parsed_uri.netloc:
                port = int(parsed_uri.netloc.split(':')[1])
            else:
                port = 8080
            # Update redirect URI to use localhost with port
            redirect_uri = f"http://localhost:{port}/oauth/callback"
            logger.info(f"Using localhost redirect URI: {redirect_uri}")
        
        # Initialize database session
        db = SessionLocal()
        
        try:
            # Initialize token manager and OAuth2 client
            token_manager = TokenManager(db)
            oauth2_client = OAuth2Client(token_manager)
            token_manager.set_oauth2_client(oauth2_client)
            
            # Check if tokens already exist
            client_id = config['keap_client_id']
            if token_manager.has_valid_tokens(client_id):
                logger.info("Valid tokens already exist. Use --force to re-authorize.")
                response = input("Do you want to re-authorize? (y/N): ")
                if response.lower() != 'y':
                    logger.info("Authorization cancelled.")
                    return
            
            # Generate authorization URL
            logger.info("Generating authorization URL...")
            auth_url = oauth2_client.get_authorization_url()
            
            # Start callback server
            logger.info(f"Starting callback server on port {port}...")
            authorization_code = []
            server = start_callback_server(port, authorization_code)
            
            # Give server time to start
            time.sleep(1)
            
            # Open browser
            logger.info("Opening browser for authorization...")
            logger.info(f"If browser doesn't open, visit: {auth_url}")
            try:
                webbrowser.open(auth_url)
            except Exception as e:
                logger.warning(f"Could not open browser automatically: {e}")
                logger.info(f"Please visit this URL in your browser: {auth_url}")
            
            # Wait for callback
            logger.info("Waiting for authorization callback...")
            logger.info("Please authorize the application in your browser.")
            
            timeout = 300  # 5 minutes
            start_time = time.time()
            
            while not authorization_code and (time.time() - start_time) < timeout:
                time.sleep(1)
            
            # Stop server
            server.shutdown()
            
            if not authorization_code:
                logger.error("Authorization timeout. No callback received.")
                sys.exit(1)
            
            code = authorization_code[0]
            if code is None:
                logger.error("Authorization failed. Check the error in your browser.")
                sys.exit(1)
            
            # Exchange code for tokens
            logger.info("Exchanging authorization code for tokens...")
            token_data = oauth2_client.exchange_code_for_tokens(code)
            
            logger.info("Authorization successful! Tokens have been stored.")
            logger.info(f"Access token expires in: {token_data.get('expires_in', 'unknown')} seconds")
            
        finally:
            db.close()
            
    except KeyboardInterrupt:
        logger.info("\nAuthorization cancelled by user.")
        sys.exit(1)
    except OAuth2Error as e:
        logger.error(f"OAuth2 error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()

