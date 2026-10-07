# Source provenance and cleanup

## Supplied material

- `eeg_stream(1).py`: the original executable EEG reader; preserved verbatim
  as `legacy/original_eeg_stream.py`.
- Two CSV recordings: inspected for their schemas and excluded from the repo.
  Their columns were `Counter, Channel1` and `Sample Counter, CH0`.
  Neither header establishes sample rate, EEG provenance, or synchronized time.
- A session-report PDF: excluded. No report generator or underlying analysis
  code was supplied.
- `ChordsWeb.zip(1).url`: a Windows Internet Shortcut pointing to
  `http://chordsweb.zip/`, not a ZIP archive. No dashboard source was available.

## Preserved behavior

- Default EXG stream type, channel 0, and 500-sample window.
- Mean squared FFT magnitude in theta, alpha, and beta bands.
- Inclusive frequency boundaries, four-place rounding, and thresholds
  0.15 / 0.30 / 0.50.
- No result for a zero denominator or fewer than 64 samples.

## Changes introduced during repository cleanup

- Package structure and import-safe command-line entry point.
- Current `pylsl.resolve_byprop` acquisition interface and optional dependency.
- Sample rate read from stream metadata, with an explicit override.
- One selected channel buffered instead of three buffers with only one used.
- Bounded stream discovery/acquisition waits, validation, and clean shutdown.
- Reporting based on received sample counts rather than wall-clock printing.
- Rejection of nonfinite data and missing frequency bands.
- Numerical labels replacing the original unvalidated cognitive-state labels.
- Synthetic demo and timestamped CSV result logging, newly added here.
- Offline regression tests and mocked LSL adapter tests.

The refactor intentionally leaves the original spectral estimator unchanged.
Do not describe the synthetic demo, new logging, or new tests as work performed
during the original research period. The provided code alone does not establish
ECG processing, eye-tracking processing, cross-sensor synchronization, a web
dashboard, or VR integration.

## Acquisition references

- [Official pylsl repository](https://github.com/labstreaminglayer/pylsl)
- [LSL stream introduction](https://labstreaminglayer.readthedocs.io/info/intro.html)
- [LSL user guide](https://labstreaminglayer.readthedocs.io/info/user_guide.html)

