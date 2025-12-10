# Skalen-Mapping und Override-Notation

## Skalen-Mapping
Wenn in der Konfiguration unter `sequences` ein `scale` angegeben ist, werden die Noten automatisch gemäß Mapping aus `config/scales.yaml` mit Vorzeichen (#/b) versehen.

Beispiel `config/scales.yaml`:
```yaml
Gmajor:
  F: '#'
Fminor:
  B: 'b'
  E: 'b'
  A: 'b'
  D: 'b'
```

## Override-Notation
Um das Standard-Vorzeichen aus dem Skalen-Mapping zu überschreiben, kann folgende Notation verwendet werden:
- `F!4` → F4 (kein Vorzeichen, Override)
- `F#4` → F#4 (explizites #)
- `Fb4` → Fb4 (explizites b)

**Beispiel-Konfiguration:**
```yaml
sequences:
  scale: Gmajor
  notes:
    - "F4 G4 A4"    # F wird zu F#4
    - "F!4 G4"      # F! wird zu F4 (Override: kein #)
```

## Testabdeckung
Die Logik ist durch Unit-Tests in `test_scales.py` abgedeckt:
- Standard-Mapping und Override werden getestet (siehe `test_gmajor_default_and_override`, `test_fminor_default_and_override`).

## Beispiel für eigene Skalen
Erweitere `config/scales.yaml` nach Bedarf um weitere Skalen und deren Noten-Mapping.
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
    - `C4:1.5` — explizite Dauer in Beats (z.B. punktierte Viertelnote)
  
  - **Pausen (Rests) in Sequenzen**:
    - `z` — Pause mit Standarddauer (entspricht `unit_length`)
    - `z2` — halbe Pause (doppelte Länge)
    - `z4` — ganze Pause (vierfache Länge)
    - `z/2` — Achtelpause (halbe Länge)
    - `z/4` — Sechzehntelpause (viertel Länge)
    - `z:1.5` — Pause mit expliziter Dauer in Beats
    - `z*2` — Pause mit Multiplikations-Syntax
    - `Z` oder `x` — Alternative Notation für Pausen (äquivalent zu `z`)
    
    **Beispiele mit Pausen**:
    ```yaml
    sequences:
      signature: "4/4"
      unit_length: 1.0
      notes:
        - "C4 D4 E4 z E4 F4 G4 z2"           # Melodie mit Atempausen
        - "G4 z/2 G4 z/2 A4 z/2 B4"         # Rhythmische Phrase mit kurzen Pausen
        - "| C4 D4 | z E4 F4 | z2 |"        # Pausen innerhalb von Takten
        - "C4 z:0.5 D4 z:1.5 E4"            # Explizite Pausenlängen
    ```
  
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
  - `rhythm_vocal`: Rhythmus-Vokalübungen mit einfachen Notenmustern
    - `enabled`: `true` zum Aktivieren (Standard: `false`)
    - `base_note`: Einzelne Note für alle Rhythmusübungen (z.B. `C4`)
    - `num_exercises`: Anzahl unterschiedlicher Rhythmusmuster (Standard: `10`)
    - `max_pattern_length`: Maximale Anzahl Noten pro Muster (Standard: `8`)
    
    **Beispiel**:
    ```yaml
    content:
      intervals:
        enabled: false
      triads:
        enabled: false
      rhythm_vocal:
        enabled: true
        base_note: C4
        num_exercises: 12
        max_pattern_length: 8
    ```
    
    Rhythmus-Vokalübungen fokussieren sich auf Rhythmusmuster mit einer einzelnen Note,
    um Rhythmusgefühl und Stimmkontrolle zu trainieren. Die generierten Muster umfassen:
    - Einfache Muster: Viertelnoten, Achtelnoten, Halbe Noten
    - Komplexe Muster: Punktierte Noten, Synkopen, Sechzehntelnoten
    - Gemischte Rhythmen zur Verbesserung der rhythmischen Vielfalt

- `timing`:
  - `note_duration`: Länge eines einzelnen Tons in Sekunden
  - `pause_between_reps`: Pause zwischen Wiederholungen **innerhalb** eines Blocks in Sekunden
    - Beispiel: Bei A A A B B B ist dies die Pause zwischen den A's und zwischen den B's
  - `pause_between_blocks`: Pause zwischen verschiedenen Übungsblöcken in Sekunden (Default: `2.0`)
    - Beispiel: Bei A A A B B B ist dies die Pause zwischen dem letzten A und dem ersten B
    - Ein Block = alle Wiederholungen derselben Übung (gesteuert durch `repetitions_per_exercise`)
    - Kann auf `0.0` gesetzt werden für keine Pause zwischen Blöcken
  - `intro_beats`, `intro_bpm`: Intro-Metronom-Informationen

- `repetitions_per_exercise`: wie oft jede einzelne (einzigartige) Übung wiederholt werden soll (Typ: integer, Default: `1`)
  - **Verhalten**: Wenn > 1, wird jede generierte Übung so viele Male **direkt hintereinander** wiederholt
  - **Beispiel**: `repetitions_per_exercise: 3` mit 97 einzigartigen Übungen ergibt 97 × 3 = 291 Trainingseinheiten
  - **Priorität**: `repetitions_per_exercise` hat Vorrang vor `exercises_count`
  - **Konsekutive Wiederholungen**: Jede Übung wird vollständig wiederholt, bevor die nächste Übung beginnt
  - **Pausen**: Zwischen Wiederholungen derselben Übung wird `pause_between_reps` verwendet, zwischen verschiedenen Übungen `pause_between_blocks`
  
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

# Note-Chains aus vocal_range

Wenn weder `scale` noch `sequences` in der YAML-Konfiguration angegeben sind, werden zufällige Notenketten (Note-Chains) aus dem Bereich `vocal_range` generiert.

**Konfigurationsbeispiel:**
```yaml
vocal_range:
  lowest_note: A2
  highest_note: C4
max_note_chain_length: 5      # Maximale Länge einer Notenkette (Standard: 5)
max_interval_length: 7        # Maximale Intervallgröße zwischen zwei Noten (in Halbtönen, Standard: 7)
num_note_chains: 20           # Anzahl der generierten Notenketten (Standard: 20)
```

- Es werden zufällige Notenketten von 2 bis `max_note_chain_length` Noten erzeugt.
- Jede Note in einer Kette liegt im Bereich von `lowest_note` bis `highest_note` (inklusive).
- Der Abstand zwischen zwei aufeinanderfolgenden Noten ist durch `max_interval_length` begrenzt.
- Die Richtung der Noten ist beliebig (aufsteigend/absteigend/mischung).
- Die generierten Ketten werden als Übungssequenzen ausgegeben (MIDI/Text).

**Beispielausgabe:**
```
A2 C3 B2 F#3 C4
C4 B3 G#3 A2
...
```

Siehe auch die Unit-Tests in `test_vocal_range_note_chains.py` für Details zur Generierung und Validierung.

## Takt-Markierungen in Verbose-Ausgabe

Bei Verwendung von `--verbose` oder `--dry-run` werden in der Text-Log-Datei automatisch Takt-Markierungen eingefügt, die anzeigen, wo neue Takte beginnen. Dies erleichtert das Verständnis der rhythmischen Struktur der Übungen.

**Format der Takt-Markierungen:**
- `|M1|` - Beginn des ersten Takts
- `|M2|` - Beginn des zweiten Takts
- `|M3|` - Beginn des dritten Takts
- usw.

**Beispiel-Ausgabe:**
```
0001: SEQUENCE  |M1| C4(60):d1.00:t480 D4(62):d1.00:t480 E4(64):d1.00:t480 F4(65):d1.00:t480 |M2| G4(67):d1.00:t480 A4(69):d1.00:t480 B4(71):d1.00:t480 C5(72):d1.00:t480
```

In diesem Beispiel (4/4-Takt):
- Takt 1: C4, D4, E4, F4 (4 Viertelnoten = 4 Schläge)
- Takt 2: G4, A4, B4, C5 (4 Viertelnoten = 4 Schläge)

**Mit Pausen:**
```
0001: SEQUENCE  |M1| REST:d1.00:t480 REST:d1.00:t480 REST:d1.00:t480 C4(60):d1.00:t480 |M2| D4(62):d2.00:t960 E4(64):d2.00:t960
```

Die Takt-Markierungen basieren auf der `signature` in der Sequenz-Konfiguration (z.B. `4/4`, `3/4`, `6/8`).

---

Dateien im Projekt (wichtig):
- `intonation_trainer.py` — Hauptskript
- `config_template.yaml` — Beispielkonfiguration für Skalen-basierte Generierung (kopieren und anpassen)
- `config_sequences_example.yaml` — Beispielkonfiguration für ABC-Notation Sequenzen
- `requirements.txt` — Python-Abhängigkeiten
- `piano/SalamanderGrandPiano.sf2` — optionaler freier SoundFont (wenn vorhanden)

Bei Fragen oder wenn Sie möchten, dass ich die CLI um `--exercises-count` erweitere oder ein Beispiel-`config.yaml` mit `exercises_count` anlege, sagen Sie kurz Bescheid — ich mache das dann schnell.