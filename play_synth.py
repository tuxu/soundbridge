#!/usr/bin/env python
from __future__ import print_function, division
import numpy as np
import soundbridge

samplerate = 4000.


def read_samples(poll_length):
    from time import sleep
    start_time = getattr(read_samples, 'start_time', 0)
    num_samples = int(poll_length * samplerate)
    time = start_time + np.arange(num_samples) / samplerate
    samples = 10 * np.sin(2 * np.pi * 3 * time)
    sleep(poll_length)
    read_samples.start_time = time[-1] + 1.0 / samplerate
    return samples


def main():
    """Setup the resampling and audio output callbacks and start playback."""

    print("Playing back...  Ctrl+C to stop.")
    with soundbridge.Soundbridge(samplerate) as bridge:
        bridge.output_processor = soundbridge.FMOutputProcessor()
        try:
            while True:
                samples = read_samples(0.050)
                bridge.push_samples(samples)
        except KeyboardInterrupt:
            print("Aborting.")


if __name__ == '__main__':
    main()
