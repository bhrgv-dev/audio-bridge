"""Android Audio Ingress Server for AUDIO BRIDGE with Security Hardening.

Security Features:
- Handshake-only authentication (no query parameter token exposure in URLs or access logs).
- Strict rejection of unauthenticated binary frames.
- Configurable authentication timeout.
- Maximum concurrent client enforcement.
- Safe rejection of duplicate handshake attempts.
- Protection against oversized/malformed frames without server crashes.
- Zero token leakage in logs, exceptions, or connection diagnostics.
"""

import asyncio
import json
import logging
from typing import Optional, Callable, Awaitable, Tuple, Set
from websockets.protocol import State
from websockets.asyncio.server import serve, ServerConnection
import websockets.exceptions

from config import BridgeConfig
from audio.mixer import AudioMixerFoundation
from network.protocol import (
    parse_audio_packet,
    MalformedPacketError,
)

logger = logging.getLogger(__name__)

StateChangeCallback = Callable[[], Awaitable[None]]


class AndroidAudioIngressServer:
    """LAN-facing ingress server for Android mobile audio capture streams."""

    def __init__(
        self,
        config: BridgeConfig,
        mixer: AudioMixerFoundation,
        on_state_change: Optional[StateChangeCallback] = None,
    ):
        self.config = config
        self.mixer = mixer
        self.on_state_change = on_state_change
        self.active_client: Optional[ServerConnection] = None
        self._connected_clients: Set[ServerConnection] = set()
        self._server = None
        self._running = False
        self.malformed_packets_dropped = 0
        self.total_packets_received = 0

    async def _notify_state_change(self) -> None:
        """Notifies desktop frontend of changes to mobile connection status."""
        if self.on_state_change:
            try:
                await self.on_state_change()
            except Exception as e:
                logger.warning(f"Error executing state change notification: {type(e).__name__}")

    async def _authenticate_client(
        self, websocket: ServerConnection, remote_addr: str
    ) -> Tuple[bool, str]:
        """
        Enforces handshake-only JSON authentication within configured timeout.
        Rejects query parameter tokens and unauthenticated binary frames.
        
        Returns:
            (is_authenticated, device_name)
        """
        try:
            raw_msg = await asyncio.wait_for(
                websocket.recv(), timeout=self.config.auth_timeout_seconds
            )
        except asyncio.TimeoutError:
            logger.info(f"Authentication timeout for client {remote_addr}")
            try:
                await websocket.send(json.dumps({
                    "type": "HANDSHAKE_REJECT",
                    "reason": "AUTH_TIMEOUT"
                }))
                await websocket.close(code=4408, reason="Authentication timeout")
            except Exception:
                pass
            return False, ""
        except Exception as e:
            logger.info(f"Connection error during authentication from {remote_addr}: {type(e).__name__}")
            return False, ""

        # Reject binary audio frames received before authentication
        if isinstance(raw_msg, (bytes, bytearray, memoryview)):
            logger.warning(f"Rejected unauthenticated binary audio frame from {remote_addr}")
            try:
                await websocket.send(json.dumps({
                    "type": "HANDSHAKE_REJECT",
                    "reason": "UNAUTHENTICATED_BINARY_FRAME"
                }))
                await websocket.close(code=4401, reason="Authentication required before streaming")
            except Exception:
                pass
            return False, ""

        # Validate JSON format
        try:
            data = json.loads(raw_msg)
        except json.JSONDecodeError:
            logger.warning(f"Malformed handshake payload from {remote_addr}")
            try:
                await websocket.send(json.dumps({
                    "type": "HANDSHAKE_REJECT",
                    "reason": "INVALID_HANDSHAKE_JSON"
                }))
                await websocket.close(code=4401, reason="Malformed handshake")
            except Exception:
                pass
            return False, ""

        if not isinstance(data, dict) or data.get("type") != "HANDSHAKE":
            logger.warning(f"First message was not HANDSHAKE from {remote_addr}")
            try:
                await websocket.send(json.dumps({
                    "type": "HANDSHAKE_REJECT",
                    "reason": "EXPECTED_HANDSHAKE"
                }))
                await websocket.close(code=4401, reason="Expected HANDSHAKE message")
            except Exception:
                pass
            return False, ""

        # Validate token constant-time without logging the candidate token
        candidate_token = data.get("token")
        if self.config.verify_token(candidate_token):
            dev_name = str(data.get("deviceName", "Android Mobile Device")).strip()
            if not dev_name:
                dev_name = "Android Mobile Device"
            # Cap device name length to prevent memory abuse
            dev_name = dev_name[:64]
            return True, dev_name
        else:
            logger.warning(f"Authentication rejected: invalid token from {remote_addr}")
            try:
                await websocket.send(json.dumps({
                    "type": "HANDSHAKE_REJECT",
                    "reason": "UNAUTHORIZED"
                }))
                await websocket.close(code=4401, reason="Invalid token")
            except Exception:
                pass
            return False, ""

    async def _handle_client(self, websocket: ServerConnection) -> None:
        """Lifecycle handler for an Android connection."""
        remote_addr = str(websocket.remote_address) if hasattr(websocket, "remote_address") else "unknown"
        logger.info(f"Incoming connection from {remote_addr}")

        # Clean up closed connections from set
        self._connected_clients = {
            c for c in self._connected_clients if getattr(c, "state", None) == State.OPEN
        }

        # Check maximum concurrent connections limit
        if len(self._connected_clients) >= self.config.max_android_clients:
            logger.warning(f"Rejecting connection from {remote_addr}: maximum concurrent clients reached")
            try:
                await websocket.send(json.dumps({
                    "type": "HANDSHAKE_REJECT",
                    "reason": "MAX_CONCURRENT_CLIENTS_REACHED"
                }))
                await websocket.close(code=1008, reason="Max concurrent clients reached")
            except Exception:
                pass
            return

        self._connected_clients.add(websocket)

        # Authenticate session via initial JSON HANDSHAKE only
        is_authenticated, device_name = await self._authenticate_client(websocket, remote_addr)

        if not is_authenticated:
            self._connected_clients.discard(websocket)
            return

        self.active_client = websocket
        self.mixer.mobile_input.device_name = device_name
        self.mixer.mobile_input.is_streaming = True
        logger.info(f"Android client authenticated successfully: '{device_name}' from {remote_addr}")

        # Send Handshake Acknowledgment
        try:
            await websocket.send(json.dumps({
                "type": "HANDSHAKE_ACK",
                "status": "AUTHORIZED",
                "sampleRate": self.config.sample_rate,
                "channels": self.config.channels,
                "bufferMs": self.config.buffer_ms,
            }))
        except Exception as e:
            logger.warning(f"Failed to send HANDSHAKE_ACK: {type(e).__name__}")
            self._connected_clients.discard(websocket)
            if self.active_client == websocket:
                self.active_client = None
            return

        await self._notify_state_change()

        # Stream processing loop (authenticated only)
        try:
            async for message in websocket:
                if isinstance(message, (bytes, bytearray, memoryview)):
                    # Guard packet size limit
                    if len(message) > self.config.max_packet_size:
                        self.malformed_packets_dropped += 1
                        logger.debug(f"Dropped oversized audio packet ({len(message)} bytes)")
                        continue

                    # Binary PCM audio frame
                    try:
                        pcm_float32, seq_num, timestamp_ms = parse_audio_packet(
                            message,
                            expected_channels=self.config.channels,
                            max_packet_size=self.config.max_packet_size,
                        )
                        self.mixer.mobile_input.receive_packet(
                            pcm_float32, timestamp=timestamp_ms / 1000.0
                        )
                        self.total_packets_received += 1
                    except MalformedPacketError as err:
                        self.malformed_packets_dropped += 1
                        logger.debug(f"Dropped malformed audio packet: {err}")
                    except Exception as err:
                        self.malformed_packets_dropped += 1
                        logger.warning(f"Unexpected packet parsing exception: {type(err).__name__}")
                elif isinstance(message, str):
                    # Control message
                    try:
                        cmd_data = json.loads(message)
                        cmd_type = cmd_data.get("type")

                        if cmd_type == "HANDSHAKE":
                            # Safe handling of duplicate authentication attempt
                            logger.info(f"Duplicate handshake received from authenticated client {remote_addr}")
                            await websocket.send(json.dumps({
                                "type": "ERROR",
                                "message": "Already authenticated"
                            }))
                        elif cmd_type == "DISCONNECT":
                            logger.info(f"Client requested disconnect from {remote_addr}")
                            break
                        elif cmd_type == "PING":
                            await websocket.send(json.dumps({"type": "PONG"}))
                    except json.JSONDecodeError:
                        pass
        except (websockets.exceptions.ConnectionClosed, ConnectionResetError):
            logger.info(f"Android client {remote_addr} disconnected")
        except Exception as e:
            logger.error(f"Error handling Android client {remote_addr}: {type(e).__name__}")
        finally:
            self._connected_clients.discard(websocket)
            if self.active_client == websocket:
                self.active_client = None
                self.mixer.mobile_input.reset()
                logger.info(f"Mobile session terminated for {remote_addr}")
                await self._notify_state_change()

    async def start(self) -> None:
        """Starts the Android audio ingress server on configured bind address and port."""
        self._running = True
        logger.info(
            f"Starting Android Audio Ingress server on {self.config.android_host}:{self.config.android_port} "
            f"(LAN interface: {self.config.get_lan_ip()}:{self.config.android_port})"
        )
        self._server = await serve(
            self._handle_client,
            self.config.android_host,
            self.config.android_port,
            ping_interval=20,
            ping_timeout=20,
            max_size=self.config.max_packet_size * 2,
        )

    async def stop(self) -> None:
        """Gracefully shuts down the Android ingress server."""
        self._running = False
        if self.active_client:
            try:
                await self.active_client.close(code=1000, reason="Server shutting down")
            except Exception:
                pass
            self.active_client = None

        self._connected_clients.clear()

        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        self.mixer.mobile_input.reset()
        logger.info("Android Audio Ingress server stopped")
