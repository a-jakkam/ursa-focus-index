"""The original spectral calculation, separated from stream acquisition."""

import math

import numpy as np


def calculate_focus_index(data, sample_rate: float = 500.0) -> float | None:
    """Return beta / (alpha + theta), using mean squared FFT magnitudes.

    This preserves the supplied script's inclusive band edges and four-place
    rounding. No filtering, detrending, windowing, or artifact rejection is
    applied. Invalid or insufficient windows return None.
    """
    if not math.isfinite(sample_rate) or sample_rate <= 60:
        raise ValueError("Sample rate must be finite and greater than 60 Hz.")
    values = np.asarray(data, dtype=float)
    if values.ndim != 1:
        raise ValueError("Expected a single channel of one-dimensional samples.")
    if values.size < 64 or not np.all(np.isfinite(values)):
        return None
    magnitudes = np.abs(np.fft.rfft(values))
    frequencies = np.fft.rfftfreq(values.size, d=1 / sample_rate)
    powers = []
    for low, high in ((13, 30), (8, 13), (4, 8)):
        band = magnitudes[(frequencies >= low) & (frequencies <= high)]
        if not band.size:
            return None
        with np.errstate(over="ignore", invalid="ignore"):
            power = float(np.mean(band**2))
        if not math.isfinite(power):
            return None
        powers.append(power)
    beta, alpha, theta = powers
    denominator = alpha + theta
    if denominator <= 0 or not math.isfinite(denominator):
        return None
    result = beta / denominator
    return round(result, 4) if math.isfinite(result) else None


def classify_index(value: float) -> str:
    """Apply the original thresholds with neutral, nonvalidated labels."""
    if not math.isfinite(value) or value < 0:
        raise ValueError("Index must be finite and nonnegative.")
    if value >= 0.5:
        return "high_index"
    if value >= 0.3:
        return "moderate_index"
    if value >= 0.15:
        return "low_index"
    return "very_low_index"

