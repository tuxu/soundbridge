#!/usr/bin/env python
from __future__ import print_function, division
import numpy as np

import zhinst.utils
import soundbridge


samplerate = 3600

default_params = {
    'demod': 3,  # Source demodulator
    'input_signal': 'x',  # Demod signal (frequency, x, y, phi)
    'freqcenter_pll': 0,  # PLL to use to query center frequency
    'highpass': True,  # Filter the input signal?
}

fm_params = {
    'gain': 20.,
    'demod': 0,
    'input_signal': 'frequency',
    'carrier_frequency': 500,
    'modulate': True,
    'highpass': False,
}

params = default_params.copy()


# Setup HF2 DAQ
device_id = 'dev823'
apilevel = 1
(daq, device, props) = zhinst.utils.create_api_session(device_id, apilevel)

settings = [
    ('/{}/demods/{}/rate'.format(device, params['demod']), samplerate),
]
daq.set(settings)
daq.sync()

samplerate_path = '/{}/demods/{}/rate'.format(device, params['demod'])
samplerate = daq.getDouble(samplerate_path)

demodsample_path = '/{}/demods/{}/sample'.format(device, params['demod'])

freqcenter_path = '/{}/plls/{}/freqcenter'.format(device,
                                                  params['freqcenter_pll'])
freqcenter = daq.getDouble(freqcenter_path)

daq.unsubscribe('*')

paths = [
    samplerate_path,
    demodsample_path,
    freqcenter_path,
]
daq.subscribe(paths)


def read_samples(poll_length):
    poll_timeout = 10
    poll_flags = 0
    poll_return_flat_dict = True
    data = daq.poll(poll_length, poll_timeout, poll_flags, poll_return_flat_dict)

    # Update center frequency if changed
    if freqcenter_path in data:
        read_samples.freqcenter = data[freqcenter_path][-1]

    samples = data[demodsample_path][params['input_signal']]

    if params['input_signal'] == 'frequency':
        samples -= read_samples.freqcenter

    if params['highpass']:
        samples -= samples.mean()

    return samples

read_samples.freqcenter = freqcenter


def main():
    """Setup the resampling and audio output callbacks and start playback."""

    print("Playing back...  Ctrl+C to stop.")
    with soundbridge.Soundbridge(samplerate) as sb:
        sb.output_processor = soundbridge.FMOutputProcessor()
        try:
            while True:
                samples = read_samples(0.050)
                sb.push_samples(samples)
        except KeyboardInterrupt:
            print("Aborting.")


if __name__ == '__main__':
    main()
