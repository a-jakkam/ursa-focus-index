"""Live LSL acquisition and an explicitly synthetic demonstration source."""

import math

import numpy as np


def demo_samples(sample_rate: float, seconds: float, channel: int = 0):
    """Yield synthetic values and relative seconds; no human data is used."""
    rng = np.random.default_rng(42)
    for i in range(int(sample_rate * seconds)):
        timestamp = i / sample_rate
        # Change beta amplitude between three equally sized demo segments.
        segment = min(int(3 * timestamp / seconds), 2)
        beta_amplitude = (0.4, 1.0, 2.0)[segment]
        value = (
            np.sin(2 * np.pi * 6 * timestamp)
            + np.sin(2 * np.pi * 10 * timestamp)
            + beta_amplitude * np.sin(2 * np.pi * 20 * timestamp)
            + rng.normal(0, 0.05)
        )
        yield [float(value)] * (channel + 1), timestamp


def open_lsl_stream(stream_type: str, stream_name: str | None,
                    channel: int, sample_rate: float | None, timeout: float):
    """Resolve one stream and return its inlet and effective sample rate."""
    try:
        from pylsl import StreamInlet, resolve_byprop
    except (ImportError, RuntimeError) as error:
        raise RuntimeError(
            "Live mode requires pylsl and the native liblsl library. "
            "Install with: python -m pip install -e '.[lsl]'"
        ) from error
    prop, value = ("name", stream_name) if stream_name else ("type", stream_type)
    streams = resolve_byprop(prop, value, minimum=1, timeout=timeout)
    if stream_name:
        streams = [s for s in streams if s.type() == stream_type]
    if not streams:
        raise RuntimeError("No matching LSL stream found. Check your device and stream settings.")
    if len(streams) != 1:
        raise RuntimeError("Multiple streams matched. Use --stream-name to select a unique stream.")
    info = streams[0]
    if channel >= info.channel_count():
        raise ValueError(f"Channel {channel} is unavailable; stream has {info.channel_count()} channels.")
    rate = sample_rate if sample_rate is not None else float(info.nominal_srate())
    if not math.isfinite(rate) or rate <= 60:
        raise ValueError("Stream needs a sample rate above 60 Hz; set --sample-rate if metadata is missing.")
    return StreamInlet(info), rate


def live_samples(inlet, timeout: float):
    """Yield source-clock timestamps; stop if acquisition becomes idle."""
    while True:
        sample, timestamp = inlet.pull_sample(timeout=timeout)
        if sample is None:
            raise RuntimeError("No LSL sample received before the timeout; check the stream connection.")
        yield sample, timestamp

