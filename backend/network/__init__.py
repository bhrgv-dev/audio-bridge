"""Network and WebSocket server package for AUDIO BRIDGE."""

from .websocket_server import BridgeWebSocketServer
from .android_server import AndroidAudioIngressServer
from .protocol import (
    parse_audio_packet,
    pack_audio_packet,
    MalformedPacketError,
    ProtocolError,
    UnauthorizedError,
    PROTOCOL_MAGIC,
    PROTOCOL_VERSION,
    TYPE_HANDSHAKE,
    TYPE_PCM_AUDIO,
    TYPE_DISCONNECT,
)

__all__ = [
    "BridgeWebSocketServer",
    "AndroidAudioIngressServer",
    "parse_audio_packet",
    "pack_audio_packet",
    "MalformedPacketError",
    "ProtocolError",
    "UnauthorizedError",
    "PROTOCOL_MAGIC",
    "PROTOCOL_VERSION",
    "TYPE_HANDSHAKE",
    "TYPE_PCM_AUDIO",
    "TYPE_DISCONNECT",
]
