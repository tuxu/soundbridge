#!/usr/bin/env python
from __future__ import print_function, division

import zhinst.utils
import soundbridge


default_params = {
    'demod': 3,  # Source demodulator
    'input_signal': 'x',  # Demod signal (frequency, x, y, phi)
    'freqcenter_pll': 0,  # PLL to use to query center frequency
    'highpass': True,  # Filter the input signal?
    'samplerate': 3600,  # Sample rate (Hz)
}

fm_params = {
    'gain': 20.,
    'demod': 0,
    'input_signal': 'frequency',
    'carrier_frequency': 500,
    'modulate': True,
    'highpass': False,
}


class InputSampler(object):
    def __init__(self, device, params):
        self._device = device
        self._params = params
        self._daq = None
        self._paths = {}
        self._device = None
        self._freqcenter = 0

    def setup(self):
        apilevel = 1
        daq, device, _ = zhinst.utils.create_api_session(self._device,
                                                         apilevel)

        params = self._params
        demod = params['demod']
        samplerate = params['samplerate']
        settings = [
            ('/{}/demods/{}/rate'.format(device, demod), samplerate),
        ]
        daq.set(settings)
        daq.sync()

        samplerate_path = '/{}/demods/{}/rate'.format(device, demod)
        samplerate = daq.getDouble(samplerate_path)

        demodsample_path = '/{}/demods/{}/sample'.format(device, demod)

        pll = params['freqcenter_pll']
        freqcenter_path = '/{}/plls/{}/freqcenter'.format(device, pll)
        self._freqcenter = daq.getDouble(freqcenter_path)

        daq.unsubscribe('*')

        paths = [
            samplerate_path,
            demodsample_path,
            freqcenter_path,
        ]
        daq.subscribe(paths)

        self._daq = daq
        self._device = device
        self._paths = {
            'samplerate': samplerate_path,
            'demodsample': demodsample_path,
            'freqcenter': freqcenter_path
        }

    def read(self, poll_length):
        if self._daq is None:
            return []
        daq = self._daq
        paths = self._paths
        params = self._params
        data = daq.poll(poll_length, poll_timeout=10, poll_flags=0,
                        poll_return_flat_dict=True)

        # Update center frequency if changed
        if paths['freqcenter'] in data:
            self._freqcenter = data[paths['freqcenter']][-1]

        samples = data[paths['demodsample']][params['input_signal']]

        if params['input_signal'] == 'frequency':
            samples -= self._freqcenter

        if params['highpass']:
            samples -= samples.mean()

        return samples


def main():
    """Setup the resampling and audio output callbacks and start playback."""

    device = 'dev823'
    params = default_params.copy()
    input_sampler = InputSampler(device, params)
    input_sampler.setup()

    print("Playing back...  Ctrl+C to stop.")
    with soundbridge.Soundbridge(params['samplerate']) as bridge:
        bridge.output_processor = soundbridge.FMOutputProcessor()
        try:
            while True:
                samples = input_sampler.read(0.050)
                bridge.push_samples(samples)
        except KeyboardInterrupt:
            print("Aborting.")


if __name__ == '__main__':
    main()
