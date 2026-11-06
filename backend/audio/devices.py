"""Windows audio output device enumeration and identification."""

import logging
from typing import List, Optional, Tuple
import sounddevice as sd
from models.messages import AudioDeviceInfo, TwsStatus

logger = logging.getLogger(__name__)

# Keywords indicating Bluetooth / Wireless TWS hardware
BLUETOOTH_KEYWORDS = [
    "bthhfenum",
    "bthaudio",
    "bluetooth",
    "airpod",
    "galaxy buds",
    "pixel buds",
    "wf-1000",
    "wh-1000",
    "boat",
    "hammer",
    "noise",
    "realme",
    "oneplus",
    "jbl",
    "oppo enco",
    "freebuds",
    "hands-free",
    "handsfree",
    "tws",
]

# Keywords indicating non-bluetooth standard PC endpoints
INTERNAL_DEVICE_EXCLUSIONS = [
    "realtek",
    "senary audio",
    "conexant",
    "sound mapper",
    "primary sound",
    "high definition audio device",
    "intel(r) display audio",
    "nvidia high definition audio",
    "amd high definition audio",
    "virtual audio",
    "cable input",
    "steam streaming",
]


def is_bluetooth_tws_device(device_name: str) -> bool:
    """
    Evaluates whether an audio device is reliably a Bluetooth or TWS device.
    Strictly avoids false positives for standard internal PC audio endpoints.
    """
    name_lower = device_name.lower()

    # If explicitly known to be a generic PC bus/internal endpoint without bluetooth tags:
    for exclusion in INTERNAL_DEVICE_EXCLUSIONS:
        if exclusion in name_lower and not any(bt in name_lower for bt in ["bluetooth", "bthhfenum", "tws"]):
            return False

    # Check for verified Bluetooth/TWS indicators
    for kw in BLUETOOTH_KEYWORDS:
        if kw in name_lower:
            return True

    return False


def get_audio_output_devices() -> List[AudioDeviceInfo]:
    """
    Scans Windows audio hardware and returns all available output endpoints.
    """
    devices: List[AudioDeviceInfo] = []

    try:
        raw_devices = sd.query_devices()
        default_out_idx = sd.default.device[1]
        hostapis = sd.query_hostapis()
    except Exception as e:
        logger.error(f"Error querying audio devices: {e}")
        return devices

    for idx, d in enumerate(raw_devices):
        max_out = d.get("max_output_channels", 0)
        if max_out <= 0:
            continue

        dev_name = d.get("name", f"Audio Output {idx}")
        is_default = (idx == default_out_idx)
        is_bt = is_bluetooth_tws_device(dev_name)

        hostapi_idx = d.get("hostapi", 0)
        hostapi_name = "WASAPI"
        if 0 <= hostapi_idx < len(hostapis):
            hostapi_name = hostapis[hostapi_idx].get("name", "Unknown")

        devices.append(
            AudioDeviceInfo(
                id=idx,
                name=dev_name,
                is_default=is_default,
                is_bluetooth=is_bt,
                max_output_channels=max_out,
                default_samplerate=float(d.get("default_samplerate", 48000.0)),
                host_api=hostapi_name,
            )
        )

    return devices


def get_default_output_device() -> Optional[AudioDeviceInfo]:
    """
    Returns the currently active default Windows audio output device.
    """
    devices = get_audio_output_devices()
    for d in devices:
        if d.is_default:
            return d
    return devices[0] if devices else None


def evaluate_tws_status(selected_id: Optional[int] = None) -> Tuple[TwsStatus, str]:
    """
    Checks if the active or user-selected audio output device is a Bluetooth TWS device.
    Strictly avoids falsely claiming TWS is connected when an inactive device merely appears in the device list.
    """
    devices = get_audio_output_devices()
    target_dev = None

    if selected_id is not None:
        target_dev = next((d for d in devices if d.id == selected_id), None)

    if target_dev is None:
        target_dev = get_default_output_device()

    if target_dev and target_dev.is_bluetooth:
        return "Connected", target_dev.name

    output_name = target_dev.name if target_dev else "No audio output device"
    return "Not connected", output_name

