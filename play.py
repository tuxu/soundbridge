#!/usr/bin/env python
from __future__ import print_function, division
import numpy as np

import sounddevice as sd
import samplerate as sr

import zhinst.utils
from fifo import FIFO

samplerate = 3600
target_samplerate = 44100
converter_type = 'sinc_fastest'

default_params = {
    'gain': 10000.,  # Output gain (1/input unit)
    'output_volume': 0.1,  # Output volume
    'demod': 3,  # Source demodulator
    'input_signal': 'x',  # Demod signal (frequency, x, y, phi)
    'freqcenter_pll': 0,  # PLL to use to query center frequency
    'carrier_frequency': 500,  # Carrier frequency (Hz)
    'modulate': False,  # Modulate onto carrier?
    'highpass': True,  # Filter the input signal?
}


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


fifo = FIFO(samplerate)


def read_fifo():
    frames = fifo.num_available()
    if frames == 0:
        # Return at least a single frame when the buffer is empty.
        return [0]
    return fifo.read(frames)


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
    fifo.write(samples)

read_samples.freqcenter = freqcenter


def get_playback_callback(resampler, samplerate, params):
    """Return a sound playback callback.

    Parameters
    ----------
    resampler : samplerate.converters.CallbackResampler
        The resampler from which samples are read.
    samplerate : float
        The sample rate.
    params : dict
        Parameters for FM generation.
    """

    def callback(outdata, frames, time, _):
        """Playback callback.

        Read samples from the resampler and modulate them onto a carrier
        frequency.
        """
        samples = params['gain'] * resampler.read(frames)
        samples = np.pad(samples, (0, frames - len(samples)), mode='constant')

        if params['modulate']:
            # Perform frequency modulation
            last_fmphase = getattr(callback, 'last_fmphase', 0)
            t = time.outputBufferDacTime + np.arange(frames) / samplerate
            phase = 2 * np.pi * params['carrier_frequency'] * t
            fmphase = (last_fmphase +
                       2 * np.pi * np.cumsum(samples) / samplerate)
            samples = np.cos(phase + fmphase)
            callback.last_fmphase = fmphase[-1]

        outdata[:, 0] = params['output_volume'] * samples

    return callback


def main(source_samplerate, target_samplerate, params, converter_type):
    """Setup the resampling and audio output callbacks and start playback."""
    ratio = target_samplerate / source_samplerate

    with sr.callback_resampler(read_fifo, ratio,
                               converter_type) as resampler, \
         sd.OutputStream(channels=1, samplerate=target_samplerate,
                         callback=get_playback_callback(
                             resampler, target_samplerate, params)):
        print("Playing back...  Ctrl+C to stop.")
        try:
            while True:
                read_samples(0.050)
        except KeyboardInterrupt:
            print("Aborting.")


if __name__ == '__main__':
    params = default_params.copy()
    #params.update(fm_params)

    fm_params = {
        'gain': 20.,
        'demod': 0,
        'input_signal': 'frequency',
        'carrier_frequency': 500,
        'modulate': True,
        'highpass': False,
    }

    main(source_samplerate=samplerate,
         target_samplerate=target_samplerate,
         params=params,
         converter_type=converter_type)
