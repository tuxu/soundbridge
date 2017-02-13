from __future__ import print_function, division
import numpy as np

import sounddevice as sd
import samplerate as sr

from fifo import FIFO


class OutputProcessor(object):
    input_gain = 20.  # Input gain (1/input sample unit)
    output_volume = 0.1  # Output volume

    def process(self, samples, _samplerate, **_kwargs):
        """Process output samples."""
        return self.output_volume * self.input_gain * samples


class FMOutputProcessor(OutputProcessor):
    carrier_frequency = 500  # Carrier frequency (Hz)

    def __init__(self, ):
        self._last_fmphase = 0

    def process(self, samples, samplerate, **kwargs):
        """Perform frequency modulation with samples and return output samples.

        """
        samples = self.input_gain * samples
        time = (kwargs['time'].outputBufferDacTime +
                np.arange(samples.size) / samplerate)
        phase = 2 * np.pi * self.carrier_frequency * time
        fmphase = (self._last_fmphase +
                   2 * np.pi * np.cumsum(samples) / samplerate)
        output_samples = np.cos(phase + fmphase)
        self._last_fmphase = fmphase[-1]
        return self.output_volume * output_samples


class Soundbridge(object):
    """Bridge a sample producer to the sound output, resampling as required.

    """
    def __init__(self, input_samplerate, output_samplerate=None, bufsize=4096,
                 converter_type='sinc_fastest'):
        if output_samplerate is None:
            default_output = sd.default.device[1]
            device_parameters = sd.query_devices(default_output)
            output_samplerate = device_parameters['default_samplerate']
        self._output_samplerate = output_samplerate
        self._fifo = FIFO(bufsize)
        ratio = output_samplerate / input_samplerate
        self._resampler = sr.CallbackResampler(self._read_fifo, ratio,
                                               converter_type)
        self._outstream = sd.OutputStream(
            channels=1, samplerate=output_samplerate,
            callback=self._output_callback)
        self._last_fmphase = 0
        self._output_processor = OutputProcessor()

    @property
    def output_processor(self):
        return self._output_processor

    @output_processor.setter
    def output_processor(self, fun):
        self._output_processor = fun

    def push_samples(self, samples):
        """Push samples into the input buffer."""
        self._fifo.write(samples)

    def _read_fifo(self):
        """Input callback."""
        frames = self._fifo.num_available()
        if frames == 0:
            # Return at least a single frame when the buffer is empty.
            return [0]
        return self._fifo.read(frames)

    def _output_callback(self, outdata, frames, time, status):
        """Output callback.

        Read samples from the resampler, optionally modulate them onto a carrier
        frequency, and write them into the output buffer `outdata`.
        """
        samples = self._resampler.read(frames)
        samples = np.pad(samples, (0, frames - len(samples)), mode='constant')
        outdata[:, 0] = self._output_processor.process(
            samples, self._output_samplerate, time=time, status=status)

    def start(self):
        self._outstream.start()

    def stop(self):
        self._outstream.stop()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()
        self._outstream.close()
