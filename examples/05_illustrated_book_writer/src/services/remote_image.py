import logging
import os
try:
    from sshtunnel import SSHTunnelForwarder
except ImportError:
    SSHTunnelForwarder = None

logger = logging.getLogger(__name__)

class RemoteImageProvider:
    """
    Manages SSH connection and tunneling for remote image generation.
    Wraps SSH logic to abstract it from the rest of the application.
    """
    def __init__(self, host, user, key_path, remote_port=8188, local_port=8189):
        self.host = host
        self.user = user
        self.key_path = key_path
        self.remote_port = remote_port
        self.local_port = local_port
        self.server = None
        self._is_connected = False

    def connect(self):
        """Establish SSH tunnel."""
        if not self.host or not self.user:
            logger.warning("SSH Host or User not configured. Skipping remote connection.")
            return

        if not SSHTunnelForwarder:
            logger.error("sshtunnel library not installed. Cannot establish tunnel.")
            raise ImportError("sshtunnel library is required for RemoteImageProvider")

        try:
            logger.info(f"Establishing SSH Tunnel to {self.user}@{self.host}...")
            # Check if key exists
            if not os.path.exists(self.key_path):
                 # Try expanduser
                 expanded_key = os.path.expanduser(self.key_path)
                 if os.path.exists(expanded_key):
                     self.key_path = expanded_key
                 else:
                     logger.error(f"SSH Key not found: {self.key_path}")
                     # Let it fail naturally or raise
            
            self.server = SSHTunnelForwarder(
                (self.host, 22),
                ssh_username=self.user,
                ssh_pkey=self.key_path,
                remote_bind_address=('127.0.0.1', self.remote_port),
                local_bind_address=('127.0.0.1', self.local_port),
                set_keepalive=10.0
            )
            self.server.start()
            self._is_connected = True
            logger.info(f"✅ SSH Tunnel active: localhost:{self.local_port} -> remote:{self.remote_port}")
        except Exception as e:
            logger.error(f"❌ Failed to establish SSH tunnel: {e}")
            self._is_connected = False
            raise

    def disconnect(self):
        if self.server:
            self.server.stop()
            self._is_connected = False
            logger.info("SSH Tunnel closed.")

    def get_base_url(self):
        """Return the local URL to access the remote service."""
        if self._is_connected:
            return f"http://127.0.0.1:{self.local_port}"
        return None
