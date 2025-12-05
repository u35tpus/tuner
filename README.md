# Intonation Trainer

Ein Python-CLI-Tool zur Erzeugung von Skalen-basierten Intervallen und Dreiklängen mit Audioausgabe.

Dieses Repository enthält das Skript `intonation_trainer.py`, eine Beispielkonfiguration `config_template.yaml` und ein Verzeichnis `piano/` mit einem kostenlosen SoundFont (Salamander Grand Piano). Das Skript kann MIDI/Audio über FluidSynth + SoundFont rendern oder — falls nicht verfügbar — ein einfaches, reines-Python WAV-Synthesizer-Fallback verwenden.

**Inhalt**
- **Installation**: Virtualenv, Abhängigkeiten
- **Schnellstart**: Ausführen mit Standard-Konfig
- **Konfigurationsdatei**: Alle relevanten YAML-Keys (inkl. `exercises_count`)
- **CLI-Optionen**: Vollständige Liste + Beispiele
- **Text-Log-Modus**: Dry-run & Wiedergabe aus Text-Log
- **Tipps & Troubleshooting**: fluidsynth / ffmpeg Hinweise

**Installation**
- Empfohlen: Erstelle und aktiviere ein virtuellen Python-Umgebung (zsh):

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

- Optionale Systemabhängigkeiten (für bessere Sound-Ausgabe):
  - `fluidsynth` (für Rendering mit `.sf2` SoundFont)
  - `ffmpeg` (für Konvertierung nach MP3/M4A aus WAV)

macOS-Installation (Homebrew):

```bash
brew install fluidsynth ffmpeg
```

**Schnellstart**
- Kopiere `config_template.yaml` und passe Werte an, oder benutze die Vorlage unverändert.
- Beispielausführung (verwende Standard-Konfig im Projektverzeichnis):

```bash
. .venv/bin/activate
python3 intonation_trainer.py config_template.yaml
```

Das erzeugt standardmäßig eine MP3-Datei nach `output.filename` in der Konfiguration.

**Wichtige Hinweis zu Lautstärke/Normalisierung**
- Die Config enthält `normalize_lufs` als Hinweis — das Skript nimmt einfache Normalisierung vor. Für präzise LUFS-Normalisierung bitte `ffmpeg` oder spezialisierte Tools verwenden.

**Konfigurationsdatei (`config_template.yaml`) — Wichtige Keys**
- `output`:
  - `filename`: Template für Ausgabe (z. B. `Intonation_{scale}_{date}.mp3`)
  - `format`: `mp3` / `wav` / `m4a`
  - `normalize_lufs`: (optional) Ziel-LUFS (Hinweis)

- `vocal_range`:
  - `lowest_note`: z. B. `A2`
  - `highest_note`: z. B. `C4`

- `scale`:
  - `name`, `root`: z. B. `root: F2`
  - `type`: z. B. `natural_minor`, `major`, `dorian`, etc.
  - Alternativ: `notes:` Liste mit konkreten Notennamen (falls du eine benutzerdefinierte Skala willst)

- `content`:
  - `intervals`: Einstellungen für Intervall-Generierung (ascending/descending, max_interval...)
  - `triads`: `enabled`, `include_inversions`, `types` (z. B. `[major, minor, diminished]`)

- `timing`:
  - `note_duration`: Länge eines einzelnen Tons in Sekunden
  - `pause_between_reps`: Pause zwischen Wiederholungen in Sekunden
  - `pause_between_blocks`: Pause zwischen Blöcken in Sekunden
  - `intro_beats`, `intro_bpm`: Intro-Metronom-Informationen

- `repetitions_per_exercise`: wie oft jede einzelne (einzigartige) Übung wiederholt werden soll (Typ: integer, Default: `1`)
  - **Verhalten**: Wenn > 1, wird jede generierte Übung so viele Male **direkt hintereinander** wiederholt
  - **Beispiel**: `repetitions_per_exercise: 3` mit 97 einzigartigen Übungen ergibt 97 × 3 = 291 Trainingseinheiten
  - **Priorität**: `repetitions_per_exercise` hat Vorrang vor `exercises_count`
  - **Konsekutive Wiederholungen**: Jede Übung wird vollständig wiederholt, bevor die nächste Übung beginnt
  
- `random_seed`: ganzzahlig oder `null`

- `max_duration`: maximale Ziel-Sitzungsdauer in Sekunden (Default: `600` = 10 Minuten)
  - Nur angewandt, wenn `repetitions_per_exercise: 1` und `exercises_count: null`

- `exercises_count` (optional)
  - Typ: integer oder `null`
  - Beschreibung: Wenn `repetitions_per_exercise: 1`, bestimmt dies die Anzahl der zu generierenden eindeutigen Übungen
  - Priorität: `repetitions_per_exercise` > `exercises_count` > `max_duration`
  - Wenn `repetitions_per_exercise > 1`: `exercises_count` wird ignoriert

- `sound`:
  - `method`: `soundfont` (Standard)
  - `soundfont_path`: Pfad zur `.sf2` Datei, z. B. `piano/SalamanderGrandPiano.sf2`
  - `velocity`: MIDI-Velocity (0–127)

**CLI-Optionen (vollständig)**
- `python3 intonation_trainer.py config.yaml [OPTIONS]`

- Positionale Argumente:
  - `config`: Pfad zur YAML-Konfigurationsdatei

- Optionen:
  - `--output`, `-o` : Überschreibt den Ausgabedateinamen. Beispiel: `--output my_session.mp3`
  - `--dry-run` : Erzeugt keine Audioausgabe, sondern schreibt stattdessen ein Text-Log der generierten Übungen (human-readable). Praktisch zum Review.
  - `--verbose` : Zusätzlich zur Audioausgabe immer ein Text-Log schreiben.
  - `--text-file` : Expliziter Pfad für das Text-Log (überschreibt Standardname). Wird mit `--dry-run` oder `--verbose` verwendet.

  - `--max-duration` : Maximale Sitzungsdauer in Sekunden (überschreibt `max_duration` in der YAML, falls explizit angegeben). Default: `600`.
  - `--from-text` : Statt die Übungen aus der Config zu generieren, lade sie aus einem zuvor erzeugten Text-Log und rendere daraus die Session.

Wichtig: Es gibt aktuell keine CLI-Flag `--exercises-count`; `exercises_count` wird über die YAML-Konfiguration gesteuert.

**Beispiele**

1) Dry-run: Erzeuge nur Text-Log mit ~3 Minuten Inhalt (über `--max-duration`):

```bash
. .venv/bin/activate
python3 intonation_trainer.py config_template.yaml --dry-run --max-duration 180 --text-file test_3min.txt
```

2) Erzeuge Session basierend auf `exercises_count` in der YAML (zuerst `config_template.yaml` bearbeiten):

```yaml
# in config_template.yaml
exercises_count: 120
```

Dann ausführen:

```bash
. .venv/bin/activate
python3 intonation_trainer.py config_template.yaml
```

3) Rendern aus einem vorhandenen Text-Log (z. B. `test_3min.txt`):

```bash
. .venv/bin/activate
python3 intonation_trainer.py config_template.yaml --from-text test_3min.txt --output from_text_session.mp3
```

4) Expliziter Output-Name & verbose Log

```bash
. .venv/bin/activate
python3 intonation_trainer.py config_template.yaml --output my_session --verbose
```

(Gibt `my_session.mp3` aus und schreibt `my_session.txt` mit den einzelnen Übungen.)

**Text-Log Format**
- Das Text-Log ist für Menschen lesbar und enthält Einträge wie:

```
0001: INTERVAL  C#3 (49) -> A#2 (46)
0002: TRIAD     A3(57) C#4(61) E4(64)
```

- Du kannst solche Logs wieder mit `--from-text` laden und als Audio rendern.

**Troubleshooting & Hinweise**
- Wenn `fluidsynth` und ein SoundFont (`.sf2`) vorhanden sind, nutzt das Skript `fluidsynth` zur MIDI-zu-WAV-Konvertierung. Pfad zu `.sf2` wird von `sound.soundfont_path` in der YAML gesteuert.
- Falls `fluidsynth` nicht vorhanden ist oder das Rendering fehlschlägt, fällt das Skript auf einen eingebauten WAV-Synth zurück (mehrere reine Sinustöne, mono).
- Für MP3/M4A-Konvertierung aus WAV installiertes `ffmpeg` ist empfehlenswert. Ohne `ffmpeg` wird nur WAV erzeugt.
- `pydub` ist optional; bei manchen Python-Builds fehlen native Extensions (z. B. `audioop`) — dann verwendet das Skript die reine-Numpy/WAV-Pipeline.

**Weiteres / Entwicklung**
- Mögliche Erweiterungen:
  - CLI-Flag `--exercises-count` (derzeit nur YAML)
  - Stereo-Ausgabe / bessere Instrumentenauswahl aus SoundFont
  - LUFS-Normalisierung via spezialisierter Bibliothek

---

Dateien im Projekt (wichtig):
- `intonation_trainer.py` — Hauptskript
- `config_template.yaml` — Beispielkonfiguration (kopieren und anpassen)
- `requirements.txt` — Python-Abhängigkeiten
- `piano/SalamanderGrandPiano.sf2` — optionaler freier SoundFont (wenn vorhanden)

Bei Fragen oder wenn Sie möchten, dass ich die CLI um `--exercises-count` erweitere oder ein Beispiel-`config.yaml` mit `exercises_count` anlege, sagen Sie kurz Bescheid — ich mache das dann schnell.