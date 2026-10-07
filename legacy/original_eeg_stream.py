import numpy as np
from collections import deque
from pylsl import StreamInlet, resolve_stream
import time

print("Looking for LSL stream...")
streams = resolve_stream('type', 'EXG')
inlet = StreamInlet(streams[0])
print("Connected!\n")

NUM_CHANNELS = 3
BUFFER_SIZE  = 500
FS           = 500  # sample rate Hz

# Research-grounded thresholds for beta/(alpha+theta)
THRESHOLD_HIGH_FOCUS    = 0.5   # active cognitive engagement
THRESHOLD_MODERATE_LOW  = 0.3   # dropping out of engagement
THRESHOLD_MIND_WANDER   = 0.15  # mind wandering / disengaged

buffers = [deque(maxlen=BUFFER_SIZE) for _ in range(NUM_CHANNELS)]

def calculate_focs(data, fs=FS):
    data = np.array(data)
    if len(data) < 64:
        return None
    fft_vals = np.abs(np.fft.rfft(data))
    freqs    = np.fft.rfftfreq(len(data), d=1/fs)
    beta  = np.mean(fft_vals[(freqs >= 13) & (freqs <= 30)] ** 2)
    alpha = np.mean(fft_vals[(freqs >= 8)  & (freqs <= 13)] ** 2)
    theta = np.mean(fft_vals[(freqs >= 4)  & (freqs <= 8)]  ** 2)
    if (alpha + theta) == 0:
        return None
    return round(beta / (alpha + theta), 4)

last_print = time.time()
PRINT_EVERY = 1.0  # seconds

while True:
    sample, timestamp = inlet.pull_sample()
    for i in range(NUM_CHANNELS):
        buffers[i].append(sample[i])

    now = time.time()
    if len(buffers[0]) == BUFFER_SIZE and (now - last_print) >= PRINT_EVERY:
        last_print = now
        focs = calculate_focs(list(buffers[0]))

        if focs is not None:
            if focs >= THRESHOLD_HIGH_FOCUS:
                state = "🔴 HIGH FOCUS — active cognitive load"
            elif focs >= THRESHOLD_MODERATE_LOW:
                state = "🟡 MODERATE — engaged but easing"
            elif focs >= THRESHOLD_MIND_WANDER:
                state = "🟠 LOW — relaxed / transitioning"
            else:
                state = "🔵 MIND WANDERING — disengaged"

            print(f"FOCS: {focs:.4f} | {state}")