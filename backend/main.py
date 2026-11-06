"""Main entry point for AUDIO BRIDGE Backend Service with Security Hardened Ingress."""

import asyncio
import logging
import signal
import sys
from config import BridgeConfig
from audio.mixer import AudioMixerFoundation
from audio.devices import get_default_output_device, evaluate_tws_status
from network.websocket_server import BridgeWebSocketServer
from network.android_server import AndroidAudioIngressServer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("audio_bridge")


async def main():
    config = BridgeConfig()
    mixer = AudioMixerFoundation(
        mobile_gain=config.mobile_gain,
        laptop_gain=config.laptop_gain,
    )

    desktop_server = BridgeWebSocketServer(config=config, mixer=mixer)
    android_server = AndroidAudioIngressServer(
        config=config,
        mixer=mixer,
        on_state_change=desktop_server.broadcast_state,
    )

    # Audio device diagnostic
    default_dev = get_default_output_device()
    tws_status, tws_label = evaluate_tws_status()
    lan_ip = config.get_lan_ip()

    print("\n" + "=" * 64)
    print("      AUDIO BRIDGE — UNIVERSAL DUAL AUDIO SYSTEM")
    print("      Phase 2.6: Security Hardened Ingress Architecture")
    print("=" * 64)
    print(f"Desktop Control:       ws://{config.host}:{config.port}")
    print(f"Android Audio Ingress: ws://{lan_ip}:{config.android_port}")
    print(f"Ingress Bind Host:     {config.android_host} (Configurable)")
    print(f"Authentication Mode:   JSON Handshake (Session Token Required)")
    print(f"Default Laptop Output: {default_dev.name if default_dev else 'None detected'}")
    print(f"TWS Output State:      {tws_status} ({tws_label})")
    print(f"Session Token (pairing, keep secret): {config.session_token}")
    print(f"Audio Specifications:  {config.sample_rate} Hz, Stereo, Signed 16-bit PCM")
    print("=" * 64)
    print("  Ready for Android connection over local Wi-Fi.")
    print("=" * 64 + "\n")

    logger.info("Security handshake authentication active on Android ingress")

    # Start both WebSocket listeners
    await desktop_server.start()
    await android_server.start()

    stop_event = asyncio.Event()

    def handle_signal():
        logger.info("Shutdown signal received")
        stop_event.set()

    # Register signals where available (Windows compatibility)
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, handle_signal)
        except NotImplementedError:
            pass

    try:
        await stop_event.wait()
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
    finally:
        logger.info("Stopping Audio Bridge network services...")
        await android_server.stop()
        await desktop_server.stop()
        mixer.stop()
        logger.info("Audio Bridge shutdown complete.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown complete.")
