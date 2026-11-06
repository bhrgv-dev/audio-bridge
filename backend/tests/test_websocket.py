"""Automated integration tests for WebSocket server, commands, state updates, and error handling."""

import asyncio
from contextlib import asynccontextmanager
import json
import pytest
from websockets.asyncio.client import connect

from config import BridgeConfig
from audio.mixer import AudioMixerFoundation
from network.websocket_server import BridgeWebSocketServer


@asynccontextmanager
async def create_test_server(port: int):
    """Context manager that starts and stops an isolated test WebSocket server instance."""
    config = BridgeConfig(host="127.0.0.1", port=port)
    mixer = AudioMixerFoundation()
    server = BridgeWebSocketServer(config=config, mixer=mixer)
    await server.start()
    try:
        yield server, config
    finally:
        await server.stop()
        mixer.stop()


@pytest.mark.asyncio
async def test_websocket_connect_and_initial_state():
    """Verify that a client can connect and immediately receives truthful initial state."""
    async with create_test_server(8771) as (server, config):
        uri = f"ws://127.0.0.1:{config.port}"
        async with connect(uri) as ws:
            raw_msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
            state = json.loads(raw_msg)

            assert state["type"] == "STATE_UPDATE"
            assert state["mobileStatus"] == "Disconnected"
            assert state["laptopStatus"] == "Ready"
            assert state["isServiceRunning"] is False
            assert state["mobileVolume"] == 100
            assert state["laptopVolume"] == 100
            assert state["bufferMode"] == "balanced"


@pytest.mark.asyncio
async def test_start_and_stop_bridge():
    """Verify START_BRIDGE and STOP_BRIDGE commands update state and notify clients."""
    async with create_test_server(8772) as (server, config):
        uri = f"ws://127.0.0.1:{config.port}"
        async with connect(uri) as ws:
            # Consume initial state
            await ws.recv()

            # Send START_BRIDGE
            await ws.send(json.dumps({
                "command": "START_BRIDGE",
                "mobileVolume": 120,
                "laptopVolume": 80,
                "bufferMode": "low",
            }))

            start_resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
            assert start_resp["type"] == "STATE_UPDATE"
            assert start_resp["isServiceRunning"] is True
            assert start_resp["mobileVolume"] == 120
            assert start_resp["laptopVolume"] == 80
            assert start_resp["bufferMode"] == "low"
            assert start_resp["mobileStatus"] == "Connecting"
            assert config.is_running is True

            # Send STOP_BRIDGE
            await ws.send(json.dumps({"command": "STOP_BRIDGE"}))
            stop_resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
            assert stop_resp["type"] == "STATE_UPDATE"
            assert stop_resp["isServiceRunning"] is False
            assert stop_resp["mobileStatus"] == "Disconnected"
            assert config.is_running is False


@pytest.mark.asyncio
async def test_volume_and_buffer_configuration():
    """Verify independent gain and buffer strategy updates."""
    async with create_test_server(8773) as (server, config):
        uri = f"ws://127.0.0.1:{config.port}"
        async with connect(uri) as ws:
            await ws.recv()  # Initial state

            # Update mobile volume
            await ws.send(json.dumps({"command": "SET_MOBILE_VOLUME", "volume": 75}))
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
            assert msg["mobileVolume"] == 75
            assert config.mobile_gain == 0.75

            # Update laptop volume
            await ws.send(json.dumps({"command": "SET_LAPTOP_VOLUME", "volume": 135}))
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
            assert msg["laptopVolume"] == 135
            assert config.laptop_gain == 1.35

            # Update buffer mode
            await ws.send(json.dumps({"command": "SET_BUFFER_MODE", "mode": "stable"}))
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
            assert msg["bufferMode"] == "stable"
            assert config.buffer_mode == "stable"


@pytest.mark.asyncio
async def test_get_devices_command():
    """Verify GET_DEVICES command returns structured audio device list."""
    async with create_test_server(8774) as (server, config):
        uri = f"ws://127.0.0.1:{config.port}"
        async with connect(uri) as ws:
            await ws.recv()  # Initial state

            await ws.send(json.dumps({"command": "GET_DEVICES"}))
            resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
            assert resp["type"] == "DEVICE_LIST"
            assert "devices" in resp
            assert isinstance(resp["devices"], list)


@pytest.mark.asyncio
async def test_select_output_device_command():
    """Verify SELECT_OUTPUT_DEVICE command updates selected device in state."""
    async with create_test_server(8778) as (server, config):
        uri = f"ws://127.0.0.1:{config.port}"
        async with connect(uri) as ws:
            await ws.recv()  # Initial state

            await ws.send(json.dumps({"command": "SELECT_OUTPUT_DEVICE", "deviceId": 3}))
            resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
            assert resp["type"] == "STATE_UPDATE"
            assert resp["selectedDeviceId"] == 3
            assert config.selected_device_id == 3


@pytest.mark.asyncio
async def test_invalid_messages_handling():
    """Verify server gracefully rejects invalid JSON and unknown commands without crashing."""
    async with create_test_server(8775) as (server, config):
        uri = f"ws://127.0.0.1:{config.port}"
        async with connect(uri) as ws:
            await ws.recv()  # Initial state

            # Send invalid non-JSON
            await ws.send("NOT_A_JSON_STRING")
            err1 = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
            assert err1["type"] == "ERROR"
            assert "Invalid JSON format" in err1["message"]

            # Send unknown command
            await ws.send(json.dumps({"command": "FLY_TO_THE_MOON"}))
            err2 = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
            assert err2["type"] == "ERROR"
            assert "Unknown command" in err2["message"]

            # Verify server is still alive and responds to normal commands
            await ws.send(json.dumps({"command": "GET_STATE"}))
            state = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
            assert state["type"] == "STATE_UPDATE"


@pytest.mark.asyncio
async def test_disconnection_cleanup():
    """Verify server cleans up client set on unexpected or normal disconnect."""
    async with create_test_server(8776) as (server, config):
        uri = f"ws://127.0.0.1:{config.port}"
        ws = await connect(uri)
        await ws.recv()
        assert len(server.clients) == 1

        await ws.close()
        await asyncio.sleep(0.05)
        assert len(server.clients) == 0
