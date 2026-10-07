"""Bounded-window processing, independent of the underlying sample source."""

from collections import deque
from dataclasses import dataclass
import math

from .signal import calculate_focus_index, classify_index


@dataclass(frozen=True)
class Measurement:
    timestamp: float
    channel: int
    focus_index: float
    index_band: str


def monitor_samples(samples, sample_rate: float, channel: int = 0,
                    window_size: int = 500, interval: float = 1.0):
    """Yield an index after a full window, then every interval of samples.

    Cadence uses the nominal sample rate, not wall-clock execution speed.
    Timestamps identify the last sample in each window and retain the source's
    clock domain; they are not UTC or proof of multimodal synchronization.
    """
    if not math.isfinite(sample_rate) or sample_rate <= 60:
        raise ValueError("Sample rate must be finite and greater than 60 Hz.")
    if channel < 0 or window_size < 64:
        raise ValueError("Channel must be nonnegative and window size at least 64.")
    if not math.isfinite(interval) or interval <= 0:
        raise ValueError("Interval must be positive and finite.")
    stride = max(1, round(sample_rate * interval))
    buffer = deque(maxlen=window_size)
    for count, (sample, timestamp) in enumerate(samples, start=1):
        if channel >= len(sample):
            raise ValueError(f"Sample does not contain channel {channel}.")
        buffer.append(float(sample[channel]))
        if count < window_size or (count - window_size) % stride:
            continue
        value = calculate_focus_index(buffer, sample_rate)
        if value is not None:
            yield Measurement(float(timestamp), channel, value, classify_index(value))

