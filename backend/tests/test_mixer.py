"""Automated unit tests for Audio Mixer foundation, buffer mixing, gains, and clipping protection."""

import numpy as np
import pytest
from audio.mixer import (
    mix_pcm_buffers,
    apply_soft_clipping_protection,
    float32_to_int16,
    AudioMixerFoundation,
    AudioBufferQueue,
)


def test_buffer_queue_push_pop():
    """Verify FIFO queue ordering, sample counts, and underrun zero padding."""
    queue = AudioBufferQueue(max_samples=1000)
    data = np.ones((100, 2), dtype=np.float32) * 0.5
    queue.push(data)

    popped = queue.pop(50)
    assert popped.shape == (50, 2)
    assert np.allclose(popped, 0.5)

    # Pop remaining 50 + 20 excess (should pad remainder with zeros)
    popped_more = queue.pop(70)
    assert popped_more.shape == (70, 2)
    assert np.allclose(popped_more[:50], 0.5)
    assert np.allclose(popped_more[50:], 0.0)
    assert queue.underrun_count > 0


def test_mix_pcm_buffers_equal_lengths():
    """Verify linear combination of laptop and mobile buffers with matching lengths."""
    laptop = np.ones((100, 2), dtype=np.float32) * 0.2
    mobile = np.ones((100, 2), dtype=np.float32) * 0.3

    mixed = mix_pcm_buffers(laptop, mobile, laptop_gain=1.0, mobile_gain=1.0)
    assert mixed.shape == (100, 2)
    assert np.allclose(mixed, 0.5)


def test_mix_pcm_buffers_mismatched_lengths():
    """Verify that buffers of differing lengths are zero-padded without truncation."""
    laptop = np.ones((100, 2), dtype=np.float32) * 0.2
    mobile = np.ones((60, 2), dtype=np.float32) * 0.4

    mixed = mix_pcm_buffers(laptop, mobile, laptop_gain=1.0, mobile_gain=1.0)
    assert mixed.shape == (100, 2)
    # First 60 samples: 0.2 + 0.4 = 0.6
    assert np.allclose(mixed[:60], 0.6)
    # Remaining 40 samples: 0.2 + 0.0 = 0.2
    assert np.allclose(mixed[60:], 0.2)


def test_gain_adjustments():
    """Verify that independent gains (0% to 150%) scale buffers accurately."""
    laptop = np.ones((100, 2), dtype=np.float32) * 0.4
    mobile = np.ones((100, 2), dtype=np.float32) * 0.4

    # 50% laptop, 150% mobile
    mixed = mix_pcm_buffers(laptop, mobile, laptop_gain=0.5, mobile_gain=1.5)
    # 0.4 * 0.5 = 0.2; 0.4 * 1.5 = 0.6; sum = 0.8
    assert np.allclose(mixed, 0.8)

    # 0% laptop (mute), 100% mobile
    mixed_mute = mix_pcm_buffers(laptop, mobile, laptop_gain=0.0, mobile_gain=1.0)
    assert np.allclose(mixed_mute, 0.4)


def test_clipping_protection_and_limiting():
    """Verify soft saturation and strict clamping when signal sums exceed 1.0."""
    # Create extreme signals that sum to 2.0 (well above DAC clipping threshold)
    laptop = np.ones((100, 2), dtype=np.float32) * 1.0
    mobile = np.ones((100, 2), dtype=np.float32) * 1.0

    mixed = mix_pcm_buffers(laptop, mobile, laptop_gain=1.0, mobile_gain=1.0)
    # Must never exceed +1.0 or -1.0
    assert np.max(mixed) <= 1.0
    assert np.min(mixed) >= -1.0
    # Must be saturated above 0.95
    assert np.max(mixed) > 0.95

    # Negative extreme
    laptop_neg = np.ones((100, 2), dtype=np.float32) * -1.2
    mobile_neg = np.ones((100, 2), dtype=np.float32) * -0.9
    mixed_neg = mix_pcm_buffers(laptop_neg, mobile_neg, laptop_gain=1.0, mobile_gain=1.0)
    assert np.min(mixed_neg) >= -1.0
    assert np.max(mixed_neg) <= 1.0


def test_float32_to_int16_conversion():
    """Verify clean 16-bit PCM conversion without integer overflow/wrapping."""
    # Values from -1.5 to +1.5
    raw_float = np.array([-1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5], dtype=np.float32)
    pcm16 = float32_to_int16(raw_float)

    assert pcm16.dtype == np.int16
    assert pcm16[0] == -32768  # Clamped, not wrapped to positive
    assert pcm16[1] == -32768  # -1.0 maps cleanly to -32768 (0x8000)
    assert pcm16[3] == 0
    assert pcm16[5] == 32767
    assert pcm16[6] == 32767  # Clamped, not wrapped to negative


def test_audio_mixer_foundation_lifecycle():
    """Verify mixer start, stop, gain updates, and frame generation."""
    mixer = AudioMixerFoundation(mobile_gain=0.8, laptop_gain=1.2)
    assert not mixer.is_active

    mixer.start()
    assert mixer.is_active

    mixer.set_gains(1.0, 0.5)
    assert mixer.mobile_gain == 1.0
    assert mixer.laptop_gain == 0.5

    # Push sample data
    mixer.laptop_input.push_samples(np.ones((240, 2), dtype=np.float32) * 0.4)
    mixer.mobile_input.receive_packet(np.ones((240, 2), dtype=np.float32) * 0.2)

    frame = mixer.process_mix_frame(240)
    assert frame.shape == (240, 2)
    # Expected: 0.4 * 0.5 + 0.2 * 1.0 = 0.2 + 0.2 = 0.4
    assert np.allclose(frame, 0.4)

    mixer.stop()
    assert not mixer.is_active
    assert mixer.mobile_input.queue.available_samples == 0
