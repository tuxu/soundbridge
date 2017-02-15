# zi-soundbridge

Makes tiny signals audible using a [Zurich Instruments](http://zhinst.com)
lock-in amplifier and your sound card 🔈.

This is the perfect tool to hunt for vibrations, or to listen to the frequency
shift during an [AFM](https://en.wikipedia.org/wiki/Atomic-force_microscopy)
session.

## Supported devices

- HF2LI
- not tested, but same API: UHFLI, MFLI

## Installation

    pip install -r requirements.txt

## Usage

    $ python play_zi.py --help
    Usage: play_zi.py [OPTIONS] DEVICE

      Route a signal from a Zurich Instruments lock-in amplifier (DEVICE) to the
      standard sound output.

    Options:
      -r, --samplerate INTEGER        Sample rate (Hz). (default: 3600)
      -d, --demod INTEGER RANGE       Input demodulator. (default: 0)
      -s, --signal [x|y|frequency|phase|auxin0|auxin1]
                                      Input demod signal. (default: x)
      -g, --gain FLOAT                Input gain. (default: 1)
      -v, --volume FLOAT              Output volume. (default: 0.1)
      -p, --pll INTEGER RANGE         PLL to read center frequency. (default: 0)
      -f, --carrier-frequency INTEGER
                                      FM carrier frequency (Hz). (default: 500)
      +m, --modulation / -m, --no-modulation
                                      Perform frequency modulation? (default: no)
      +h, --highpass / -h, --no-highpass
                                      Filter input signal? (default: yes)
      --help                          Show this message and exit.

Modulate frequency shift of demod 0 on `dev###` with a 20x ∆f gain onto a 500 Hz carrier:

    $ python play_zi.py dev### -s frequency +m -h -g 20
    Device: dev###
    Parameters:
      Sample rate (Hz): 3600
      Demodulator: 0
      Signal: frequency
      Input gain: 20.0
      Volume: 0.1
      PLL: 0
      FM carrier frequency (Hz): 500
      Perform frequency modulation? True
      Filter input signal? False
    Playing back...  Ctrl+C to stop.

## License

This project is licensed under the MIT license. See [LICENSE.md](LICENSE.md) for
details.

© 2017 [Tino Wagner](http://www.tinowagner.com/), Nanotechnology Group, ETH Zurich