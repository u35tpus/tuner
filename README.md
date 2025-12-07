# Intonation Trainer

[![Run Tests](https://github.com/u35tpus/tuner/actions/workflows/tests.yml/badge.svg)](https://github.com/u35tpus/tuner/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/u35tpus/tuner/branch/main/graph/badge.svg)](https://codecov.io/gh/u35tpus/tuner)

Ein Python-CLI-Tool zur Erzeugung von Skalen-basierten Intervallen und Dreiklängen mit Audioausgabe.

Dieses Repository enthält das Skript `intonation_trainer.py`, eine Beispielkonfiguration `config_template.yaml` und ein Verzeichnis `piano/` mit einem kostenlosen SoundFont (Salamander Grand Piano). Das Skript erzeugt MIDI-Dateien (`.mid`) für Trainingsübungen mit Intervallen, Dreiklängen und benutzerdefinierten Notensequenzen.

**Inhalt**
- **Installation**: Virtualenv, Abhängigkeiten
- **Schnellstart**: Ausführen mit Standard-Konfig oder mit ABC-Sequenzen
- **Konfigurationsdatei**: Alle relevanten YAML-Keys (inkl. `sequences`, `exercises_count`)
- **ABC-Notation**: Format für Notatensequenzen mit Taktstrichsymbolen
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

- Externe Audio-Tools sind nicht erforderlich: Das Skript schreibt standardmäßig eine MIDI-Datei (`.mid`).
  - Hinweise zu `fluidsynth` / `ffmpeg` aus älteren Versionen entfernt (Audio-Rendering wurde entfernt).

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

Das erzeugt standardmäßig eine MIDI-Datei nach `output.filename` in der Konfiguration (z. B. `Intonation_session_20251206_013323.mid`).

**Wichtige Hinweis zu Lautstärke/Normalisierung**
- Die Config enthält `normalize_lufs` als Hinweis — das Skript nimmt einfache Normalisierung vor. Für präzise LUFS-Normalisierung bitte `ffmpeg` oder spezialisierte Tools verwenden.

**Konfigurationsdatei (`config_template.yaml`) — Wichtige Keys**
- `output`:
  - `filename`: Template für Ausgabe (z. B. `Intonation_{scale}_{date}.mid`)
  - `format`: (wird aktuell ignoriert — das Tool schreibt MIDI)
  - `normalize_lufs`: (optional) Ziel-LUFS (Hinweis)

- `vocal_range`:
  - `lowest_note`: z. B. `A2`
  - `highest_note`: z. B. `C4`

- `sequences` (optional):
  - Alternativ zu `scale` / `content`: Definiere explizite Note-Sequenzen mit optionalen Notenlängen
  - **Strukturiertes Format** (empfohlen, mit Notenlängen):
    ```yaml
    sequences:
      signature: "4/4"          # Taktart (nur zur Information)
      unit_length: 1.0          # Basis-Notenlänge (1.0 = Viertelnote, 0.5 = Halbnote, etc.)
      notes:
        - "|C4 D42 E4 F4|"      # C, D (doppelt), E, F Vierteln in 4/4
        - "|G3 C4 A4/2 D3|"     # G, C Vierteln; A (halbe); D Vierteln
        - "|G#2 C4 E3|"         # Alle Vierteln
    ```
  - **Notenlängen-Syntax**:
    - `C4` — Viertelnote (standard, multipliziert mit `unit_length`)
    - `C42` oder `C4*2` — doppelte Länge (Halbnote bei unit_length=1.0)
    - `C4/2` — halbe Länge (Achtelnote bei unit_length=1.0)
    - `C4/4` — Viertel der Länge (Sechzehntelnote)
  
  - **Einfaches Format** (komma-getrennt, rückwärts-kompatibel, ohne Notenlängen):
    ```yaml
    sequences:
      - "D#3, A#2, C4, C4"     # Komma-getrennte Notennamen
      - "G3, C4, A4, D3"       # Alternative Format
    ```
  
  - **Alte ABC-Notation** (einfache Liste, ohne Taktart/unit_length):
    ```yaml
    sequences:
      - "|D#3 A#2 C4| C4 |"    # Pipe (|) markiert Taktstrich, Noten raumgetrennt
      - "|G3 C4| A4 D3 |"     # Mehrere Takte in einer Sequenz
    ```
  
  - **Priorität**: Wenn `sequences` definiert, werden `scale` und `content` ignoriert
  - **Keine `vocal_range` nötig**: Sequenzen spezifizieren Noten explizit

- `scale` (optional, wird ignoriert wenn `sequences` definiert):
  - `name`, `root`: z. B. `root: F2`
  - `type`: z. B. `natural_minor`, `major`, `dorian`, etc.
  - Alternativ: `notes:` Liste mit konkreten Notennamen (falls du eine benutzerdefinierte Skala willst)

- `content` (optional, wird ignoriert wenn `sequences` definiert):
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
  - `--output`, `-o` : Überschreibt den Ausgabedateinamen. Beispiel: `--output my_session.mid`
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

2) Erzeuge Session mit expliziten Note-Sequenzen in ABC-Notation mit Notenlängen:

```yaml
# in config_sequences.yaml
sequences:
  signature: "4/4"
  unit_length: 1.0  # Basis-Notenlänge (1.0 = Viertelnote)
  notes:
    - "|C4 D42 E4 F4|"       # C, D (doppelt), E, F
    - "|G3 C4 A4/2 D3|"      # G, C (normal), A (halbe), D (normal)
    - "|G#2 C4 E3|"          # Alle normal
    - "|G3 C4 A4 D3|"        # Alle normal
    - "|G#2 C4 E3 F#3 D#3|"  # Alle normal

repetitions_per_exercise: 3    # Jede Sequenz 3x wiederholt

timing:
  note_duration: 1.0          # Fallback für non-sequence exercises
  pause_between_reps: 1.0

sound:
  method: soundfont
  soundfont_path: "piano/SalamanderGrandPiano.sf2"
```

Dann ausführen:

```bash
. .venv/bin/activate
python3 intonation_trainer.py config_sequences.yaml
```

Das erzeugt Audioausgabe mit den definierten Sequenzen.

3) Erzeuge Session basierend auf `exercises_count` in der YAML (zuerst `config_template.yaml` bearbeiten):

```yaml
# in config_template.yaml
exercises_count: 120
```

Dann ausführen:

```bash
. .venv/bin/activate
python3 intonation_trainer.py config_template.yaml
```

4) Rendern aus einem vorhandenen Text-Log (z. B. `test_3min.txt`):

```bash
. .venv/bin/activate
python3 intonation_trainer.py config_template.yaml --from-text test_3min.txt --output from_text_session.mid
```

5) Expliziter Output-Name & verbose Log

```bash
. .venv/bin/activate
python3 intonation_trainer.py config_template.yaml --output my_session --verbose
```

(Gibt `my_session.mid` aus und schreibt `my_session.txt` mit den einzelnen Übungen.)

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
-- Audio-Rendering/MP3-Konvertierung wurde entfernt; das Tool erzeugt nur MIDI-Dateien. Externe Tools wie `ffmpeg` oder `fluidsynth` sind nicht mehr benötigt.
- `pydub` ist optional; bei manchen Python-Builds fehlen native Extensions (z. B. `audioop`) — dann verwendet das Skript die reine-Numpy/WAV-Pipeline.

## Fehlerbehandlung und Pre-Parsing von ABC-Sequenzen

Vor dem eigentlichen Parsing einer ABC-Sequenz wird jetzt ein Pre-Parsing-Check durchgeführt. Dabei werden alle Noten einzeln geprüft. Falls eine Note nicht geparst werden kann, wird eine klare Fehlermeldung ausgegeben, die die problematische Note und deren Position nennt.

**Beispiel für Pre-Parsing-Fehler:**

```python
result = parse_abc_sequence("C4 D4 X4 F#4")
if result[0] is None:
    print(result[1])
# Ausgabe:
# Pre-parsing error: Note 'X4' at position 3 in sequence 'C4 D4 X4 F#4' did not pass pre-check. Reason: Invalid note format 'X4' (expected format: C4, F#3, or Bb4)
```

**Validierung in Unit-Tests:**

Siehe `test_abc_preparse.py` für Unit-Tests, die sicherstellen, dass fehlerhafte Noten korrekt erkannt und gemeldet werden.

**Hinweis:**
- Die Pre-Parsing-Prüfung erfolgt automatisch bei jedem Aufruf von `parse_abc_sequence()`.
- Die Fehlermeldung enthält immer die Note, die nicht geparst werden konnte, deren Position und den Grund.

---

Dateien im Projekt (wichtig):
- `intonation_trainer.py` — Hauptskript
- `config_template.yaml` — Beispielkonfiguration für Skalen-basierte Generierung (kopieren und anpassen)
- `config_sequences_example.yaml` — Beispielkonfiguration für ABC-Notation Sequenzen
- `requirements.txt` — Python-Abhängigkeiten
- `piano/SalamanderGrandPiano.sf2` — optionaler freier SoundFont (wenn vorhanden)

Bei Fragen oder wenn Sie möchten, dass ich die CLI um `--exercises-count` erweitere oder ein Beispiel-`config.yaml` mit `exercises_count` anlege, sagen Sie kurz Bescheid — ich mache das dann schnell.