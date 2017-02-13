#!/usr/bin/env python
from __future__ import print_function, division
import numpy as np
import soundbridge

samplerate = 4000.


def read_samples(poll_length):
    from time import sleep
    num_samples = int(poll_length * samplerate)
    samples = np.zeros(num_samples)
    sleep(poll_length)
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
