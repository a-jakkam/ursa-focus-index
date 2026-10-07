import ast
from contextlib import redirect_stderr, redirect_stdout
import csv
import io
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
import warnings
from unittest.mock import Mock, patch

import numpy as np

from ursa_focus.cli import main
from ursa_focus.monitor import monitor_samples
from ursa_focus.signal import calculate_focus_index, classify_index
from ursa_focus.sources import demo_samples, live_samples, open_lsl_stream


class SignalTests(unittest.TestCase):
    def test_matches_supplied_function(self):
        original = Path(__file__).parents[1] / "legacy/original_eeg_stream.py"
        tree = ast.parse(original.read_text(encoding="utf-8"))
        function = next(n for n in tree.body if isinstance(n, ast.FunctionDef))
        namespace = {"np": np, "FS": 500}
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(original), "exec"), namespace)
        rng = np.random.default_rng(7)
        for size in (64, 128, 500, 1000):
            for rate in (128, 250, 500):
                data = rng.normal(size=size)
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", RuntimeWarning)
                    expected = namespace["calculate_focs"](data, rate)
                actual = calculate_focus_index(data, rate)
                if np.isfinite(expected):
                    self.assertEqual(actual, expected)
                else:
                    # Cleanup explicitly rejects empty bands instead of returning NaN.
                    self.assertIsNone(actual)

    def test_analytical_sine_ratio_and_scaling(self):
        t = np.arange(500) / 500
        data = np.sin(2*np.pi*6*t) + np.sin(2*np.pi*10*t) + np.sin(2*np.pi*20*t)
        # 18 beta bins, 6 alpha bins, 5 theta bins; one nonzero bin each.
        expected = round((1/18) / (1/6 + 1/5), 4)
        self.assertEqual(calculate_focus_index(data), expected)
        self.assertEqual(calculate_focus_index(10*data), expected)

    def test_invalid_windows(self):
        for data in ([], np.zeros(500), np.ones(20), np.full(500, np.nan), np.full(500, np.inf)):
            with self.subTest(size=len(data)):
                self.assertIsNone(calculate_focus_index(data))

    def test_invalid_rate_and_dimensions(self):
        for rate in (0, 60, -1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                calculate_focus_index(np.ones(500), rate)
        with self.assertRaises(ValueError):
            calculate_focus_index(np.ones((500, 2)))

    def test_band_thresholds(self):
        for value, label in ((0, "very_low_index"), (0.1499, "very_low_index"),
                             (0.15, "low_index"), (0.2999, "low_index"),
                             (0.3, "moderate_index"), (0.4999, "moderate_index"),
                             (0.5, "high_index")):
            self.assertEqual(classify_index(value), label)
        for value in (-1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                classify_index(value)


class MonitorTests(unittest.TestCase):
    def test_windows_and_source_timestamps(self):
        result = list(monitor_samples(demo_samples(500, 3), 500))
        self.assertEqual(len(result), 3)
        self.assertEqual([x.timestamp for x in result], [0.998, 1.998, 2.998])
        self.assertTrue(all(x.channel == 0 for x in result))

    def test_selected_channel(self):
        samples = [([0, s[0]], ts) for s, ts in demo_samples(500, 1)]
        self.assertEqual(len(list(monitor_samples(samples, 500, channel=1))), 1)
        self.assertEqual(list(monitor_samples(samples, 500, channel=0)), [])

    def test_warmup_and_missing_channel(self):
        self.assertEqual(list(monitor_samples(demo_samples(500, 0.5), 500)), [])
        with self.assertRaises(ValueError):
            list(monitor_samples([([], 0)], 500))

    def test_invalid_config(self):
        for kwargs in ({"sample_rate": 0}, {"channel": -1}, {"window_size": 63}, {"interval": 0}):
            values = {"sample_rate": 500, **kwargs}
            with self.assertRaises(ValueError):
                list(monitor_samples([], **values))


class AcquisitionTests(unittest.TestCase):
    def fake_pylsl(self, streams):
        return SimpleNamespace(resolve_byprop=Mock(return_value=streams), StreamInlet=Mock())

    def test_metadata_and_explicit_rate(self):
        info = SimpleNamespace(channel_count=lambda: 3, nominal_srate=lambda: 250)
        fake = self.fake_pylsl([info])
        with patch.dict(sys.modules, {"pylsl": fake}):
            inlet, rate = open_lsl_stream("EXG", None, 0, None, 5)
            self.assertEqual(rate, 250)
            self.assertIs(inlet, fake.StreamInlet.return_value)
            self.assertEqual(open_lsl_stream("EXG", None, 0, 500, 5)[1], 500)
        fake.resolve_byprop.assert_called_with("type", "EXG", minimum=1, timeout=5)

    def test_missing_and_ambiguous_streams(self):
        for streams in ([], [Mock(), Mock()]):
            with patch.dict(sys.modules, {"pylsl": self.fake_pylsl(streams)}):
                with self.assertRaises(RuntimeError):
                    open_lsl_stream("EXG", None, 0, None, 5)

    def test_stream_name_type_channel_and_rate(self):
        info = SimpleNamespace(type=lambda: "EXG", channel_count=lambda: 1, nominal_srate=lambda: 0)
        fake = self.fake_pylsl([info])
        with patch.dict(sys.modules, {"pylsl": fake}):
            self.assertEqual(open_lsl_stream("EXG", "sensor", 0, 500, 5)[1], 500)
            with self.assertRaises(ValueError):
                open_lsl_stream("EXG", "sensor", 1, 500, 5)
            with self.assertRaises(ValueError):
                open_lsl_stream("EXG", "sensor", 0, None, 5)
            with self.assertRaises(RuntimeError):
                open_lsl_stream("EEG", "sensor", 0, 500, 5)

    def test_timeout_does_not_loop_forever(self):
        inlet = Mock()
        inlet.pull_sample.side_effect = [([1], 4.2), (None, None)]
        source = live_samples(inlet, 5)
        self.assertEqual(next(source), ([1], 4.2))
        with self.assertRaises(RuntimeError):
            next(source)


class CliTests(unittest.TestCase):
    def test_demo_csv_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "demo.csv"
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(["--demo", "--seconds", "3", "--output", str(destination)]), 0)
            with destination.open(newline="") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 3)
            self.assertTrue(all(row["source"] == "synthetic_demo" for row in rows))
            self.assertTrue(all(row["clock_domain"] == "relative_seconds" for row in rows))
            before = destination.read_bytes()
            with redirect_stderr(io.StringIO()):
                self.assertEqual(main(["--demo", "--output", str(destination)]), 1)
            self.assertEqual(destination.read_bytes(), before)

    def test_invalid_arguments(self):
        for args in (["--sample-rate", "0"], ["--interval", "nan"], ["--window-size", "10"], ["--channel", "-1"]):
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as result:
                main(args)
            self.assertEqual(result.exception.code, 2)

    def test_live_inlet_closed(self):
        inlet = Mock()
        with patch("ursa_focus.cli.open_lsl_stream", return_value=(inlet, 500)), \
             patch("ursa_focus.cli.live_samples", return_value=iter([])), \
             redirect_stdout(io.StringIO()):
            self.assertEqual(main([]), 0)
        inlet.close_stream.assert_called_once()


if __name__ == "__main__":
    unittest.main()

