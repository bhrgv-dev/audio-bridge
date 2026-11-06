"""Modular audio mixer foundation for AUDIO BRIDGE.

Provides PCM buffer mixing, independent gain stages, soft-saturation clipping protection,
and input interfaces for Mobile and Laptop audio streams.
"""

import time
import threading
from typing import Optional, Tuple
import numpy as np


class AudioBufferQueue:
    """Thread-safe linear FIFO ring/buffer queue for PCM audio data."""

    def __init__(self, max_samples: int = 48000 * 2):  # 1 sec stereo buffer default
        self.max_samples = max_samples
        self._buffer: Optional[np.ndarray] = None
        self._lock = threading.Lock()
        self.underrun_count = 0
        self.overflow_count = 0

    def push(self, data: np.ndarray) -> None:
        """Pushes a 2D float32 array (samples, channels) into the buffer queue."""
        if data.size == 0:
            return

        with self._lock:
            if self._buffer is None or self._buffer.size == 0:
                self._buffer = data.copy()
            else:
                self._buffer = np.vstack((self._buffer, data))

            # Guard against buffer overflow
            if len(self._buffer) > self.max_samples:
                excess = len(self._buffer) - self.max_samples
                self._buffer = self._buffer[excess:]
                self.overflow_count += 1

    def pop(self, num_samples: int, channels: int = 2) -> np.ndarray:
        """Pops num_samples from the queue. If insufficient, pads with zeros."""
        with self._lock:
            if self._buffer is None or len(self._buffer) == 0:
                self.underrun_count += 1
                return np.zeros((num_samples, channels), dtype=np.float32)

            available = len(self._buffer)
            if available >= num_samples:
                chunk = self._buffer[:num_samples]
                self._buffer = self._buffer[num_samples:]
                return chunk
            else:
                # Underrun: return available data and pad remainder with silence
                chunk = np.zeros((num_samples, channels), dtype=np.float32)
                chunk[:available] = self._buffer
                self._buffer = None
                self.underrun_count += 1
                return chunk

    def clear(self) -> None:
        """Clears all queued data and resets counters."""
        with self._lock:
            self._buffer = None
            self.underrun_count = 0
            self.overflow_count = 0

    @property
    def available_samples(self) -> int:
        with self._lock:
            return len(self._buffer) if self._buffer is not None else 0


class MobileAudioInput:
    """Interface for incoming mobile audio stream from the Android companion app."""

    def __init__(self):
        self.queue = AudioBufferQueue()
        self.last_packet_time: float = 0.0
        self.total_packets_received: int = 0
        self.is_streaming: bool = False
        self.device_name: str = ""

    def receive_packet(self, pcm_data: np.ndarray, timestamp: Optional[float] = None) -> None:
        """Receives a PCM packet from the network."""
        if not isinstance(pcm_data, np.ndarray):
            raise TypeError("Audio data must be a numpy ndarray")
        if pcm_data.ndim == 1:
            pcm_data = pcm_data.reshape(-1, 1)
        self.queue.push(pcm_data)
        self.last_packet_time = timestamp or time.time()
        self.total_packets_received += 1
        self.is_streaming = True

    def push_pcm_frame(self, pcm_data: np.ndarray, timestamp: Optional[float] = None) -> None:
        """Alias for receive_packet providing explicit validation."""
        self.receive_packet(pcm_data, timestamp)

    def read_samples(self, count: int) -> np.ndarray:
        return self.queue.pop(count)

    def reset(self) -> None:
        self.queue.clear()
        self.is_streaming = False
        self.last_packet_time = 0.0
        self.total_packets_received = 0
        self.device_name = ""


class LaptopAudioInput:
    """Interface for captured laptop system audio from Windows WASAPI loopback."""

    def __init__(self):
        self.queue = AudioBufferQueue()
        self.is_capturing: bool = False

    def push_samples(self, pcm_data: np.ndarray) -> None:
        self.queue.push(pcm_data)

    def read_samples(self, count: int) -> np.ndarray:
        return self.queue.pop(count)

    def reset(self) -> None:
        self.queue.clear()
        self.is_capturing = False


def apply_soft_clipping_protection(signal: np.ndarray, threshold: float = 0.95) -> np.ndarray:
    """
    Applies musical soft-clipping saturation to audio when peaks exceed threshold,
    and hard clamps strictly between -1.0 and 1.0 to prevent DAC distortion.
    """
    peak = np.max(np.abs(signal)) if signal.size > 0 else 0.0
    if peak <= threshold:
        return signal

    # Apply soft tanh compression above threshold to preserve audio transients smoothly
    excess_mask = np.abs(signal) > threshold
    compressed = signal.copy()
    compressed[excess_mask] = (
        np.sign(signal[excess_mask]) * (
            threshold + (1.0 - threshold) * np.tanh((np.abs(signal[excess_mask]) - threshold) / (1.0 - threshold))
        )
    )

    # Strictly clamp within floating point unit bounds
    return np.clip(compressed, -1.0, 1.0)


def mix_pcm_buffers(
    laptop_buffer: np.ndarray,
    mobile_buffer: np.ndarray,
    laptop_gain: float = 1.0,
    mobile_gain: float = 1.0,
) -> np.ndarray:
    """
    Mixes two float32 PCM buffers with independent gains and clipping protection.
    Ensures dimension matching and zero padding when lengths differ.
    """
    # Standardize dimensions to 2D (samples, channels)
    if laptop_buffer.ndim == 1:
        laptop_buffer = laptop_buffer.reshape(-1, 1)
    if mobile_buffer.ndim == 1:
        mobile_buffer = mobile_buffer.reshape(-1, 1)

    max_len = max(len(laptop_buffer), len(mobile_buffer))
    channels = max(laptop_buffer.shape[1], mobile_buffer.shape[1])

    # Align laptop buffer
    laptop_aligned = np.zeros((max_len, channels), dtype=np.float32)
    laptop_aligned[:len(laptop_buffer), :laptop_buffer.shape[1]] = laptop_buffer * laptop_gain

    # Align mobile buffer
    mobile_aligned = np.zeros((max_len, channels), dtype=np.float32)
    mobile_aligned[:len(mobile_buffer), :mobile_buffer.shape[1]] = mobile_buffer * mobile_gain

    # Sum signals
    mixed = laptop_aligned + mobile_aligned

    # Apply soft saturation and hard clamping protection
    return apply_soft_clipping_protection(mixed)


def float32_to_int16(buffer: np.ndarray) -> np.ndarray:
    """
    Safely converts float32 [-1.0, 1.0] to int16 [-32768, 32767]
    with strict clamping to prevent overflow wrapping artifacts.
    """
    clamped = np.clip(buffer, -1.0, 1.0)
    scaled = np.where(clamped < 0, clamped * 32768.0, clamped * 32767.0)
    return np.clip(scaled, -32768.0, 32767.0).astype(np.int16)


class AudioMixerFoundation:
    """
    Orchestrates inputs, gains, and buffer mixing.
    """

    def __init__(self, mobile_gain: float = 1.0, laptop_gain: float = 1.0):
        self.mobile_input = MobileAudioInput()
        self.laptop_input = LaptopAudioInput()
        self.mobile_gain = max(0.0, min(1.5, mobile_gain))
        self.laptop_gain = max(0.0, min(1.5, laptop_gain))
        self.is_active = False

    def set_gains(self, mobile_gain: float, laptop_gain: float) -> None:
        self.mobile_gain = max(0.0, min(1.5, mobile_gain))
        self.laptop_gain = max(0.0, min(1.5, laptop_gain))

    def process_mix_frame(self, frame_size: int = 480) -> np.ndarray:
        """Reads a frame from both inputs and produces a mixed frame."""
        laptop_chunk = self.laptop_input.read_samples(frame_size)
        mobile_chunk = self.mobile_input.read_samples(frame_size)
        return mix_pcm_buffers(
            laptop_chunk,
            mobile_chunk,
            laptop_gain=self.laptop_gain,
            mobile_gain=self.mobile_gain,
        )

    def start(self) -> None:
        self.is_active = True

    def stop(self) -> None:
        self.is_active = False
        self.mobile_input.reset()
        self.laptop_input.reset()
