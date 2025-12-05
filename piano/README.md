# Piano samples

This folder is intended to contain a free Grand Piano SoundFont (SF2) or a small set
of pre-rendered WAV samples. The default `config_template.yaml` points to
`piano/SalamanderGrandPiano.sf2`.

Recommended free SoundFont mirrors (you should verify the source before downloading):

- GitHub mirror (example):
  ```bash
  curl -L -o piano/SalamanderGrandPiano.sf2 \
    https://github.com/uriel1998/SalamanderGrandPiano/raw/master/SalamanderGrandPiano-v3.0.sf2
  ```

If you prefer not to use FluidSynth+SF2, the program will fall back to a simple
sine-based synth to allow quick testing. For best results install `fluidsynth` and
download a high-quality SF2 file (Salamander Grand Piano is a common choice).
