"""Configuration settings for AUDIO BRIDGE Backend and Network Architecture.

Security Architecture:
- Desktop Control Server: Strictly bound to loopback 127.0.0.1 (local only).
- Android Audio Ingress: By default binds to configurable interface address (0.0.0.0 or specific LAN adapter IP).
  Security Note on 0.0.0.0 (INADDR_ANY):
  Binding to 0.0.0.0 listens on all local network adapters simultaneously (Wi-Fi, Ethernet, VPNs,
  virtual interfaces). On untrusted or public networks, users can restrict listening to a specific
  interface by setting AUDIO_BRIDGE_ANDROID_HOST or configuring android_host with their exact Wi-Fi IP.
"""

import hmac
import os
import secrets
import socket
from dataclasses import dataclass, field
from typing import Literal, Optional

BufferMode = Literal["low", "balanced", "stable"]

BUFFER_DURATIONS_MS = {
    "low": 5,
    "balanced": 15,
    "stable": 30,
}


def detect_local_lan_ip() -> str:
    """
    Detects the primary local IPv4 address accessible on the Wi-Fi/LAN network
    without sending any data over the internet.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Does not actually transmit packets; connects to routable IP to query interface
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
    except Exception:
        try:
            ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            ip = "127.0.0.1"
    finally:
        s.close()
    return ip


@dataclass
class BridgeConfig:
    # Desktop Frontend Control Endpoint (Strictly Local-only Loopback)
    host: str = "127.0.0.1"
    port: int = 8765

    # Android Audio Ingress Endpoint (LAN-accessible)
    # Default is 0.0.0.0 (all interfaces), but can be set to specific interface IP for hardened isolation
    android_host: str = field(
        default_factory=lambda: os.getenv("AUDIO_BRIDGE_ANDROID_HOST", "0.0.0.0")
    )
    android_port: int = 8766

    # Security & Concurrency Controls
    auth_timeout_seconds: float = 3.0  # Max time allowed for handshake authentication
    max_android_clients: int = 1       # Maximum active authenticated mobile devices

    # Audio Engine Specifications
    sample_rate: int = 48000
    channels: int = 2
    audio_format: str = "pcm_s16le"
    max_packet_size: int = 16384  # 16 KB max per audio frame

    # Gain and Buffer Configurations
    mobile_gain: float = 1.0  # 100% default, range 0.0 - 1.5
    laptop_gain: float = 1.0  # 100% default, range 0.0 - 1.5
    buffer_mode: BufferMode = "balanced"
    is_running: bool = False
    selected_device_id: Optional[int] = None

    # Security Session Token (generated per backend run or configured)
    session_token: str = field(default_factory=lambda: secrets.token_hex(16))

    @property
    def buffer_ms(self) -> int:
        return BUFFER_DURATIONS_MS.get(self.buffer_mode, 15)

    def get_lan_ip(self) -> str:
        """Returns the detected local IPv4 address."""
        return detect_local_lan_ip()

    def get_masked_token(self) -> str:
        """Returns masked token string safe for public logs."""
        if len(self.session_token) <= 8:
            return "****"
        return f"{self.session_token[:4]}...{self.session_token[-4:]}"

    def verify_token(self, candidate_token: Optional[str]) -> bool:
        """Securely verifies candidate token using constant-time comparison."""
        if not candidate_token:
            return False
        return hmac.compare_digest(self.session_token, candidate_token)

    def set_mobile_volume(self, volume: int) -> None:
        """Sets mobile volume from percentage (0 - 150)."""
        clamped = max(0, min(150, volume))
        self.mobile_gain = clamped / 100.0

    def set_laptop_volume(self, volume: int) -> None:
        """Sets laptop volume from percentage (0 - 150)."""
        clamped = max(0, min(150, volume))
        self.laptop_gain = clamped / 100.0

    def set_buffer_mode(self, mode: str) -> None:
        """Sets jitter buffer strategy mode."""
        if mode in BUFFER_DURATIONS_MS:
            self.buffer_mode = mode  # type: ignore[assignment]
