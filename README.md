# URSA Focus Index

A Python utility for monitoring an experimental EEG spectral index from a
Lab Streaming Layer (LSL) stream. This repository packages the EEG component
of an undergraduate research project exploring cognitive workload during VR
simulations.

The supplied implementation reads an `EXG` stream and reports
`beta / (alpha + theta)` from a rolling window. The refactored version keeps
that calculation, separates acquisition from processing, and adds a synthetic
demo, configurable settings, optional CSV logging, and automated tests.

**Scope:** this repository contains the EEG reader only. The project's web
dashboard, ECG analysis, eye-tracking integration, and VR software were not
provided and are not implemented here. No participant recordings or session
reports are included.

## Quick start

Use Python 3.10 or newer. Open a terminal in this folder:

```bash
python -m venv .venv
```

Activate the environment:

```bash
# macOS / Linux
source .venv/bin/activate
```

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Install and run a six-second synthetic recording (processed immediately):

```bash
python -m pip install -e .
python -m ursa_focus --demo
```

The demo combines synthetic 6 Hz, 10 Hz, and 20 Hz signals with noise. Its
changing beta amplitude illustrates the index calculation; it is not a
simulation or measurement of a person's cognitive state.

## Live EEG stream

```bash
python -m pip install -e ".[lsl]"
python -m ursa_focus --stream-type EXG
```

Start your device's LSL publisher first. Confirm that the selected channel
contains EEG rather than another EXG signal. The reader uses the stream's
advertised sample rate; the original script assumed 500 Hz. A missing or
incorrect rate can be overridden explicitly:

```bash
python -m ursa_focus --stream-type EXG --stream-name "Your stream name" --channel 0 --sample-rate 500
```

`--channel` is zero-based. Use Ctrl+C to stop. Discovery and sample acquisition
have a five-second timeout, configurable with `--timeout`. Live mode requires
the native `liblsl` library as well as `pylsl`; see the
[official pylsl installation instructions](https://github.com/labstreaminglayer/pylsl).
If discovery fails, check the publisher, stream name/type, local network, and
firewall. If multiple streams are detected, select one by name.

## Local logging

```bash
python -m ursa_focus --demo --seconds 9 --output outputs/demo.csv
python -m ursa_focus --stream-type EXG --output outputs/session.csv
```

CSV output contains the last sample's timestamp, clock domain, source mode,
sample rate, window size, channel, index, and threshold band. Existing files
are refused rather than overwritten. These logs contain calculated results,
not raw EEG samples.

Demo timestamps are relative seconds. Live timestamps retain the LSL source
clock; they are not calendar dates or UTC. This reader does not perform
cross-stream clock correction, gap detection, or multimodal synchronization.

## Method

With a default 500-sample window at 500 Hz, a result is produced after the
first full window and then every 500 samples. `--window-size` and `--interval`
configure this behavior. Reporting follows sample counts rather than the
original script's wall-clock print timer.

| Band | Inclusive frequency range |
| --- | --- |
| Theta | 4-8 Hz |
| Alpha | 8-13 Hz |
| Beta | 13-30 Hz |

For each band, the code calculates the mean squared magnitude of its FFT
bins, then rounds `beta / (alpha + theta)` to four decimal places. It preserves
the original overlapping 8 Hz and 13 Hz boundary bins. This is not integrated
bandpower or a Welch PSD estimate. Insufficient, nonfinite, empty-band, and
zero-denominator windows produce no result.

| Index range | Output label |
| --- | --- |
| >= 0.50 | `high_index` |
| 0.30 to < 0.50 | `moderate_index` |
| 0.15 to < 0.30 | `low_index` |
| < 0.15 | `very_low_index` |

The thresholds come from the supplied script. No supporting validation study
was supplied, so these labels describe numerical bands rather than confirmed
focus, workload, or mental states. The implementation does not apply
filtering, artifact rejection, baseline calibration, or clinical validation.

## Repository layout

```text
src/ursa_focus/       Signal calculation, acquisition, processing, and CLI
tests/               Offline regression and acquisition-adapter tests
docs/provenance.md   Supplied components and changes made during cleanup
legacy/              Unmodified original EEG script for reference
```

Run the checks:

```bash
python -m unittest discover -s tests -v
```

Tests do not need a device or pylsl. They compare the calculation against the
original function and exercise configuration, invalid windows, logging, and
mocked stream discovery. Physical hardware acquisition must be verified in
the lab.

## Data and publication

Raw CSV recordings and the session PDF are excluded from this repository.
`.gitignore` also excludes common sensor files, generated outputs, environment
files, and archives. Keep real recordings outside public version control;
`.gitignore` does not remove files that have already been tracked.

Review research ownership and permissions before making this repository
public. No open-source license has been assigned; choose one once the relevant
permissions are established.

