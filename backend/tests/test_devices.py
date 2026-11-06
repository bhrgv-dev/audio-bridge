"""Automated unit tests for Windows Audio output device enumeration and Bluetooth identification."""

from audio.devices import (
    is_bluetooth_tws_device,
    get_audio_output_devices,
    get_default_output_device,
    evaluate_tws_status,
)


def test_bluetooth_tws_detection_heuristics():
    """Verify that Bluetooth TWS devices are recognized and standard PC speakers are not falsely flagged."""
    # Positive test cases (real Bluetooth TWS headsets and brands)
    positives = [
        "Headset (@System32\\drivers\\bthhfenum.sys,#2;%1 Hands-Free%0;(HTWS004))",
        "AirPods Pro",
        "boAt Rockerz 255 Pro+",
        "Noise Buds VS102",
        "Hammer KO TWS",
        "Sony WF-1000XM5",
        "OnePlus Buds Z2",
        "Realme Buds Air 3",
        "JBL Live Free NC+",
        "Samsung Galaxy Buds2 Pro",
        "Bluetooth Audio Device (Hands-Free AG Audio)",
    ]
    for dev in positives:
        assert is_bluetooth_tws_device(dev) is True, f"Failed to identify Bluetooth device: {dev}"

    # Negative test cases (internal PC chips, sound mapper, virtual sinks)
    negatives = [
        "Speakers (Senary Audio)",
        "Speakers (Realtek High Definition Audio)",
        "Speakers (Conexant ISST Audio)",
        "Microsoft Sound Mapper - Output",
        "Primary Sound Driver",
        "Intel(R) Display Audio",
        "NVIDIA High Definition Audio",
        "Virtual Audio Cable",
        "Steam Streaming Speakers",
    ]
    for dev in negatives:
        assert is_bluetooth_tws_device(dev) is False, f"Falsely identified as Bluetooth: {dev}"


def test_device_enumeration_structure():
    """Verify that get_audio_output_devices returns structured, valid AudioDeviceInfo objects."""
    devices = get_audio_output_devices()
    assert isinstance(devices, list)

    if devices:
        first = devices[0]
        assert hasattr(first, "id")
        assert hasattr(first, "name")
        assert hasattr(first, "is_default")
        assert hasattr(first, "is_bluetooth")
        assert hasattr(first, "max_output_channels")
        assert first.max_output_channels > 0


def test_default_device_resolution():
    """Verify that get_default_output_device identifies a default output when devices exist."""
    devices = get_audio_output_devices()
    default_dev = get_default_output_device()

    if devices:
        assert default_dev is not None
        assert default_dev.max_output_channels > 0


def test_tws_status_evaluation():
    """Verify evaluate_tws_status returns a valid tuple of (TwsStatus, str)."""
    status, label = evaluate_tws_status()
    assert status in ["Connected", "Not connected"]
    assert isinstance(label, str)
    assert len(label) > 0

