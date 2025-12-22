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
      validate_time_signature: true  # Optional: Taktart-Validierung aktivieren (Default: true wenn signature angegeben)
      transpose: 2              # Optional: Transponierung in Halbtönen (positiv = höher, negativ = tiefer, 0 = keine Transponierung)
      notes:
        - "|C4 D42 E4 F4|"      # C, D (doppelt), E, F Vierteln in 4/4
        - "|G3 C4 A4/2 D3|"     # G, C Vierteln; A (halbe); D Vierteln
        - "|G#2 C4 E3|"         # Alle Vierteln
    ```
  
  - **Transponierung**:
    - Mit dem Parameter `transpose` können Sequenzen um beliebig viele Halbtöne transponiert werden
    - `transpose: 2` — Transponiert alle Noten um 2 Halbtöne nach oben (z.B. C4 → D4, E4 → F#4)
    - `transpose: -3` — Transponiert alle Noten um 3 Halbtöne nach unten (z.B. C4 → A3)
    - `transpose: 12` — Transponiert um eine Oktave nach oben
    - `transpose: -12` — Transponiert um eine Oktave nach unten
    - `transpose: 0` oder nicht angegeben — Keine Transponierung (Standard)
    - Pausen bleiben bei der Transponierung unverändert
    - Noten werden auf den gültigen MIDI-Bereich (0-127) begrenzt
    
    **Beispiel-Konfiguration mit Transponierung:**
    ```yaml
    sequences:
      signature: "4/4"
      unit_length: 1.0
      scale: Gminor
      transpose: -2  # Alle Noten um 2 Halbtöne nach unten transponieren
      notes:
        - "| C4 D4 E4 F4 |"  # Wird zu Bb3 C4 D4 Eb4
        - "| G4 A4 B4 C5 |"  # Wird zu F4 G4 A4 Bb4
    ```
  
  - **Notenlängen-Syntax**:
    - `C4` — Viertelnote (standard, multipliziert mit `unit_length`)
    - `C42` oder `C4*2` — doppelte Länge (Halbnote bei unit_length=1.0)
    - `C4/2` — halbe Länge (Achtelnote bei unit_length=1.0)
    - `C4/4` — Viertel der Länge (Sechzehntelnote)
    - `C4:1.5` — explizite Dauer in Beats (z.B. punktierte Viertelnote)

  - **Legato / Bindebogen (Tie) in Sequenzen**:
    - Ein `-` am Ende einer Note bindet zur **nächsten Note derselben Tonhöhe**.
    - Die Fortsetzungs-Note wird **nicht erneut angeschlagen**, sondern verlängert die vorherige Note (auch über `|` hinweg).
    - Die Dauer wird pro Token angegeben und addiert sich (z.B. `C4- C4` ergibt 2 Beats bei `unit_length: 1.0`).
    - Pausen (`z`, `Z`, `x`) können nicht gebunden werden.

    **Beispiele**:
    ```yaml
    sequences:
      signature: "4/4"
      unit_length: 1.0
      notes:
        - "| C4- C4 D4 E4 |"      # C4 wird insgesamt 2 Beats gehalten
        - "| C4- | C4 | D4 |"      # Tie über Taktgrenze
        - "| C4:1.0- C4:0.5 D4 |"  # Gesamtdauer C4 = 1.5 Beats
    ```
  
  - **Taktart-Validierung**:
    - Wenn `signature` (z.B. `"4/4"`, `"3/4"`, `"6/8"`) angegeben ist, kann optional die Validierung aktiviert werden
    - `validate_time_signature: true` (Standard wenn `signature` vorhanden) prüft, ob die Summe der Notenlängen pro Takt mit der Taktart übereinstimmt
    - `validate_time_signature: false` deaktiviert die Validierung
    - **Inline Taktwechsel**: `|3 C4 D4 E4|` wechselt zu 3/4 für diesen Takt (die Zahl nach `|` gibt die Anzahl Schläge an)
    - **Unvollständige Takte**: Takte ohne öffnende oder schließende `|` am Anfang/Ende einer Sequenz werden als Auftakt/Abgesang erkannt und nicht validiert
    - Beispiel: `C4 D4 | E4 F4 G4 A4 |` — erster Takt (C4 D4) ist unvollständig (Auftakt), zweiter Takt wird validiert
    - Bei `combine_sequences_to_one: true` wird auch die kombinierte Sequenz validiert
  
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

  - **Beispiel-Konfiguration**:
    - Eine komplette Beispiel-Konfig für Legato/Ties findest du in [config_legato_example.yaml](config_legato_example.yaml).
  
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

# Vocal-Range Übungen (ohne `scale` / `sequences`)

Wenn weder `scale` noch `sequences` in der YAML-Konfiguration angegeben sind, kann der Generator Übungen direkt aus `vocal_range` erzeugen. Das Verhalten wird über `vocal_range.mode` gesteuert.

## Modus: zufällige Note-Chains (Default)

**Konfigurationsbeispiel:**
```yaml
vocal_range:
  lowest_note: A2
  highest_note: C4
  mode: note_chains
max_note_chain_length: 5      # Maximale Länge einer Notenkette (Standard: 5)
max_interval_length: 7        # Maximale Intervallgröße zwischen zwei Noten (in Halbtönen, Standard: 7)
num_note_chains: 20           # Anzahl der generierten Notenketten (Standard: 20)
```

- Es werden zufällige Notenketten von 2 bis `max_note_chain_length` Noten erzeugt.
- Jede Note in einer Kette liegt im Bereich von `lowest_note` bis `highest_note` (inklusive).
- Der Abstand zwischen zwei aufeinanderfolgenden Noten ist durch `max_interval_length` begrenzt.
- Die Richtung der Noten ist beliebig (aufsteigend/absteigend/mischung).

Siehe auch die Unit-Tests in `test/test_vocal_range_note_chains.py` für Details zur Generierung und Validierung.

## Modus: Halbton-Schritte mit Dur-Dreiklang + 1-2-1

Dieser Modus erzeugt eine deterministische Übung, die den Stimmumfang in Halbton-Schritten nach oben durchläuft. Pro Grundton (startend bei `lowest_note`) werden:

1. ein **Dur-Dreiklang als Akkord** (3 Noten gleichzeitig) gespielt: 1-3-5 der jeweiligen Dur-Tonleiter
2. danach eine kurze Folge gespielt: **1-2-1** der jeweiligen Dur-Tonleiter
3. der Grundton um einen Halbton erhöht und wiederholt

Der Generator stoppt, sobald die dafür benötigten Töne den `highest_note` überschreiten würden.

**Konfigurationsbeispiel:**
```yaml
vocal_range:
  lowest_note: A2
  highest_note: C4
  mode: scale_step_triads

# Wiederholt jeden Halbton-Schritt (CHORD + 1-2-1) n-mal
repetitions_per_exercise: 5
```

In der Verbose-Textausgabe erscheinen Akkorde als `CHORD`-Zeilen.

Beispiel-Datei im Repo:
- tracks/vocal_range_example/scale_step_triads_A2_F4.yaml

## Modus: Halbton-Schritte mit Dur-Dreiklang + 1-3-5-3-1

Dieser Modus ist ähnlich wie `scale_step_triads`, spielt aber nach dem Akkord ein Arpeggio-Muster **1-3-5-3-1** (der jeweiligen Dur-Tonleiter des aktuellen Grundtons).

**Konfigurationsbeispiel:**
```yaml
vocal_range:
  lowest_note: A2
  highest_note: F4
  mode: scale_step_triads_13531

# Wiederholt jeden Halbton-Schritt (CHORD + 1-3-5-3-1) n-mal
repetitions_per_exercise: 5
```

Beispiel-Datei im Repo:
- tracks/vocal_range_example/scale_step_triads_13531_A2_F4.yaml

## Modus: Halbton-Schritte mit Moll-Dreiklang + 1-3-5-3-1

Dieser Modus erzeugt pro Halbton-Schritt einen **Moll-Dreiklang** (gleichzeitig) und danach ein Arpeggio-Muster **1-3-5-3-1**.

Wichtig: Die Skala wird als `natural_minor` (aeolian) vom aktuellen Grundton interpretiert.

**Konfigurationsbeispiel:**
```yaml
vocal_range:
  lowest_note: A2
  highest_note: F4
  mode: scale_step_minor_triads_13531

# Wiederholt jeden Halbton-Schritt (CHORD + 1-3-5-3-1) n-mal
repetitions_per_exercise: 5
```

Beispiel-Datei im Repo:
- tracks/vocal_range_example/scale_step_minor_triads_13531_A2_F4.yaml

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