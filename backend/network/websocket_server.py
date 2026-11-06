"""WebSocket server implementation for AUDIO BRIDGE control and state synchronization."""

import asyncio
import json
import logging
from typing import Set, Dict, Any, Optional
from websockets.asyncio.server import serve, ServerConnection
import websockets.exceptions

from config import BridgeConfig
from audio.mixer import AudioMixerFoundation
from audio.devices import evaluate_tws_status, get_audio_output_devices
from models.messages import StateUpdate

logger = logging.getLogger(__name__)


class BridgeWebSocketServer:
    """Manages WebSocket connections and dispatches commands between frontend and audio engine."""

    def __init__(self, config: BridgeConfig, mixer: AudioMixerFoundation):
        self.config = config
        self.mixer = mixer
        self.clients: Set[ServerConnection] = set()
        self._server = None
        self._running = False

    def get_current_state_dict(self) -> Dict[str, Any]:
        """Constructs a truthful state update payload."""
        tws_status, output_dev_name = evaluate_tws_status(self.config.selected_device_id)
        devices = get_audio_output_devices()

        # Mobile status resolution
        if not self.config.is_running:
            mobile_status = "Disconnected"
            mobile_name = ""
        elif self.mixer.mobile_input.is_streaming:
            mobile_status = "Connected"
            mobile_name = self.mixer.mobile_input.device_name or "Android Mobile Device"
        else:
            mobile_status = "Connecting"
            mobile_name = ""

        # Laptop audio status resolution (Truthful: Phase 2 mixer foundation is Ready)
        laptop_status = "Ready"

        state = StateUpdate(
            mobileStatus=mobile_status,
            laptopStatus=laptop_status,
            twsStatus=tws_status,
            mobileName=mobile_name,
            outputDevice=output_dev_name,
            latency=self.config.buffer_ms if self.config.is_running else 0,
            mobileVolume=int(round(self.config.mobile_gain * 100)),
            laptopVolume=int(round(self.config.laptop_gain * 100)),
            bufferMode=self.config.buffer_mode,
            isServiceRunning=self.config.is_running,
            lanIp=self.config.get_lan_ip(),
            androidPort=self.config.android_port,
            selectedDeviceId=self.config.selected_device_id,
            availableDevices=[d.to_dict() for d in devices],
        )
        return state.to_dict()

    async def broadcast_state(self) -> None:
        """Broadcasts current state to all connected desktop frontend clients."""
        if not self.clients:
            return

        payload = json.dumps(self.get_current_state_dict())
        closed_clients = set()

        for client in list(self.clients):
            try:
                await client.send(payload)
            except (websockets.exceptions.ConnectionClosed, ConnectionResetError):
                closed_clients.add(client)
            except Exception as e:
                logger.warning(f"Failed to send state to client: {e}")
                closed_clients.add(client)

        self.clients.difference_update(closed_clients)

    async def _handle_message(self, websocket: ServerConnection, raw_message: str) -> None:
        """Parses and handles a single incoming JSON command."""
        try:
            data = json.loads(raw_message)
        except json.JSONDecodeError:
            await websocket.send(json.dumps({
                "type": "ERROR",
                "message": "Invalid JSON format"
            }))
            return

        command = data.get("command")
        if not command:
            await websocket.send(json.dumps({
                "type": "ERROR",
                "message": "Missing 'command' property"
            }))
            return

        logger.info(f"Received command: {command}")

        if command == "START_BRIDGE":
            if "mobileVolume" in data:
                self.config.set_mobile_volume(int(data["mobileVolume"]))
            if "laptopVolume" in data:
                self.config.set_laptop_volume(int(data["laptopVolume"]))
            if "bufferMode" in data:
                self.config.set_buffer_mode(str(data["bufferMode"]))

            self.mixer.set_gains(self.config.mobile_gain, self.config.laptop_gain)
            self.mixer.start()
            self.config.is_running = True
            await self.broadcast_state()

        elif command == "STOP_BRIDGE":
            self.config.is_running = False
            self.mixer.stop()
            await self.broadcast_state()

        elif command == "SET_MOBILE_VOLUME":
            volume = data.get("volume", 100)
            try:
                vol_int = int(volume)
                self.config.set_mobile_volume(vol_int)
                self.mixer.set_gains(self.config.mobile_gain, self.config.laptop_gain)
                await self.broadcast_state()
            except (ValueError, TypeError):
                await websocket.send(json.dumps({
                    "type": "ERROR",
                    "message": "Volume must be an integer"
                }))

        elif command == "SET_LAPTOP_VOLUME":
            volume = data.get("volume", 100)
            try:
                vol_int = int(volume)
                self.config.set_laptop_volume(vol_int)
                self.mixer.set_gains(self.config.mobile_gain, self.config.laptop_gain)
                await self.broadcast_state()
            except (ValueError, TypeError):
                await websocket.send(json.dumps({
                    "type": "ERROR",
                    "message": "Volume must be an integer"
                }))

        elif command == "SET_BUFFER_MODE":
            mode = data.get("mode")
            if mode in ["low", "balanced", "stable"]:
                self.config.set_buffer_mode(mode)
                await self.broadcast_state()
            else:
                await websocket.send(json.dumps({
                    "type": "ERROR",
                    "message": f"Invalid buffer mode '{mode}'"
                }))

        elif command == "SELECT_OUTPUT_DEVICE":
            device_id = data.get("deviceId")
            try:
                self.config.selected_device_id = int(device_id) if device_id is not None else None
                await self.broadcast_state()
            except (ValueError, TypeError):
                await websocket.send(json.dumps({
                    "type": "ERROR",
                    "message": "Invalid deviceId"
                }))

        elif command == "GET_STATE":
            await websocket.send(json.dumps(self.get_current_state_dict()))

        elif command == "GET_DEVICES":
            devices = get_audio_output_devices()
            await websocket.send(json.dumps({
                "type": "DEVICE_LIST",
                "devices": [d.to_dict() for d in devices]
            }))

        else:
            await websocket.send(json.dumps({
                "type": "ERROR",
                "message": f"Unknown command '{command}'"
            }))

    async def _client_handler(self, websocket: ServerConnection) -> None:
        """Handles lifecycle for a single client connection."""
        self.clients.add(websocket)
        logger.info(f"Client connected. Active clients: {len(self.clients)}")

        # Send initial state immediately upon connection
        try:
            await websocket.send(json.dumps(self.get_current_state_dict()))
        except Exception as e:
            logger.warning(f"Error sending initial state: {e}")

        try:
            async for raw_message in websocket:
                await self._handle_message(websocket, raw_message)
        except (websockets.exceptions.ConnectionClosed, ConnectionResetError):
            logger.info("Client disconnected normally")
        except Exception as e:
            logger.error(f"Unexpected client error: {e}")
        finally:
            self.clients.discard(websocket)
            logger.info(f"Client removed. Remaining clients: {len(self.clients)}")

    async def start(self) -> None:
        """Starts the WebSocket server."""
        self._running = True
        logger.info(f"Starting WebSocket server on {self.config.host}:{self.config.port}")
        self._server = await serve(
            self._client_handler,
            self.config.host,
            self.config.port,
            ping_interval=20,
            ping_timeout=20,
        )

    async def stop(self) -> None:
        """Gracefully stops the WebSocket server and disconnects clients."""
        self._running = False
        if self.clients:
            close_tasks = [client.close() for client in list(self.clients)]
            await asyncio.gather(*close_tasks, return_exceptions=True)
            self.clients.clear()

        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        logger.info("WebSocket server stopped")
