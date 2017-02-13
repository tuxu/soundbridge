#!/usr/bin/env python
from __future__ import print_function, division

import click
import numpy as np
import soundbridge

default_device = 'dev823'
default_params = {
    'samplerate': 3600,  # Sample rate (Hz)
    'demod': 0,  # Source demodulator
    'signal': 'x',  # Demod signal (frequency, x, y, phase)
    'gain': 1.,  # Input gain
    'volume': 0.1, # Output volume
    'pll': 0,  # PLL used to query center frequency
    'carrier_frequency': 500,  # FM carrier frequency
    'modulation': True,  # Perform frequency modulation?
    'highpass': True,  # Filter the input signal?
}

valid_signals = ['x', 'y', 'frequency', 'phase', 'auxin0', 'auxin1']

class InputSampler(object):
    def __init__(self, device, params):
        self._device = device
        self._params = params
        self._daq = None
        self._paths = {}
        self._device = None
        self._freqcenter = 0

    def setup(self):
        import zhinst.utils
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

        pll = params['pll']
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
        daq = self._daq
        paths = self._paths
        params = self._params

        if daq is None:
            # Return zero-samples if nothing can be read
            from time import sleep
            sleep(poll_length)
            num_samples = int(poll_length * params['samplerate'])
            return np.zeros(num_samples)

        data = daq.poll(poll_length, poll_timeout=10, poll_flags=0,
                        poll_return_flat_dict=True)

        # Update center frequency if changed
        if paths['freqcenter'] in data:
            self._freqcenter = data[paths['freqcenter']][-1]

        samples = data[paths['demodsample']][params['signal']]

        if params['signal'] == 'frequency':
            samples -= self._freqcenter

        if params['highpass']:
            # Extremely crude high-pass filter...
            samples -= samples.mean()

        return samples


def print_parameters(params):
    click.echo(click.style('Parameters:', bold=True))
    items = [
        ('Sample rate (Hz)', 'samplerate'),
        ('Demodulator', 'demod'),
        ('Signal', 'signal'),
        ('Input gain', 'gain'),
        ('Volume', 'volume'),
        ('PLL', 'pll'),
        ('FM carrier frequency (Hz)', 'carrier_frequency'),
        ('Perform frequency modulation?', 'modulation'),
        ('Filter input signal?', 'highpass')
    ]
    for label, key in items:
        label = label if label.endswith('?') else label + ':'
        click.echo(
            '  {} {}'.format(click.style(label, fg='white'), params[key]))


@click.command()
@click.argument('device', default=default_device)
@click.option('--samplerate', '-r', default=default_params['samplerate'],
              help='sample rate (Hz)')
@click.option('--demod', '-d', default=default_params['demod'],
              type=click.IntRange(0, 6),
              help='input demodulator')
@click.option('--signal', '-s', default=default_params['signal'],
              type=click.Choice(valid_signals),
              help='input demod signal, e.g. x, frequency')
@click.option('--gain', '-g', default=default_params['gain'],
              help='input gain')
@click.option('--volume', '-v', default=default_params['volume'],
              help='output volume')
@click.option('--pll', '-p', default=default_params['pll'],
              type=click.IntRange(0, 2),
              help='PLL to read center frequency (frequency input only)')
@click.option('--carrier-frequency', '-f', default=default_params['carrier_frequency'],
              help='FM carrier frequency')
@click.option('--modulation/--no-modulation', '+m/-m',
              default=default_params['modulation'],
              help='Perform frequncy modulation?')
@click.option('--highpass/--no-highpass', '+h/-h',
              default=default_params['highpass'],
              help='Filter input signal?')
def main(device=None, **kwargs):
    """Route a signal from a Zurich Instruments lock-in amplifier (DEVICE) to
       the standard sound output.
    """
    click.echo('{} {}'.format(click.style('Device:', bold=True), device))

    params = default_params.copy()
    # Update only available parameters
    for key in default_params:
        if key in kwargs:
            params[key] = kwargs[key]
        else:
            raise KeyError('Invalid parameter: {}'.format(key))

    print_parameters(params)

    input_sampler = InputSampler(device, params)
    input_sampler.setup()

    click.echo(
        '{}  {}'.format(click.style('Playing back...', fg='green'),
                        click.style('Ctrl+C to stop.', fg='white')))

    with soundbridge.Soundbridge(params['samplerate']) as bridge:
        # Set up output processor
        processor_type = (soundbridge.FMOutputProcessor if params['modulation']
                          else soundbridge.OutputProcessor)
        output_processor = processor_type()
        if params['modulation']:
            output_processor.carrier_frequency = params['carrier_frequency']
        output_processor.input_gain = params['gain']
        output_processor.output_volume = params['volume']
        bridge.output_processor = output_processor

        try:
            while True:
                samples = input_sampler.read(0.050)
                bridge.push_samples(samples)
        except KeyboardInterrupt:
            click.echo(click.style('Aborting.', fg='red'))


if __name__ == '__main__':
    main()
