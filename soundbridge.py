from __future__ import print_function, division
import numpy as np

import sounddevice as sd
import samplerate as sr

from fifo import FIFO


class OutputProcessor(object):
    """Basic output processor.

    Passes samples through by multiplying with `input_gain` and `output_volume`.
    """

    def __init__(self, input_gain=1.0, output_volume=1.0):
        self._input_gain = input_gain
        self._output_volume = output_volume

    @property
    def input_gain(self):
        """Input gain."""
        return self._input_gain

    @input_gain.setter
    def input_gain(self, gain):
        self._input_gain = gain

    @property
    def output_volume(self):
        """Output volume."""
        return self._output_volume

    @output_volume.setter
    def output_volume(self, volume):
        self._output_volume = volume

    def process(self, samples, _samplerate, **_kwargs):
        """Process output samples."""
        return self.output_volume * self.input_gain * samples


class FMOutputProcessor(OutputProcessor):
    """Frequency modulating output processor.

    Modulates samples onto a carrier frequency.
    """
    def __init__(self, input_gain=1.0, output_volume=1.0, carrier_frequency=500):
        super(FMOutputProcessor, self).__init__(input_gain, output_volume)
        self._carrier_frequency = carrier_frequency
        self._last_fmphase = 0

    @property
    def carrier_frequency(self):
        """Carrier frequency (Hz)."""
        return self._carrier_frequency

    @carrier_frequency.setter
    def carrier_frequency(self, frequency):
        self._carrier_frequency = frequency

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
        """Output processor."""
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

        Read samples from the resampler, turn them into output samples (via an
        output processor), and write them into the output buffer `outdata`.
        """
        samples = self._resampler.read(frames)
        samples = np.pad(samples, (0, frames - len(samples)), mode='constant')
        outdata[:, 0] = self._output_processor.process(
            samples, self._output_samplerate, time=time, status=status)

    def start(self):
        """Start output stream."""
        self._outstream.start()

    def stop(self):
        """Stop output stream."""
        self._outstream.stop()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()
        self._outstream.close()
