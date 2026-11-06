"""Binary Audio Protocol and Packet Specification for Android Companion Ingress."""

import struct
from typing import Tuple, Optional
import numpy as np

# Protocol Header Constants (Audio Bridge Protocol v1)
PROTOCOL_MAGIC = b"\xAB\x01"
PROTOCOL_VERSION = 1

# Message Type Identifiers
TYPE_HANDSHAKE = 0x01
TYPE_PCM_AUDIO = 0x02
TYPE_PING = 0x03
TYPE_PONG = 0x04
TYPE_DISCONNECT = 0x05

# Header format:
#   2s: Magic bytes (b"\xAB\x01")
#   B:  Message Type (uint8)
#   B:  Channel Count (uint8, e.g. 2 for Stereo)
#   I:  Sequence Number (uint32, network byte order)
#   Q:  Timestamp in ms (uint64, network byte order)
# Total = 2 + 1 + 1 + 4 + 8 = 16 bytes
HEADER_STRUCT = struct.Struct("!2sBBIQ")
HEADER_SIZE = HEADER_STRUCT.size  # 16 bytes


class ProtocolError(Exception):
    """Base exception for protocol violations."""
    pass


class MalformedPacketError(ProtocolError):
    """Raised when an incoming packet cannot be parsed or violates size/alignment constraints."""
    pass


class UnauthorizedError(ProtocolError):
    """Raised when an unauthenticated client attempts to stream or connect."""
    pass


def parse_audio_packet(
    raw_bytes: bytes,
    expected_channels: int = 2,
    max_packet_size: int = 16384,
) -> Tuple[np.ndarray, int, int]:
    """
    Parses and validates a binary audio frame.
    
    Returns:
        Tuple of (float32_pcm_array, seq_num, timestamp_ms)
        where float32_pcm_array has shape (samples, channels) normalized to [-1.0, 1.0].
        
    Raises:
        MalformedPacketError if packet is malformed, oversized, or misaligned.
    """
    if not isinstance(raw_bytes, (bytes, bytearray, memoryview)):
        raise MalformedPacketError("Packet must be binary bytes")

    packet_len = len(raw_bytes)
    if packet_len < HEADER_SIZE:
        raise MalformedPacketError(f"Packet too short ({packet_len} bytes, minimum {HEADER_SIZE})")

    if packet_len > max_packet_size:
        raise MalformedPacketError(f"Packet size ({packet_len} bytes) exceeds limit ({max_packet_size} bytes)")

    try:
        magic, msg_type, channels, seq_num, timestamp_ms = HEADER_STRUCT.unpack_from(raw_bytes, 0)
    except struct.error as e:
        raise MalformedPacketError(f"Failed to unpack header: {e}")

    if magic != PROTOCOL_MAGIC:
        raise MalformedPacketError(f"Invalid protocol magic {magic!r}, expected {PROTOCOL_MAGIC!r}")

    if msg_type != TYPE_PCM_AUDIO:
        raise MalformedPacketError(f"Unexpected message type {msg_type}, expected TYPE_PCM_AUDIO ({TYPE_PCM_AUDIO})")

    if channels != expected_channels:
        raise MalformedPacketError(f"Channel count mismatch: packet has {channels}, expected {expected_channels}")

    payload = raw_bytes[HEADER_SIZE:]
    payload_len = len(payload)

    bytes_per_frame = 2 * channels  # 2 bytes per 16-bit sample * channel count
    if payload_len == 0:
        raise MalformedPacketError("Audio payload is empty")

    if payload_len % bytes_per_frame != 0:
        raise MalformedPacketError(
            f"Payload length ({payload_len} bytes) is not aligned to sample boundary ({bytes_per_frame} bytes)"
        )

    # Convert Little-Endian signed 16-bit PCM bytes to numpy array
    pcm_int16 = np.frombuffer(payload, dtype=np.int16)
    pcm_int16 = pcm_int16.reshape(-1, channels)

    # Convert to normalized float32 in [-1.0, 1.0]
    pcm_float32 = pcm_int16.astype(np.float32) / 32768.0

    return pcm_float32, seq_num, timestamp_ms


def pack_audio_packet(
    pcm_data: np.ndarray,
    seq_num: int,
    timestamp_ms: int,
    channels: int = 2,
) -> bytes:
    """
    Serializes PCM audio into the binary v1 frame format.
    Accepts float32 or int16 numpy array with shape (samples, channels).
    """
    if pcm_data.ndim == 1:
        pcm_data = pcm_data.reshape(-1, 1)

    if pcm_data.shape[1] != channels:
        raise ValueError(f"Data channels ({pcm_data.shape[1]}) does not match expected channels ({channels})")

    # If float, convert to clamped int16
    if np.issubdtype(pcm_data.dtype, np.floating):
        clamped = np.clip(pcm_data, -1.0, 1.0)
        pcm_int16 = (clamped * 32767.0).astype(np.int16)
    else:
        pcm_int16 = pcm_data.astype(np.int16)

    payload_bytes = pcm_int16.tobytes()
    header_bytes = HEADER_STRUCT.pack(
        PROTOCOL_MAGIC,
        TYPE_PCM_AUDIO,
        channels,
        seq_num,
        timestamp_ms,
    )
    return header_bytes + payload_bytes

