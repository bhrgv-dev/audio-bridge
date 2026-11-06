"""Audio processing and device detection package for AUDIO BRIDGE."""

from .devices import (
    get_audio_output_devices,
    get_default_output_device,
    evaluate_tws_status,
    is_bluetooth_tws_device,
)
from .mixer import (
    AudioMixerFoundation,
    MobileAudioInput,
    LaptopAudioInput,
    mix_pcm_buffers,
    apply_soft_clipping_protection,
    float32_to_int16,
)

__all__ = [
    "get_audio_output_devices",
    "get_default_output_device",
    "evaluate_tws_status",
    "is_bluetooth_tws_device",
    "AudioMixerFoundation",
    "MobileAudioInput",
    "LaptopAudioInput",
    "mix_pcm_buffers",
    "apply_soft_clipping_protection",
    "float32_to_int16",
]

