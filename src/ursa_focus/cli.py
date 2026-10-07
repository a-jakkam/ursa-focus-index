"""Command-line entry point; importing this module never connects to a device."""

import argparse
import csv
from contextlib import ExitStack
import math
from pathlib import Path
import sys

from .monitor import monitor_samples
from .sources import demo_samples, live_samples, open_lsl_stream


def parser():
    p = argparse.ArgumentParser(description="Monitor the experimental URSA EEG spectral index.")
    p.add_argument("--demo", action="store_true", help="Run synthetic data without a device.")
    p.add_argument("--seconds", type=float, default=6, help="Synthetic demo duration (default: 6).")
    p.add_argument("--stream-type", default="EXG")
    p.add_argument("--stream-name", help="Select a specific LSL stream by name.")
    p.add_argument("--sample-rate", type=float, help="Hz; defaults to LSL metadata or 500 in demo.")
    p.add_argument("--channel", type=int, default=0, help="Zero-based channel (default: 0).")
    p.add_argument("--window-size", type=int, default=500, help="Samples per FFT window.")
    p.add_argument("--interval", type=float, default=1, help="Reporting interval in signal seconds.")
    p.add_argument("--timeout", type=float, default=5, help="LSL discovery and sample timeout in seconds.")
    p.add_argument("--output", type=Path, help="Optional local CSV; existing files are never overwritten.")
    return p


def main(argv=None):
    p = parser()
    args = p.parse_args(argv)
    for name in ("seconds", "interval", "timeout"):
        value = getattr(args, name)
        if not math.isfinite(value) or value <= 0:
            p.error(f"--{name.replace('_', '-')} must be positive and finite")
    if args.channel < 0 or args.window_size < 64:
        p.error("--channel must be nonnegative and --window-size at least 64")
    if args.sample_rate is not None and (
        not math.isfinite(args.sample_rate) or args.sample_rate <= 60
    ):
        p.error("--sample-rate must be finite and greater than 60 Hz")
    try:
        with ExitStack() as stack:
            writer = None
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                output = stack.enter_context(args.output.open("x", newline="", encoding="utf-8"))
                writer = csv.writer(output)
                writer.writerow(["timestamp", "clock_domain", "source", "sample_rate_hz",
                                 "window_samples", "channel", "focus_index", "index_band"])
            if args.demo:
                rate = args.sample_rate or 500.0
                samples = demo_samples(rate, args.seconds, args.channel)
                source, clock = "synthetic_demo", "relative_seconds"
                print("Synthetic demo | Experimental index; thresholds are not validated.")
            else:
                inlet, rate = open_lsl_stream(args.stream_type, args.stream_name,
                                             args.channel, args.sample_rate, args.timeout)
                stack.callback(inlet.close_stream)
                samples = live_samples(inlet, args.timeout)
                source, clock = "live_lsl", "lsl_source_clock"
                print(f"Connected | {rate:g} Hz | channel {args.channel} | Experimental index")
            for result in monitor_samples(samples, rate, args.channel, args.window_size, args.interval):
                print(f"Index: {result.focus_index:.4f} | {result.index_band}")
                if writer:
                    writer.writerow([result.timestamp, clock, source, rate, args.window_size,
                                     result.channel, result.focus_index, result.index_band])
                    output.flush()
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")
        return 0
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0
