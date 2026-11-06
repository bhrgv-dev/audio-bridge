"""Automated unit and integration tests for Security-Hardened Android Ingress Server."""

import asyncio
from contextlib import asynccontextmanager
import json
import numpy as np
import pytest
from websockets.asyncio.client import connect

from config import BridgeConfig
from audio.mixer import AudioMixerFoundation
from network.android_server import AndroidAudioIngressServer
from network.protocol import (
    pack_audio_packet,
    parse_audio_packet,
    MalformedPacketError,
    PROTOCOL_MAGIC,
    TYPE_PCM_AUDIO,
    HEADER_SIZE,
)


@asynccontextmanager
async def create_test_android_server(
    port: int,
    token: str = "test-secret-token-1234",
    max_clients: int = 1,
    auth_timeout: float = 0.5,
):
    """Context manager for an isolated AndroidAudioIngressServer test instance."""
    config = BridgeConfig(
        android_host="127.0.0.1",
        android_port=port,
        session_token=token,
        max_packet_size=1024,
        max_android_clients=max_clients,
        auth_timeout_seconds=auth_timeout,
    )
    mixer = AudioMixerFoundation()
    state_updates = []

    async def on_state_change():
        state_updates.append(mixer.mobile_input.is_streaming)

    server = AndroidAudioIngressServer(
        config=config, mixer=mixer, on_state_change=on_state_change
    )
    await server.start()
    try:
        yield server, config, mixer, state_updates
    finally:
        await server.stop()
        mixer.stop()


def test_protocol_packing_and_parsing_roundtrip():
    """Verify pack_audio_packet and parse_audio_packet preserve sample values and shape."""
    audio_in = np.ones((240, 2), dtype=np.float32) * 0.5
    packed = pack_audio_packet(audio_in, seq_num=42, timestamp_ms=1600000000000, channels=2)

    assert len(packed) == HEADER_SIZE + (240 * 2 * 2)

    parsed_audio, seq_num, ts = parse_audio_packet(packed, expected_channels=2)
    assert seq_num == 42
    assert ts == 1600000000000
    assert parsed_audio.shape == (240, 2)
    assert np.allclose(parsed_audio, 0.5, atol=1e-3)


def test_protocol_malformed_packets():
    """Verify validation catches invalid magic, truncated headers, and unaligned payloads."""
    with pytest.raises(MalformedPacketError, match="Packet too short"):
        parse_audio_packet(b"\x00" * 10)

    bad_magic = b"\xFF\xFF" + b"\x00" * 14 + b"\x00\x00\x00\x00"
    with pytest.raises(MalformedPacketError, match="Invalid protocol magic"):
        parse_audio_packet(bad_magic)

    valid_header = PROTOCOL_MAGIC + bytes([TYPE_PCM_AUDIO, 2]) + b"\x00" * 12
    with pytest.raises(MalformedPacketError, match="Audio payload is empty"):
        parse_audio_packet(valid_header)

    with pytest.raises(MalformedPacketError, match="not aligned to sample boundary"):
        parse_audio_packet(valid_header + b"\x01\x02\x03")

    with pytest.raises(MalformedPacketError, match="exceeds limit"):
        parse_audio_packet(valid_header + (b"\x00" * 200), max_packet_size=100)


@pytest.mark.asyncio
async def test_authorized_android_connection_handshake():
    """Verify authorized client handshake establishes mobile connection and updates device name."""
    test_token = "valid-token-xyz-123"
    async with create_test_android_server(8811, token=test_token) as (
        server,
        config,
        mixer,
        updates,
    ):
        uri = f"ws://127.0.0.1:{config.android_port}"
        async with connect(uri) as ws:
            # Send Handshake message
            await ws.send(
                json.dumps({
                    "type": "HANDSHAKE",
                    "token": test_token,
                    "deviceName": "Pixel 8 Pro",
                    "sampleRate": 48000,
                    "channels": 2,
                    "version": 1,
                })
            )

            ack_raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
            ack = json.loads(ack_raw)

            assert ack["type"] == "HANDSHAKE_ACK"
            assert ack["status"] == "AUTHORIZED"
            assert ack["sampleRate"] == 48000
            assert ack["channels"] == 2
            assert mixer.mobile_input.device_name == "Pixel 8 Pro"
            assert mixer.mobile_input.is_streaming is True
            assert len(updates) > 0


@pytest.mark.asyncio
async def test_query_param_token_not_accepted():
    """Verify that URL query parameter token is NOT accepted as authentication."""
    test_token = "query-token-abc"
    async with create_test_android_server(8812, token=test_token, auth_timeout=0.3) as (
        server,
        config,
        mixer,
        updates,
    ):
        # Connecting with query param only, without sending JSON HANDSHAKE
        uri = f"ws://127.0.0.1:{config.android_port}?token={test_token}"
        async with connect(uri) as ws:
            # Must timeout and reject because JSON handshake was not sent
            resp_raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
            resp = json.loads(resp_raw)
            assert resp["type"] == "HANDSHAKE_REJECT"
            assert resp["reason"] == "AUTH_TIMEOUT"
            assert mixer.mobile_input.is_streaming is False


@pytest.mark.asyncio
async def test_unauthenticated_binary_frame_rejected():
    """Verify binary audio frames sent prior to handshake authentication are immediately rejected."""
    async with create_test_android_server(8813) as (server, config, mixer, updates):
        uri = f"ws://127.0.0.1:{config.android_port}"
        async with connect(uri) as ws:
            # Send binary frame without authenticating
            audio_frame = pack_audio_packet(
                np.ones((60, 2), dtype=np.float32) * 0.5,
                seq_num=1,
                timestamp_ms=1000,
                channels=2,
            )
            await ws.send(audio_frame)

            resp_raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
            resp = json.loads(resp_raw)
            assert resp["type"] == "HANDSHAKE_REJECT"
            assert resp["reason"] == "UNAUTHENTICATED_BINARY_FRAME"
            assert mixer.mobile_input.queue.available_samples == 0


@pytest.mark.asyncio
async def test_unauthorized_client_rejection():
    """Verify client sending invalid token in handshake is rejected with 4401 and closed."""
    async with create_test_android_server(8814, token="secret-token") as (
        server,
        config,
        mixer,
        updates,
    ):
        uri = f"ws://127.0.0.1:{config.android_port}"
        async with connect(uri) as ws:
            await ws.send(
                json.dumps({
                    "type": "HANDSHAKE",
                    "token": "WRONG_TOKEN",
                    "deviceName": "Unauthorized Device",
                })
            )

            resp_raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
            resp = json.loads(resp_raw)
            assert resp["type"] == "HANDSHAKE_REJECT"
            assert resp["reason"] == "UNAUTHORIZED"

            with pytest.raises(Exception):
                await asyncio.wait_for(ws.recv(), timeout=1.0)

            assert server.active_client is None
            assert mixer.mobile_input.is_streaming is False


@pytest.mark.asyncio
async def test_authentication_timeout():
    """Verify client failing to send handshake within auth_timeout is closed."""
    async with create_test_android_server(8815, auth_timeout=0.2) as (
        server,
        config,
        mixer,
        updates,
    ):
        uri = f"ws://127.0.0.1:{config.android_port}"
        async with connect(uri) as ws:
            resp_raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
            resp = json.loads(resp_raw)
            assert resp["type"] == "HANDSHAKE_REJECT"
            assert resp["reason"] == "AUTH_TIMEOUT"


@pytest.mark.asyncio
async def test_duplicate_handshake_rejected_safely():
    """Verify duplicate handshake on an already authenticated socket is safely rejected without crash."""
    test_token = "dup-token-123"
    async with create_test_android_server(8816, token=test_token) as (
        server,
        config,
        mixer,
        updates,
    ):
        uri = f"ws://127.0.0.1:{config.android_port}"
        async with connect(uri) as ws:
            # 1. Successful authentication
            await ws.send(
                json.dumps({
                    "type": "HANDSHAKE",
                    "token": test_token,
                    "deviceName": "Galaxy S24",
                })
            )
            ack = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
            assert ack["status"] == "AUTHORIZED"

            # 2. Attempt duplicate handshake
            await ws.send(
                json.dumps({
                    "type": "HANDSHAKE",
                    "token": test_token,
                    "deviceName": "Galaxy S24",
                })
            )
            err = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
            assert err["type"] == "ERROR"
            assert "Already authenticated" in err["message"]

            # Connection remains alive and usable
            assert server.active_client is not None
            assert mixer.mobile_input.is_streaming is True


@pytest.mark.asyncio
async def test_max_concurrent_clients_rejection():
    """Verify second client is rejected when maximum concurrent clients limit is reached."""
    test_token = "concurrency-token"
    async with create_test_android_server(8817, token=test_token, max_clients=1) as (
        server,
        config,
        mixer,
        updates,
    ):
        uri = f"ws://127.0.0.1:{config.android_port}"

        # Client 1 connects and authenticates
        ws1 = await connect(uri)
        await ws1.send(
            json.dumps({"type": "HANDSHAKE", "token": test_token, "deviceName": "Client 1"})
        )
        ack1 = json.loads(await ws1.recv())
        assert ack1["status"] == "AUTHORIZED"
        assert server.active_client is not None
        assert mixer.mobile_input.device_name == "Client 1"

        # Client 2 connects while Client 1 is active
        ws2 = await connect(uri)
        resp2 = json.loads(await asyncio.wait_for(ws2.recv(), timeout=2.0))
        assert resp2["type"] == "HANDSHAKE_REJECT"
        assert resp2["reason"] == "MAX_CONCURRENT_CLIENTS_REACHED"

        # Client 1 is unaffected
        assert server.active_client is not None
        assert mixer.mobile_input.device_name == "Client 1"

        await ws1.close()
        await ws2.close()


@pytest.mark.asyncio
async def test_audio_packet_routing_into_mixer():
    """Verify valid binary PCM audio packet is parsed and queued into mixer.mobile_input."""
    test_token = "audio-route-token"
    async with create_test_android_server(8818, token=test_token) as (
        server,
        config,
        mixer,
        updates,
    ):
        uri = f"ws://127.0.0.1:{config.android_port}"
        async with connect(uri) as ws:
            # Authenticate via JSON Handshake
            await ws.send(
                json.dumps({"type": "HANDSHAKE", "token": test_token, "deviceName": "Pixel 8"})
            )
            await ws.recv()  # Consume HANDSHAKE_ACK

            # Generate 120 samples of stereo audio at 0.75 amplitude
            audio_samples = np.ones((120, 2), dtype=np.float32) * 0.75
            packet_bytes = pack_audio_packet(
                audio_samples, seq_num=1, timestamp_ms=1000, channels=2
            )

            await ws.send(packet_bytes)
            await asyncio.sleep(0.05)

            assert server.total_packets_received == 1
            assert mixer.mobile_input.total_packets_received == 1
            assert mixer.mobile_input.queue.available_samples == 120

            # Read from mixer queue and verify audio accuracy
            read_chunk = mixer.mobile_input.read_samples(120)
            assert read_chunk.shape == (120, 2)
            assert np.allclose(read_chunk, 0.75, atol=1e-3)


@pytest.mark.asyncio
async def test_malformed_packets_dropped_gracefully():
    """Verify malformed binary packets are dropped without crashing server."""
    test_token = "malform-token"
    async with create_test_android_server(8819, token=test_token) as (
        server,
        config,
        mixer,
        updates,
    ):
        uri = f"ws://127.0.0.1:{config.android_port}"
        async with connect(uri) as ws:
            # Authenticate first
            await ws.send(
                json.dumps({"type": "HANDSHAKE", "token": test_token, "deviceName": "Pixel 8"})
            )
            await ws.recv()  # Consume HANDSHAKE_ACK

            # Send garbage bytes
            await ws.send(b"\xDE\xAD\xBE\xEF\x00\x01\x02\x03")
            await asyncio.sleep(0.05)

            assert server.malformed_packets_dropped == 1
            assert mixer.mobile_input.queue.available_samples == 0

            # Send valid packet right after to confirm server remains operational
            valid_packet = pack_audio_packet(
                np.ones((60, 2), dtype=np.float32) * 0.2,
                seq_num=2,
                timestamp_ms=2000,
                channels=2,
            )
            await ws.send(valid_packet)
            await asyncio.sleep(0.05)

            assert server.total_packets_received == 1
            assert mixer.mobile_input.queue.available_samples == 60


@pytest.mark.asyncio
async def test_disconnection_cleanup():
    """Verify client disconnection cleans up active_client and resets MobileAudioInput."""
    test_token = "disconnect-token"
    async with create_test_android_server(8820, token=test_token) as (
        server,
        config,
        mixer,
        updates,
    ):
        uri = f"ws://127.0.0.1:{config.android_port}"
        ws = await connect(uri)
        await ws.send(
            json.dumps({"type": "HANDSHAKE", "token": test_token, "deviceName": "Pixel 8"})
        )
        await ws.recv()  # HANDSHAKE_ACK
        assert server.active_client is not None
        assert mixer.mobile_input.is_streaming is True

        await ws.close()
        await asyncio.sleep(0.05)

        assert server.active_client is None
        assert mixer.mobile_input.is_streaming is False
        assert mixer.mobile_input.device_name == ""
