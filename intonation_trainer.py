def preparse_abc_notes(abc_str, default_length=1.0):
    """Pre-Parsing: Check each note in ABC string before main parsing. Returns error if any note fails."""
    import re
    original_str = abc_str
    # Split by | but keep them
    parts = re.split(r'(\|)', abc_str)
    
    all_tokens = []
    for part in parts:
        part = part.strip()
        if part == '|':
            all_tokens.append('|')
        elif part:
            all_tokens.extend(part.split())
    
    # Filter out inline time signature numbers (number after |)
    note_strs = []
    i = 0
    while i < len(all_tokens):
        token = all_tokens[i]
        if token == '|':
            # Check if next token is a number (inline time signature)
            if i + 1 < len(all_tokens) and all_tokens[i + 1].isdigit():
                i += 2  # Skip both | and the number
                continue
            else:
                i += 1  # Just skip the |
                continue
        note_strs.append(token)
        i += 1
    
    for i, note_str in enumerate(note_strs):
        parsed = parse_abc_note_with_duration(note_str, default_length)
        if parsed is None or (isinstance(parsed, tuple) and len(parsed) == 2 and parsed[0] is None):
            error_msg = parsed[1] if parsed and len(parsed) == 2 else "Unknown error"
            context = " ".join(note_strs[max(0,i-1):min(len(note_strs),i+2)])
            return (None, f"Pre-parsing error: Note '{note_str}' at position {i+1} in sequence '{original_str}' did not pass pre-check. Reason: {error_msg}\nContext: ...{context}...")
    return True
#!/usr/bin/env python3
"""
Intonation Trainer – Scale-Aware Random Interval & Triad Generator (CLI)

Usage:
  python intonation_trainer.py config.yaml
  python intonation_trainer.py config.yaml --output my_session.mp3

This script implements the functionality described in `docs/spec.txt`.

It attempts to render audio via `fluidsynth` + SoundFont if available.
If not available, it falls back to a simple synthesized tone generator (sine waves).

Dependencies: pyyaml, mido, numpy, pydub

See `requirements.txt` for an installable list.
"""
import argparse
import os
import sys
import tempfile
import shutil
import subprocess
import math
import random
from datetime import datetime

try:
    import yaml
except Exception:
    print("Missing dependency 'pyyaml'. Install with: pip install pyyaml")
    raise

# Audio rendering has been removed; this tool produces MIDI files only.


try:
    import mido
    from mido import Message, MidiFile, MidiTrack, bpm2tempo
except Exception:
    print("Missing dependency 'mido'. Install with: pip install mido")
    raise

import numpy as np
import wave


# ------------------------- Utilities ---------------------------------
def print_red(text):
    """Print text in red color using ANSI escape codes."""
    RED = '\033[91m'
    RESET = '\033[0m'
    print(f"{RED}{text}{RESET}")


NOTE_BASE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def note_name_to_midi(name: str) -> int:
    name = name.strip()
    if len(name) < 2:
        raise ValueError(f"Invalid note name: {name}")
    letter = name[0].upper()
    rest = name[1:]
    accidental = 0
    octave_str = ''
    if rest[0] in ('#', 'b', 'B'):
        if rest[0] == '#':
            accidental = 1
        else:
            accidental = -1
        octave_str = rest[1:]
    else:
        octave_str = rest
    octave = int(octave_str)
    semitone = NOTE_BASE[letter] + accidental
    midi = 12 + octave * 12 + semitone
    return midi


def midi_to_freq(midi: int) -> float:
    return 440.0 * (2 ** ((midi - 69) / 12.0))


SCALE_PATTERNS = {
    'major': [2, 2, 1, 2, 2, 2, 1],
    'natural_minor': [2, 1, 2, 2, 1, 2, 2],
    'harmonic_minor': [2, 1, 2, 2, 1, 3, 1],
    'melodic_minor': [2, 1, 2, 2, 2, 2, 1],
    'dorian': [2, 1, 2, 2, 2, 1, 2],
    'phrygian': [1, 2, 2, 2, 1, 2, 2],
    'lydian': [2, 2, 2, 1, 2, 2, 1],
    'mixolydian': [2, 2, 1, 2, 2, 1, 2],
}


def build_scale_notes(root_midi: int, kind: str):
    if kind in SCALE_PATTERNS:
        pattern = SCALE_PATTERNS[kind]
    else:
        raise ValueError(f"Unknown scale type: {kind}")
    notes = [root_midi]
    cur = root_midi
    for step in pattern:
        cur += step
        notes.append(cur)
    return notes[:-1]


def expand_scale_over_range(scale_root_midi: int, scale_type: str, low_m: int, high_m: int):
    base_scale = build_scale_notes(scale_root_midi % 12 + (scale_root_midi // 12) * 12, scale_type)
    pool = []
    for midi in range(low_m, high_m + 1):
        semis = [n % 12 for n in base_scale]
        if (midi % 12) in semis:
            pool.append(midi)
    return sorted(set(pool))


def transpose_notes(notes_with_durations, semitones):
    """Transpose a sequence of notes by a given number of semitones.
    
    Args:
        notes_with_durations: List of (midi_note, duration) tuples or rest markers
        semitones: Number of semitones to transpose (positive = up, negative = down)
    
    Returns:
        List of transposed notes with same structure
    """
    if semitones == 0:
        return notes_with_durations
    
    transposed = []
    for item in notes_with_durations:
        if isinstance(item, tuple) and len(item) >= 2:
            # Check if it's a rest or a special marker (first element is a string)
            if isinstance(item[0], str):
                # Rest ('rest', duration) or other marker: keep unchanged
                transposed.append(item)
            elif isinstance(item[0], (int, float)) and not isinstance(item[0], bool):
                # Regular note (MIDI number): transpose it
                new_midi = int(item[0]) + semitones
                # Clamp to valid MIDI range (0-127)
                new_midi = max(0, min(127, new_midi))
                transposed.append((new_midi, item[1]))
            else:
                # Other types: keep unchanged
                transposed.append(item)
        else:
            # Other types: keep unchanged
            transposed.append(item)
    
    return transposed


def parse_yaml(path: str) -> dict:
    with open(path, 'r', encoding='utf8') as f:
        return yaml.safe_load(f)


def parse_abc_note_with_duration(note_str, default_length=1.0):
    """Parse ABC note string with optional duration suffix.
    
    Examples:
      "C4" -> (60, 1.0)  [quarter note at default length]
      "C4/2" -> (60, 0.5)  [eighth note, half the length]
      "C4*2" or "C42" -> (60, 2.0)  [half note, double the length]
      "G#3" or "G3#" -> (56, 1.0)
      "C4:1.5" -> (60, 1.5)  [explicit duration]
      "z2" -> ('rest', 2.0)  [rest with duration 2]
    
    Args:
        note_str: String like "C4", "C42", "C4/2", "G#3*2", "z2"
        default_length: Base unit length in beats (typically 1.0 for quarter note)
    
    Returns:
        Tuple (midi_number, duration_in_beats) or ('rest', duration) for rests
        or tuple (None, error_message) if parsing fails
    """
    import re
    note_str = note_str.strip()
    # Erlaube ! als Override für kein Vorzeichen
    if '!' in note_str:
        note_str = note_str.replace('!', '')

    if not note_str:
        return (None, "Empty note string")

    # Check for rest notation (z, Z, or x)
    rest_match = re.match(r'^([zZx])([\d.:/*]*)$', note_str)
    if rest_match:
        rest_symbol = rest_match.group(1)
        length_part = rest_match.group(2)
        duration = default_length
        if length_part:
            try:
                duration = _parse_duration_modifier(length_part, default_length)
            except ValueError as e:
                return (None, f"Invalid duration '{length_part}' for rest '{rest_symbol}': {e}")
        return ('rest', duration)

    # Try to parse as note: letter + optional accidental (before or after octave) + octave + optional duration
    # Support patterns: C#4, C4#, Db4, D4b, C4:1.5, C42, C4/2, C4*2
    match = re.match(r'^([A-G])([#b]?)(\d)([#b]?)([\d.:/*]*)$', note_str, re.IGNORECASE)
    if not match:
        return (None, f"Invalid note format '{note_str}'. Expected format: <Letter>[#/b]<Octave>[duration], e.g., 'C4', 'F#3', 'G4:1.5', 'A#42', 'Bb4/2'")

    letter = match.group(1).upper()
    accidental_before = match.group(2)
    octave = match.group(3)
    accidental_after = match.group(4)
    length_part = match.group(5)

    # Combine accidentals (prefer one before octave, but accept after)
    accidental = accidental_before or accidental_after
    if accidental_before and accidental_after:
        return (None, f"Conflicting accidentals in '{note_str}': both '{accidental_before}' (before octave) and '{accidental_after}' (after octave) specified")

    note_name_part = letter + accidental + octave

    try:
        midi = note_name_to_midi(note_name_part)
    except Exception as e:
        return (None, f"Could not convert '{note_name_part}' to MIDI: {e}")

    # Parse duration modifier
    duration = default_length
    if length_part:
        try:
            duration = _parse_duration_modifier(length_part, default_length)
        except ValueError as e:
            return (None, f"Invalid duration '{length_part}' for note '{note_name_part}': {e}")

    return (midi, duration)


def _parse_duration_modifier(length_str, default_length):
    """Parse duration modifier string and return duration in beats.
    
    Supports:
      - Direct multiplier: "2" means 2x length
      - Division: "/2" means half length
      - Multiplication: "*2" means 2x length
      - Explicit duration: ":1.5" means 1.5 beats
    
    Raises ValueError if parsing fails.
    """
    if not length_str:
        return default_length
    
    if length_str.startswith(':'):
        # Explicit duration: :1.5
        try:
            return float(length_str[1:])
        except ValueError:
            raise ValueError(f"Cannot parse explicit duration '{length_str[1:]}' as number")
    elif length_str.startswith('/'):
        # Division: /2 means half duration
        try:
            divisor = float(length_str[1:])
            if divisor == 0:
                raise ValueError("Cannot divide by zero")
            return default_length / divisor
        except ValueError as e:
            raise ValueError(f"Cannot parse divisor '{length_str[1:]}': {e}")
    elif length_str.startswith('*'):
        # Multiplication: *2 means double duration
        try:
            multiplier = float(length_str[1:])
            return default_length * multiplier
        except ValueError:
            raise ValueError(f"Cannot parse multiplier '{length_str[1:]}' as number")
    else:
        # Direct multiplier: "2" means 2x length (ABC standard notation)
        try:
            multiplier = float(length_str)
            return default_length * multiplier
        except ValueError:
            raise ValueError(f"Cannot parse '{length_str}' as number")


def validate_time_signature(notes_with_durations, time_signature='4/4', sequence_name='sequence'):
    """Validate that note durations in a sequence match the time signature.
    
    Supports:
    - Normal measures with standard time signature
    - Partial measures at start/end (without opening/closing |)
    - Inline time signature changes: |3 C4 D4 E4| for 3/4 measure
    
    Args:
        notes_with_durations: List of (midi/rest, duration) tuples or (special_marker, ...) tuples
        time_signature: Default time signature (e.g., '4/4', '3/4', '6/8')
        sequence_name: Name for error messages
    
    Returns:
        tuple (is_valid, error_message, has_partial_start, has_partial_end)
    """
    if not notes_with_durations:
        return (True, None, False, False)
    
    # Parse default time signature
    try:
        parts = time_signature.split('/')
        default_beats_per_measure = int(parts[0])
    except:
        return (False, f"Invalid time signature format: {time_signature}", False, False)
    
    # Group notes by measures (split by measure markers)
    measures = []
    current_measure = []
    current_beats_per_measure = default_beats_per_measure
    
    # Track whether we started with a measure_start
    first_non_marker_index = -1
    for i, item in enumerate(notes_with_durations):
        if isinstance(item, tuple) and len(item) >= 2 and item[0] not in ['measure_start', 'measure_end']:
            first_non_marker_index = i
            break
    
    first_item_is_note = (first_non_marker_index >= 0 and 
                          (first_non_marker_index == 0 or 
                           all(notes_with_durations[j][0] not in ['measure_start'] 
                               for j in range(first_non_marker_index))))
    
    # Track whether we ended with a measure_end
    last_item_is_measure_end = False
    if notes_with_durations:
        # Find last non-marker item
        for i in range(len(notes_with_durations) - 1, -1, -1):
            item = notes_with_durations[i]
            if isinstance(item, tuple) and len(item) >= 2:
                if item[0] == 'measure_end':
                    last_item_is_measure_end = True
                    break
                elif item[0] not in ['measure_start', 'measure_end']:
                    # Found a note/rest, no measure_end after it
                    break
    
    for i, item in enumerate(notes_with_durations):
        if isinstance(item, tuple) and len(item) >= 2:
            if item[0] == 'measure_start':
                # Measure start marker with optional beat count
                if current_measure:
                    # Determine if previous measure was partial
                    is_first_measure = (len(measures) == 0)
                    is_partial = is_first_measure and first_item_is_note
                    measures.append((current_measure, current_beats_per_measure, is_partial, False))
                    current_measure = []
                current_beats_per_measure = item[1] if len(item) > 1 and isinstance(item[1], (int, float)) else default_beats_per_measure
            elif item[0] == 'measure_end':
                # Measure end marker
                if current_measure:
                    is_first_measure = (len(measures) == 0)
                    is_partial_start = is_first_measure and first_item_is_note
                    measures.append((current_measure, current_beats_per_measure, is_partial_start, False))
                    current_measure = []
                    current_beats_per_measure = default_beats_per_measure
            else:
                # Regular note or rest
                current_measure.append(item)
    
    # Add final measure if any notes remain
    if current_measure:
        is_first_measure = (len(measures) == 0)
        is_partial_start = is_first_measure and first_item_is_note
        is_partial_end = not last_item_is_measure_end
        measures.append((current_measure, current_beats_per_measure, is_partial_start, is_partial_end))
    
    # If no measure markers at all, treat as single partial measure
    if not measures and notes_with_durations:
        # All notes, no markers
        notes_only = [n for n in notes_with_durations if not (isinstance(n, tuple) and n[0] in ['measure_start', 'measure_end'])]
        measures = [(notes_only, default_beats_per_measure, True, True)]
    
    has_partial_start = any(m[2] for m in measures)
    has_partial_end = any(m[3] for m in measures)
    
    # Validate each complete measure (skip partial measures)
    errors = []
    for i, (notes, expected_beats, is_partial_start, is_partial_end) in enumerate(measures):
        # Skip partial measures
        if is_partial_start or is_partial_end:
            continue  # Don't validate partial measures
        
        # Calculate total duration
        total_beats = sum(note[1] for note in notes if len(note) >= 2)
        
        # Allow small floating point errors
        if abs(total_beats - expected_beats) > 0.01:
            errors.append(f"Measure {i+1} has {total_beats} beats but should have {expected_beats} beats (time signature)")
    
    if errors:
        return (False, f"Time signature validation failed for {sequence_name}:\n  " + "\n  ".join(errors), has_partial_start, has_partial_end)
    
    return (True, None, has_partial_start, has_partial_end)


def parse_abc_sequence(abc_str, default_length=1.0, scale_name=None, include_markers=False):
    """Parse ABC notation sequence with durations into list of (midi, duration) tuples.
    
    ABC format: |D#3 A#2 C4| C4 |  or  |C4 D42 E4/2 F4|
    Pipes (|) mark bar lines and are ignored (but can be tracked for validation).
    Notes are space-separated within bars.
    Default length (L) can be specified (e.g., 1.0 = quarter note).
    Supports rests: z, Z, or x with optional duration.
    Supports inline time signature: |3 C4 D4 E4| for 3/4 measure
    
    Args:
        abc_str: ABC notation string (e.g., "|C4 D42 E4|" or "z2 | B3 | E4:1.5")
        default_length: Unit length in beats (default 1.0 for quarter note)
        scale_name: Optional scale name for automatic accidentals (e.g., 'Gmajor', 'Fminor')
        include_markers: If True, include measure_start and measure_end markers in output
    
    Returns:
        List of (midi_number, duration) tuples (or ('rest', duration) for rests)
        Optionally includes ('measure_start', beats) and ('measure_end', None) markers
        or tuple (None, error_message) if parsing fails
    """
    # Pre-parsing check
    precheck = preparse_abc_notes(abc_str, default_length)
    if precheck is not True:
        return precheck
    original_str = abc_str
    
    # Parse with measure tracking
    # Split by | but keep track of them
    import re
    # Split on | and keep the bars and content between them
    parts = re.split(r'(\|)', abc_str)
    
    tokens = []
    for part in parts:
        part = part.strip()
        if part == '|':
            tokens.append('|')
        elif part:
            # Split into individual note/rest tokens
            for token in part.split():
                if token.strip():
                    tokens.append(token.strip())
    
    if not tokens or (len(tokens) == 1 and tokens[0] == '|'):
        return (None, f"No notes found in ABC sequence '{original_str}'")

    # Skalen-Mapping laden, falls scale angegeben
    scale_map = None
    if scale_name:
        try:
            scales_cfg = parse_yaml('config/scales.yaml')
            scale_map = scales_cfg.get(scale_name, {})
        except Exception:
            scale_map = None

    notes_with_durations = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        
        if token == '|':
            # Check if next token is a number (inline time signature)
            if i + 1 < len(tokens) and tokens[i + 1].isdigit():
                # Inline time signature: |3 means 3/4 measure
                beats_count = int(tokens[i + 1])
                notes_with_durations.append(('measure_start', beats_count))
                i += 2  # Skip both | and the number
            else:
                # Regular measure marker
                # Determine if it's start or end based on context
                if not notes_with_durations or (notes_with_durations and notes_with_durations[-1][0] in ['measure_start', 'measure_end']):
                    notes_with_durations.append(('measure_start', None))
                else:
                    notes_with_durations.append(('measure_end', None))
                i += 1
            continue
        
        note_str = token
        # Prüfe auf Override-Notation (!, #, b)
        override = None
        note_base = note_str
        if '!' in note_str:
            override = '!'
            note_base = note_str.replace('!', '')
        elif '#' in note_str:
            override = '#'
        elif 'b' in note_str:
            override = 'b'

        # Extrahiere Buchstaben und Oktave
        m = re.match(r'^([A-G])([#b]?)(\d)([#b]?)([\d.:/*]*)$', note_base)
        if m:
            letter = m.group(1)
            accidental_before = m.group(2)
            octave = m.group(3)
            accidental_after = m.group(4)
            length_part = m.group(5)
            accidental = accidental_before or accidental_after
            # Override-Logik
            if override == '!':
                accidental = ''
            elif override in ['#', 'b']:
                accidental = override
            elif scale_map:
                accidental = scale_map.get(letter, '')
            note_name_part = letter + accidental + octave
            note_str_mod = note_name_part + length_part
            parsed = parse_abc_note_with_duration(note_str_mod, default_length)
        else:
            # Rest oder ungültig
            parsed = parse_abc_note_with_duration(note_str, default_length)
        if parsed is None or (isinstance(parsed, tuple) and len(parsed) == 2 and parsed[0] is None):
            error_msg = parsed[1] if parsed and len(parsed) == 2 else "Unknown error"
            position_info = f"at position '{note_str}'"
            context = " ".join([t for t in tokens if t != '|'])
            return (None, f"Failed to parse ABC sequence '{original_str}' {position_info}.\nError: {error_msg}\nContext: ...{context}...")
        notes_with_durations.append(parsed)
        i += 1
    
    # Filter out measure markers if not requested
    if not include_markers:
        notes_with_durations = [n for n in notes_with_durations if not (isinstance(n, tuple) and len(n) >= 1 and n[0] in ['measure_start', 'measure_end'])]
    
    # Check if we have any actual notes/rests
    actual_notes = [n for n in notes_with_durations if not (isinstance(n, tuple) and len(n) >= 1 and n[0] in ['measure_start', 'measure_end'])]
    if not actual_notes:
        return (None, f"No notes found in ABC sequence '{original_str}'")
    
    return notes_with_durations


def parse_sequences_from_config(sequences_cfg, default_unit_length=1.0):
    """Parse sequences from config and return list of exercises.
    
    Supports multiple formats:
    1. Comma-separated notes (old): "D#3, A#2, C4"
    2. ABC notation (simple): "|D#3 A#2 C4|"
    3. ABC notation with durations: "|C4 D42 E4/2|" (requires default_unit_length)
    4. Full structure with signature, L, notes:
       sequences:
         signature: "4/4"
         unit_length: 0.25  # or L: 1/4
         notes: ["|C4 D42|", "..."]
    
    Returns list of ('sequence', notes_with_durations) exercises.
    notes_with_durations is list of (midi, duration) tuples.
    """
    exercises = []
    if not sequences_cfg:
        return exercises
    
    # Extract scale name if present
    scale_name = None
    if isinstance(sequences_cfg, dict):
        scale_name = sequences_cfg.get('scale', None)
    
    # Handle structured format (dict with signature, L, notes)
    if isinstance(sequences_cfg, dict):
        notes_list = sequences_cfg.get('notes', [])
        unit_length_val = sequences_cfg.get('unit_length', 1.0)
        time_signature = sequences_cfg.get('signature', None)
        # Only validate if signature is present and validation is explicitly enabled
        validate_ts = sequences_cfg.get('validate_time_signature', False) if time_signature is None else sequences_cfg.get('validate_time_signature', True)
        combine_sequences = sequences_cfg.get('combine_sequences_to_one', True)
        transpose_semitones = sequences_cfg.get('transpose', 0)  # Number of semitones to transpose
        
        # If no signature specified, use default but don't validate
        if time_signature is None:
            time_signature = '4/4'
            validate_ts = False
        
        # Also support 'L' format (e.g., "1/4" -> 0.25)
        if 'L' in sequences_cfg:
            L_str = sequences_cfg['L']
            if isinstance(L_str, str) and '/' in L_str:
                parts = L_str.split('/')
                unit_length_val = float(parts[0]) / float(parts[1])
        
        # Parse all sequences first (with markers for validation)
        parsed_sequences = []
        for seq_idx, seq_str in enumerate(notes_list):
            notes_with_dur = parse_abc_sequence(seq_str, unit_length_val, scale_name, include_markers=True)
            if notes_with_dur and not (isinstance(notes_with_dur, tuple) and notes_with_dur[0] is None):
                parsed_sequences.append((seq_str, notes_with_dur))
            else:
                error_msg = notes_with_dur[1] if notes_with_dur and len(notes_with_dur) == 2 else "Unknown error"
                print_red(f'Warning: {error_msg}')
        
        # Validate time signatures if requested
        if validate_ts and time_signature:
            # Validate individual sequences
            for seq_idx, (seq_str, notes_with_dur) in enumerate(parsed_sequences):
                is_valid, error_msg, has_partial_start, has_partial_end = validate_time_signature(
                    notes_with_dur, time_signature, f"Sequence {seq_idx + 1}"
                )
                if not is_valid:
                    print_red(f'Time signature validation error in sequence {seq_idx + 1}:\n{error_msg}')
            
            # If combining sequences, validate the combined sequence
            if combine_sequences and len(parsed_sequences) > 1:
                combined_notes = []
                for seq_str, notes_with_dur in parsed_sequences:
                    # Keep measure markers for validation
                    combined_notes.extend(notes_with_dur)
                
                is_valid, error_msg, _, _ = validate_time_signature(
                    combined_notes, time_signature, "Combined sequence"
                )
                if not is_valid:
                    print_red(f'Time signature validation error in combined sequence:\n{error_msg}')
        
        # Add to exercises (without measure markers for MIDI generation)
        for seq_str, notes_with_dur in parsed_sequences:
            # Filter out measure markers
            notes_only = [n for n in notes_with_dur if not (isinstance(n, tuple) and n[0] in ['measure_start', 'measure_end'])]
            # Apply transposition if specified
            if transpose_semitones != 0:
                notes_only = transpose_notes(notes_only, transpose_semitones)
            exercises.append(('sequence', notes_only))
        
        return exercises
    
    # Handle list format (simple strings, backward compatible)
    for seq_str in sequences_cfg:
        # Detect format: if contains pipe (|), treat as ABC; else as comma-separated
        if '|' in seq_str:
            # ABC format (with optional durations)
            notes_with_dur = parse_abc_sequence(seq_str, default_unit_length, scale_name)
            if notes_with_dur and not (isinstance(notes_with_dur, tuple) and notes_with_dur[0] is None):
                exercises.append(('sequence', notes_with_dur))
            else:
                error_msg = notes_with_dur[1] if notes_with_dur and len(notes_with_dur) == 2 else "Unknown error"
                print_red(f'Warning: {error_msg}')
        else:
            # Comma-separated format (backward compatible, no durations)
            note_names = [n.strip() for n in seq_str.split(',')]
            try:
                notes = [(note_name_to_midi(n), default_unit_length) for n in note_names]
                exercises.append(('sequence', notes))
            except Exception as e:
                print(f'Warning: Could not parse sequence "{seq_str}": {e}')
    
    return exercises


# ------------------ Helpers extracted from main for testing -----------------
def midi_to_note_name(midi: int) -> str:
    octave = (midi // 12) - 1
    pc = midi % 12
    names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    name = names[pc]
    return f"{name}{octave}"


def write_text_log(path: str, exercises_list, ticks_per_beat: int = None, scale_name: str = 'session', time_signature: str = '4/4'):
    """Write text log with measure markers based on time signature."""
    with open(path, 'w', encoding='utf8') as f:
        f.write(f"Intonation Trainer Log\n")
        f.write(f"Scale: {scale_name}\n")
        f.write(f"Time Signature: {time_signature}\n")
        f.write(f"Generated: {len(exercises_list)} exercises (with repetitions)\n\n")
        
        # Parse time signature to get beats per measure
        try:
            beats_per_measure = int(time_signature.split('/')[0])
        except:
            beats_per_measure = 4  # Default to 4/4
        
        for i, ex in enumerate(exercises_list, start=1):
            if ex[0] == 'interval':
                a, b = ex[1], ex[2]
                f.write(f"{i:04d}: INTERVAL  {midi_to_note_name(a)} ({a}) -> {midi_to_note_name(b)} ({b})\n")
            elif ex[0] == 'triad':
                notes = ex[1]
                names = ' '.join([f"{midi_to_note_name(n)}({n})" for n in notes])
                f.write(f"{i:04d}: TRIAD     {names}\n")
            elif ex[0] == 'chord':
                notes = ex[1]
                names = ' '.join([f"{midi_to_note_name(n)}({n})" for n in notes])
                f.write(f"{i:04d}: CHORD    {names}\n")
            elif ex[0] == 'rhythm_vocal':
                notes_with_dur = ex[1]
                if ticks_per_beat is None:
                    ticks_per_beat = 480
                parts = []
                cumulative_beats = 0.0
                measure_num = 0  # Start at 0 so first note triggers M1
                for n, d in notes_with_dur:
                    # Check if we're at the start of a new measure
                    current_measure = int(cumulative_beats // beats_per_measure) + 1
                    if current_measure > measure_num:
                        parts.append(f"|M{current_measure}|")
                        measure_num = current_measure
                    
                    name = midi_to_note_name(n)
                    midi_num = int(n)
                    beats = float(d)
                    ticks = int(beats * ticks_per_beat)
                    parts.append(f"{name}({midi_num}):d{beats:.2f}:t{ticks}")
                    cumulative_beats += beats
                names = ' '.join(parts)
                f.write(f"{i:04d}: RHYTHM_VOCAL  {names}\n")
            elif ex[0] == 'sequence':
                notes_with_dur = ex[1]
                if notes_with_dur and isinstance(notes_with_dur[0], tuple):
                    if ticks_per_beat is None:
                        ticks_per_beat = 480
                    parts = []
                    cumulative_beats = 0.0
                    measure_num = 0  # Start at 0 so first note triggers M1
                    for item in notes_with_dur:
                        # Check if we're at the start of a new measure
                        current_measure = int(cumulative_beats // beats_per_measure) + 1
                        if current_measure > measure_num:
                            parts.append(f"|M{current_measure}|")
                            measure_num = current_measure
                        
                        if item[0] == 'rest':
                            # Rest notation
                            beats = float(item[1])
                            ticks = int(beats * ticks_per_beat)
                            parts.append(f"REST:d{beats:.2f}:t{ticks}")
                        else:
                            # Regular note
                            n, d = item
                            name = midi_to_note_name(n)
                            midi_num = int(n)
                            beats = float(d)
                            ticks = int(beats * ticks_per_beat)
                            parts.append(f"{name}({midi_num}):d{beats:.2f}:t{ticks}")
                        cumulative_beats += beats
                    names = ' '.join(parts)
                else:
                    names = ' '.join([f"{midi_to_note_name(n)}({n})" for n in notes_with_dur])
                f.write(f"{i:04d}: SEQUENCE  {names}\n")
            else:
                f.write(f"{i:04d}: UNKNOWN   {ex}\n")
    return path


def parse_text_log(path: str):
    """Parse exercises from a text log file generated by write_text_log."""
    exercises = []
    try:
        with open(path, 'r', encoding='utf8') as f:
            for line in f:
                line = line.strip()
                if not line or ':' not in line:
                    continue
                parts = line.split(':', 1)
                if len(parts) < 2:
                    continue
                content = parts[1].strip()
                if content.startswith('INTERVAL'):
                    rest = content[len('INTERVAL'):].strip()
                    import re
                    matches = re.findall(r'\((\d+)\)', rest)
                    if len(matches) >= 2:
                        a, b = int(matches[0]), int(matches[1])
                        exercises.append(('interval', a, b))
                elif content.startswith('TRIAD'):
                    rest = content[len('TRIAD'):].strip()
                    import re
                    matches = re.findall(r'\((\d+)\)', rest)
                    if len(matches) >= 3:
                        notes = tuple(int(m) for m in matches)
                        exercises.append(('triad', notes))
                elif content.startswith('CHORD'):
                    rest = content[len('CHORD'):].strip()
                    import re
                    matches = re.findall(r'\((\d+)\)', rest)
                    if len(matches) >= 3:
                        notes = tuple(int(m) for m in matches)
                        exercises.append(('chord', notes))
                elif content.startswith('SEQUENCE'):
                    # parse simple sequence names (no durations)
                    rest = content[len('SEQUENCE'):].strip()
                    import re
                    matches = re.findall(r'([A-G][#b]?\d)\((\d+)\)', rest)
                    if matches:
                        notes = [int(m[1]) for m in matches]
                        exercises.append(('sequence', notes))
    except Exception:
        return []
    return exercises


def build_final_list(cfg: dict, args) -> tuple:
    """Construct the final_list of exercises based on cfg and CLI-like args.

    Returns: (final_list, scale_name, out_name, estimated_duration)
    """
    # Get max_duration from config, then override with CLI if provided
    config_max_duration = cfg.get('max_duration', 600)
    if getattr(args, 'max_duration', 600) != 600:
        max_duration_seconds = args.max_duration
    else:
        max_duration_seconds = config_max_duration

    vocal = cfg.get('vocal_range', {})
    lowest = note_name_to_midi(vocal.get('lowest_note', 'A3'))
    highest = note_name_to_midi(vocal.get('highest_note', 'A4'))

    repetitions = cfg.get('repetitions_per_exercise', 10)
    seed = cfg.get('random_seed', None)
    if seed is not None:
        random.seed(seed)

    sequences_cfg = cfg.get('sequences', None)

    scale_name = 'session'

    if getattr(args, 'from_text', None):
        exercises = parse_text_log(args.from_text)
    elif sequences_cfg:
        exercises = parse_sequences_from_config(sequences_cfg)
    else:
        scale_cfg = cfg.get('scale', {})
        # Vocal-range only modes: if neither scale nor sequences are provided.
        if not scale_cfg:
            vocal_mode = (cfg.get('vocal_range', {}) or {}).get('mode', 'note_chains')
            if vocal_mode == 'scale_step_triads':
                exercises = generate_vocal_range_scale_step_triads(
                    lowest,
                    highest,
                    repetitions_per_step=cfg.get('repetitions_per_exercise', 1),
                )
            elif vocal_mode == 'scale_step_triads_13531':
                exercises = generate_vocal_range_scale_step_triads_13531(
                    lowest,
                    highest,
                    repetitions_per_step=cfg.get('repetitions_per_exercise', 1),
                )
            else:
                exercises = generate_vocal_range_note_chains(
                    lowest,
                    highest,
                    max_note_chain_length=cfg.get('max_note_chain_length', 5),
                    max_interval_length=cfg.get('max_interval_length', 7),
                    num_chains=cfg.get('num_note_chains', 20),
                )
            scale_name = 'vocal_range'
        else:
            scale_name = scale_cfg.get('name', 'scale')
        if scale_cfg and 'notes' in scale_cfg and scale_cfg['notes']:
            custom_notes = [note_name_to_midi(n) for n in scale_cfg['notes']]
            pool = [n for n in custom_notes if lowest <= n <= highest]
            scale_single_octave = sorted(set([n % 12 + 12 for n in custom_notes]))[:7]
        elif scale_cfg:
            root = note_name_to_midi(scale_cfg.get('root', 'A3'))
            stype = scale_cfg.get('type', 'natural_minor')
            pool = expand_scale_over_range(root, stype, lowest, highest)
            scale_single_octave = build_scale_notes(root, stype)

        if not scale_cfg:
            # Vocal-range modes already produced a complete exercises list.
            pass
        else:
            content = cfg.get('content', {})
            intervals_cfg = content.get('intervals', {})
            triads_cfg = content.get('triads', {})

            max_interval = 12
            include_m3 = intervals_cfg.get('include_minor_3rd_even_in_major', True)
            ascending = intervals_cfg.get('ascending', True)
            descending = intervals_cfg.get('descending', True)

            exercises = []
            exercises += generate_intervals(pool, ascending=ascending, descending=descending, max_interval=max_interval, include_m3=include_m3)
            if triads_cfg.get('enabled', True):
                tri_types = triads_cfg.get('types', ['major','minor','diminished'])
                triads = generate_triads(
                    scale_single_octave,
                    pool,
                    include_inversions=triads_cfg.get('include_inversions', True),
                    triad_types=tri_types,
                    low=lowest,
                    high=highest,
                )
                exercises += triads

    # Nur mischen, wenn keine sequences verwendet werden (Skalen/Intervalle/Triaden)
    # vocal_range modes that are step-based should be deterministic (no shuffle).
    vocal_mode = (cfg.get('vocal_range', {}) or {}).get('mode', None)
    if not sequences_cfg and vocal_mode not in ('scale_step_triads', 'scale_step_triads_13531'):
        random.shuffle(exercises)
    # timing
    note_duration = cfg.get('timing', {}).get('note_duration', 1.8)
    pause_between_reps = cfg.get('timing', {}).get('pause_between_reps', 1.0)
    time_per_exercise = note_duration + pause_between_reps

    exercises_count_cfg = cfg.get('exercises_count', None)
    repetitions_per_exercise_cfg = cfg.get('repetitions_per_exercise', 1)

    exercises_count = None
    if exercises_count_cfg is not None:
        try:
            exercises_count = int(exercises_count_cfg)
        except Exception:
            exercises_count = None

    actual_reps = 1
    max_unique_exercises = len(exercises) if len(exercises) > 0 else 1

    if repetitions_per_exercise_cfg > 1:
        actual_reps = repetitions_per_exercise_cfg
    elif exercises_count is not None and exercises_count > 0:
        actual_reps = 1
        max_unique_exercises = exercises_count
    else:
        max_total_exercises = int(max_duration_seconds / time_per_exercise)
        if max_total_exercises < 1:
            max_total_exercises = 1
        if max_unique_exercises > 0:
            actual_reps = max(1, max_total_exercises // max_unique_exercises)
        else:
            actual_reps = 1

    final_list = []
    if len(exercises) > 0:
        if getattr(args, 'from_text', None):
            if exercises_count is not None and exercises_count > 0:
                final_list = exercises[:exercises_count]
            else:
                max_count = int(max_duration_seconds / time_per_exercise)
                final_list = exercises[:max(1, max_count)]
        elif sequences_cfg:
            # Blockweise Wiederholung: Jede Sequenz n-mal hintereinander
            final_list = []
            for ex in exercises:
                for _ in range(repetitions_per_exercise_cfg):
                    final_list.append(ex)
        else:
            # Standardverhalten für Skalen/Intervalle/Triaden
            vocal_mode = (cfg.get('vocal_range', {}) or {}).get('mode', None)
            if vocal_mode == 'scale_step_triads':
                for _ in range(actual_reps):
                    for ex in exercises:
                        final_list.append(ex)
            else:
                for ex in exercises:
                    for _ in range(actual_reps):
                        final_list.append(ex)
            if exercises_count is not None and len(final_list) > exercises_count:
                final_list = final_list[:exercises_count]

    estimated_duration = len(final_list) * time_per_exercise

    # determine out_name similar to main
    outcfg = cfg.get('output', {})
    fname_template = outcfg.get('filename', 'Intonation_{scale}_{date}.mp3')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    scale_label = cfg.get('scale', {}).get('name', scale_name)
    out_name = getattr(args, 'output', None) or fname_template.format(scale=scale_label.replace(' ', '_'), date=timestamp)

    return final_list, scale_name, out_name, estimated_duration


def generate_vocal_range_note_chains(
    lowest: int,
    highest: int,
    *,
    max_note_chain_length: int = 5,
    max_interval_length: int = 7,
    num_chains: int = 20,
    rng=None,
):
    """Generate random note-chains within [lowest, highest] (inclusive)."""
    if rng is None:
        rng = random
    pool = list(range(int(lowest), int(highest) + 1))
    exercises = []
    for _ in range(int(num_chains)):
        chain_len = rng.randint(2, int(max_note_chain_length))
        chain = []
        note = rng.choice(pool)
        chain.append(note)
        for _ in range(chain_len - 1):
            candidates = [n for n in pool if abs(n - note) <= int(max_interval_length) and n != note]
            if not candidates:
                break
            note = rng.choice(candidates)
            chain.append(note)
        exercises.append(('sequence', [(n, 1.0) for n in chain]))
    return exercises


def generate_vocal_range_scale_step_triads(lowest: int, highest: int, *, repetitions_per_step: int = 1):
    """Generate a deterministic vocal-range exercise.

    For each root note starting at lowest and moving up by 1 semitone:
      1) play major triad as a chord (3 notes concurrently)
      2) play scale degrees 1, 2, 1 as a sequence (root, second, root)

    Stops when the required notes would exceed highest.
    """
    exercises = []
    low = int(lowest)
    high = int(highest)
    reps = max(1, int(repetitions_per_step))
    for root in range(low, high + 1):
        scale = build_scale_notes(root, 'major')
        second = scale[1]
        third = scale[2]
        fifth = scale[4]
        if second > high or fifth > high:
            break
        for _ in range(reps):
            exercises.append(('chord', (root, third, fifth)))
            exercises.append(('sequence', [root, second, root]))
    return exercises


def generate_vocal_range_scale_step_triads_13531(lowest: int, highest: int, *, repetitions_per_step: int = 1):
    """Generate a deterministic vocal-range exercise using major triad + 1-3-5-3-1.

    For each root note starting at lowest and moving up by 1 semitone:
      1) play major triad as a chord (3 notes concurrently)
      2) play scale degrees 1, 3, 5, 3, 1 as a sequence (root, third, fifth, third, root)

    The whole step is repeated repetitions_per_step times before moving to the next semitone.
    Stops when the required notes would exceed highest.
    """
    exercises = []
    low = int(lowest)
    high = int(highest)
    reps = max(1, int(repetitions_per_step))
    for root in range(low, high + 1):
        scale = build_scale_notes(root, 'major')
        third = scale[2]
        fifth = scale[4]
        if fifth > high:
            break
        for _ in range(reps):
            exercises.append(('chord', (root, third, fifth)))
            exercises.append(('sequence', [root, third, fifth, third, root]))
    return exercises


def append_exercise_to_session_track(
    track,
    ex,
    *,
    velocity: int,
    secs_to_ticks,
    note_dur: float,
    intra_interval_gap: float,
    rest_between: float,
):
    """Append one exercise to a session MIDI track.

    Supported exercise types: interval, triad (sequential), chord (simultaneous), rhythm_vocal, sequence.
    """
    if ex[0] == 'interval':
        a, b = int(ex[1]), int(ex[2])
        track.append(Message('note_on', note=a, velocity=velocity, time=0))
        track.append(Message('note_off', note=a, velocity=0, time=secs_to_ticks(note_dur)))
        track.append(Message('note_on', note=b, velocity=velocity, time=secs_to_ticks(intra_interval_gap)))
        track.append(Message('note_off', note=b, velocity=0, time=secs_to_ticks(note_dur)))
        track.append(mido.MetaMessage('track_name', name='', time=secs_to_ticks(rest_between)))
    elif ex[0] == 'triad':
        notes = [int(n) for n in ex[1]]
        for n in notes:
            track.append(Message('note_on', note=n, velocity=velocity, time=0))
            track.append(Message('note_off', note=n, velocity=0, time=secs_to_ticks(note_dur)))
        track.append(mido.MetaMessage('track_name', name='', time=secs_to_ticks(rest_between)))
    elif ex[0] == 'chord':
        notes = [int(n) for n in ex[1]]
        if notes:
            for n in notes:
                track.append(Message('note_on', note=n, velocity=velocity, time=0))
            track.append(Message('note_off', note=notes[0], velocity=0, time=secs_to_ticks(note_dur)))
            for n in notes[1:]:
                track.append(Message('note_off', note=n, velocity=0, time=0))
        track.append(mido.MetaMessage('track_name', name='', time=secs_to_ticks(rest_between)))
    elif ex[0] == 'rhythm_vocal':
        notes_with_dur = ex[1]
        for midi_note, dur in notes_with_dur:
            midi_note = int(midi_note)
            ticks = secs_to_ticks(dur)
            track.append(Message('note_on', note=midi_note, velocity=velocity, time=0))
            track.append(Message('note_off', note=midi_note, velocity=0, time=ticks))
        track.append(mido.MetaMessage('track_name', name='', time=secs_to_ticks(rest_between)))
    elif ex[0] == 'sequence':
        seq = ex[1]
        if seq and isinstance(seq[0], tuple):
            for midi_note, dur in seq:
                if midi_note == 'rest':
                    ticks = secs_to_ticks(dur)
                    track.append(mido.MetaMessage('track_name', name='', time=ticks))
                else:
                    midi_note = int(midi_note)
                    ticks = secs_to_ticks(dur)
                    track.append(Message('note_on', note=midi_note, velocity=velocity, time=0))
                    track.append(Message('note_off', note=midi_note, velocity=0, time=ticks))
        else:
            notes = [int(n) for n in seq]
            for n in notes:
                track.append(Message('note_on', note=n, velocity=velocity, time=0))
                track.append(Message('note_off', note=n, velocity=0, time=secs_to_ticks(note_dur)))
        track.append(mido.MetaMessage('track_name', name='', time=secs_to_ticks(rest_between)))
    else:
        track.append(mido.MetaMessage('track_name', name='', time=secs_to_ticks(rest_between)))



# ---------------------- Exercise generation ---------------------------

def generate_intervals(pool_notes, ascending=True, descending=True, max_interval=12, include_m3=False):
    intervals = []
    n = len(pool_notes)
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            a = pool_notes[i]
            b = pool_notes[j]
            semis = b - a
            if abs(semis) > max_interval:
                continue
            if semis > 0 and not ascending:
                continue
            if semis < 0 and not descending:
                continue
            intervals.append(('interval', a, b))
    unique = []
    seen = set()
    for it in intervals:
        key = (it[1], it[2])
        if key not in seen:
            seen.add(key)
            unique.append(it)
    return unique


def generate_rhythm_vocal_exercises(base_note, num_exercises=10, max_pattern_length=8):
    """Generate rhythm vocal exercises.
    
    These exercises focus on rhythm patterns using a single note or very simple
    note variations to help practice rhythm and vocal control.
    
    Args:
        base_note: MIDI note number to use as the base pitch
        num_exercises: Number of different rhythm patterns to generate
        max_pattern_length: Maximum number of notes in a rhythm pattern
    
    Returns:
        List of ('rhythm_vocal', notes_with_durations) tuples
    """
    exercises = []
    
    # Common rhythm patterns (in beats)
    rhythm_patterns = [
        # Simple patterns
        [1.0, 1.0, 1.0, 1.0],  # Quarter notes
        [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5],  # Eighth notes
        [2.0, 2.0],  # Half notes
        [1.0, 0.5, 0.5, 1.0, 1.0],  # Mixed
        [0.5, 0.5, 1.0, 0.5, 0.5, 1.0],  # Syncopated
        # More complex patterns
        [1.5, 0.5, 1.0, 1.0],  # Dotted quarter
        [0.5, 1.0, 0.5, 1.0, 1.0],  # Varied
        [0.25, 0.25, 0.5, 1.0, 0.5, 0.5, 1.0],  # Sixteenth notes
        [1.0, 1.0, 0.5, 0.5, 1.0],  # Mixed quarters and eighths
        [2.0, 1.0, 1.0],  # Half and quarters
        [0.5, 0.5, 0.5, 0.5, 1.0, 1.0],  # Building up
        [1.0, 1.0, 1.0, 0.5, 0.5],  # Quarter then eighths
        [0.75, 0.25, 1.0, 1.0, 1.0],  # Triplet feel
        [1.0, 0.5, 0.5, 0.5, 0.5, 1.0],  # Extended pattern
    ]
    
    # Select random patterns
    selected_patterns = random.sample(rhythm_patterns, min(num_exercises, len(rhythm_patterns)))
    
    for pattern in selected_patterns:
        # Limit pattern length
        if len(pattern) > max_pattern_length:
            pattern = pattern[:max_pattern_length]
        
        # Create note sequence with the same base note but varying durations
        notes_with_dur = [(base_note, duration) for duration in pattern]
        exercises.append(('rhythm_vocal', notes_with_dur))
    
    return exercises


def generate_triads(scale_notes_single_octave_midi, pool_notes, include_inversions=True, triad_types=('major','minor','diminished'), low=None, high=None):
    """Generate triads from a pool of notes.

    If `low` and/or `high` are provided, any generated triad (including inversions)
    that contains notes outside the inclusive range [low, high] will be discarded.
    """
    triads = []
    semitone_to_index = {n % 12: i for i, n in enumerate(scale_notes_single_octave_midi)}
    for root in pool_notes:
        root_pc = root % 12
        if root_pc not in semitone_to_index:
            continue
        deg = semitone_to_index[root_pc]
        tri = []
        for offset in (0, 2, 4):
            idx = (deg + offset) % 7
            octave_shift = (deg + offset) // 7
            pitch = (scale_notes_single_octave_midi[idx] - scale_notes_single_octave_midi[0]) + root + octave_shift * 12
            tri.append(pitch)
        a, b, c = tri
        int1 = b - a
        int2 = c - b
        quality = None
        if int1 == 4 and int2 == 3:
            quality = 'major'
        elif int1 == 3 and int2 == 4:
            quality = 'minor'
        elif int1 == 3 and int2 == 3:
            quality = 'diminished'
        else:
            quality = 'other'

        def in_range(notes_tuple):
            if low is None and high is None:
                return True
            for p in notes_tuple:
                if low is not None and p < low:
                    return False
                if high is not None and p > high:
                    return False
            return True

        if quality in triad_types:
            base_tri = tuple(tri)
            if in_range(base_tri):
                triads.append(('triad', base_tri))
            if include_inversions:
                inv1 = tuple([tri[1], tri[2], tri[0] + 12])
                inv2 = tuple([tri[2], tri[0] + 12, tri[1] + 12])
                if in_range(inv1):
                    triads.append(('triad', inv1))
                if in_range(inv2):
                    triads.append(('triad', inv2))

    uniq = []
    seen = set()
    for t in triads:
        if t[1] not in seen:
            seen.add(t[1])
            uniq.append(t)
    return uniq


# ---------------------- Audio rendering -------------------------------

# Audio rendering via external tools removed. MIDI-only output maintained.


def write_midi_for_exercise(events, midi_path, tempo_bpm=120, channel=0):
    mid = MidiFile()
    track = MidiTrack()
    mid.tracks.append(track)
    track.append(mido.MetaMessage('set_tempo', tempo=bpm2tempo(tempo_bpm)))
    ticks_per_beat = mid.ticks_per_beat
    for note, start, dur, vel in events:
        start_ticks = int(start * (ticks_per_beat * tempo_bpm / 60.0))
        duration_ticks = int(dur * (ticks_per_beat * tempo_bpm / 60.0))
        track.append(Message('note_on', note=note, velocity=vel, time=0))
        track.append(Message('note_off', note=note, velocity=0, time=duration_ticks))
    mid.save(midi_path)


def synth_simple_wav(notes, duration, out_wav, sample_rate=44100, velocity=90):
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    data = np.zeros_like(t)
    for n in notes:
        freq = midi_to_freq(int(n))
        tone = 0.6 * np.sin(2 * np.pi * freq * t) * np.exp(-3 * t)
        data += tone
    maxv = np.max(np.abs(data))
    if maxv > 0:
        data = data / maxv * 0.9
    audio = (data * 32767).astype(np.int16)
    with wave.open(out_wav, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio.tobytes())


def make_silence_ms(ms, sr=44100):
    """Return a numpy int16 array of silence for given milliseconds at sample rate sr."""
    n = int(sr * (ms / 1000.0))
    return np.zeros(n, dtype=np.int16)


def normalize_int16(arr):
    """Normalize an array to int16 amplitude range [-32767,32767].

    If `arr` is already int16, scale it so the maximum absolute value becomes 32767.
    If `arr` is float, scale by its max absolute value and convert to int16.
    """
    a = np.asarray(arr)
    if a.size == 0:
        return a.astype(np.int16)
    if a.dtype == np.int16:
        mx = np.max(np.abs(a))
        if mx == 0:
            return a
        scale = 32767.0 / float(mx)
        out = (a.astype(np.float64) * scale).astype(np.int16)
        return out
    else:
        mx = np.max(np.abs(a))
        if mx == 0:
            return a.astype(np.int16)
        scaled = a.astype(np.float64) / mx * 32767.0
        return scaled.astype(np.int16)


def write_wav_mono(path, arr, sr=44100):
    """Write a mono int16 numpy array to a WAV file."""
    a = np.asarray(arr)
    if a.dtype != np.int16:
        a = normalize_int16(a)
    with wave.open(path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(int(sr))
        wf.writeframes(a.tobytes())


def read_wav_mono(path):
    """Read a mono WAV file and return (numpy int16 array, sample_rate)."""
    with wave.open(path, 'rb') as wf:
        channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        sr = wf.getframerate()
        frames = wf.readframes(wf.getnframes())
    if sampwidth != 2:
        raise RuntimeError('Unsupported sample width')
    arr = np.frombuffer(frames, dtype=np.int16)
    if channels > 1:
        # Reduce to mono by taking first channel
        arr = arr[::channels]
    return arr, sr


# ---------------------- Main program ---------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('config')
    parser.add_argument('--output', '-o', help='Output filename (overrides config)')
    parser.add_argument('--dry-run', action='store_true', help='Do not render audio; only write a text log of generated exercises')
    parser.add_argument('--verbose', action='store_true', help='Also write a text log of generated exercises alongside the audio output')
    parser.add_argument('--text-file', help='Explicit path for the text log (overrides default)')
    parser.add_argument('--max-duration', type=int, default=600, help='Maximum session duration in seconds (default 600=10 min)')
    parser.add_argument('--from-text', help='Read exercises from a text log file instead of generating them from config')
    args = parser.parse_args()

    cfg = parse_yaml(args.config)
    outcfg = cfg.get('output', {})
    fname_template = outcfg.get('filename', 'Intonation_{scale}_{date}.mp3')
    fmt = outcfg.get('format', 'mp3')
    normalize_lufs = outcfg.get('normalize_lufs', -16)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    scale_name = cfg.get('scale', {}).get('name', 'scale')
    out_name = args.output or fname_template.format(scale=scale_name.replace(' ', '_'), date=timestamp)

    # Define helper functions early so they can be used throughout
    def midi_to_note_name(midi: int) -> str:
        # Convert MIDI number back to a note name like C4, Db3
        octave = (midi // 12) - 1
        pc = midi % 12
        names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        name = names[pc]
        return f"{name}{octave}"

    def write_text_log(path: str, exercises_list, ticks_per_beat: int = None, time_signature: str = '4/4'):
        # Parse time signature to get beats per measure
        try:
            beats_per_measure = int(time_signature.split('/')[0])
        except:
            beats_per_measure = 4  # Default to 4/4
        
        with open(path, 'w', encoding='utf8') as f:
            f.write(f"Intonation Trainer Log\n")
            f.write(f"Scale: {scale_name}\n")
            f.write(f"Time Signature: {time_signature}\n")
            f.write(f"Generated: {len(exercises_list)} exercises (with repetitions)\n\n")
            for i, ex in enumerate(exercises_list, start=1):
                if ex[0] == 'interval':
                    a, b = ex[1], ex[2]
                    f.write(f"{i:04d}: INTERVAL  {midi_to_note_name(a)} ({a}) -> {midi_to_note_name(b)} ({b})\n")
                elif ex[0] == 'triad':
                    notes = ex[1]
                    names = ' '.join([f"{midi_to_note_name(n)}({n})" for n in notes])
                    f.write(f"{i:04d}: TRIAD     {names}\n")
                elif ex[0] == 'chord':
                    notes = ex[1]
                    names = ' '.join([f"{midi_to_note_name(n)}({n})" for n in notes])
                    f.write(f"{i:04d}: CHORD    {names}\n")
                elif ex[0] == 'sequence':
                    notes_with_dur = ex[1]
                    # Handle both old format (just MIDI numbers) and new format (with durations)
                    if notes_with_dur and isinstance(notes_with_dur[0], tuple):
                        # New format: list of (midi, duration) tuples or ('rest', duration) for rests
                        # Include duration in beats and ticks
                        if ticks_per_beat is None:
                            ticks_per_beat = 480
                        parts = []
                        cumulative_beats = 0.0
                        measure_num = 0  # Start at 0 so first note triggers M1
                        for item in notes_with_dur:
                            # Check if we're at the start of a new measure
                            current_measure = int(cumulative_beats // beats_per_measure) + 1
                            if current_measure > measure_num:
                                parts.append(f"|M{current_measure}|")
                                measure_num = current_measure
                            
                            if item[0] == 'rest':
                                # Rest notation
                                beats = float(item[1])
                                ticks = int(beats * ticks_per_beat)
                                parts.append(f"REST:d{beats:.2f}:t{ticks}")
                                cumulative_beats += beats
                            else:
                                # Regular note
                                n, d = item
                                name = midi_to_note_name(n)
                                midi_num = int(n)
                                beats = float(d)
                                ticks = int(beats * ticks_per_beat)
                                parts.append(f"{name}({midi_num}):d{beats:.2f}:t{ticks}")
                                cumulative_beats += beats
                        names = ' '.join(parts)
                    else:
                        # Old format: just MIDI numbers
                        names = ' '.join([f"{midi_to_note_name(n)}({n})" for n in notes_with_dur])
                    f.write(f"{i:04d}: SEQUENCE  {names}\n")
                else:
                    f.write(f"{i:04d}: UNKNOWN   {ex}\n")
        print(f'Wrote text log to {path}')

    def parse_text_log(path: str):
        """Parse exercises from a text log file generated by write_text_log."""
        exercises = []
        try:
            with open(path, 'r', encoding='utf8') as f:
                for line in f:
                    line = line.strip()
                    if not line or ':' not in line:
                        continue
                    # Format: "0001: INTERVAL  C#3 (49) -> A#2 (46)"
                    #         "0001: TRIAD     A3(57) C#4(61) E4(64)"
                    parts = line.split(':', 1)
                    if len(parts) < 2:
                        continue
                    content = parts[1].strip()
                    if content.startswith('INTERVAL'):
                        # Parse: "INTERVAL  C#3 (49) -> A#2 (46)"
                        rest = content[len('INTERVAL'):].strip()
                        # Extract MIDI numbers in parentheses
                        import re
                        matches = re.findall(r'\((\d+)\)', rest)
                        if len(matches) >= 2:
                            a, b = int(matches[0]), int(matches[1])
                            exercises.append(('interval', a, b))
                    elif content.startswith('TRIAD'):
                        # Parse: "TRIAD     A3(57) C#4(61) E4(64)"
                        rest = content[len('TRIAD'):].strip()
                        import re
                        matches = re.findall(r'\((\d+)\)', rest)
                        if len(matches) >= 3:
                            notes = tuple(int(m) for m in matches)
                            exercises.append(('triad', notes))
                    elif content.startswith('CHORD'):
                        # Parse: "CHORD    A3(57) C#4(61) E4(64)"
                        rest = content[len('CHORD'):].strip()
                        import re
                        matches = re.findall(r'\((\d+)\)', rest)
                        if len(matches) >= 3:
                            notes = tuple(int(m) for m in matches)
                            exercises.append(('chord', notes))
        except Exception as e:
            print(f'Error parsing text log {path}: {e}')
            return []
        return exercises

    # Get max_duration from config, then override with CLI if provided
    config_max_duration = cfg.get('max_duration', 600)
    if args.max_duration != 600:  # CLI was explicitly set
        max_duration_seconds = args.max_duration
    else:
        max_duration_seconds = config_max_duration

    vocal = cfg.get('vocal_range', {})
    lowest = note_name_to_midi(vocal.get('lowest_note', 'A3'))
    highest = note_name_to_midi(vocal.get('highest_note', 'A4'))

    repetitions = cfg.get('repetitions_per_exercise', 10)
    seed = cfg.get('random_seed', None)
    if seed is not None:
        random.seed(seed)

    # Check if sequences are specified in config
    sequences_cfg = cfg.get('sequences', None)
    
    # Set default scale_name that will be used in output filename
    scale_name = 'session'
    
    # Extract time signature for measure markers in text log
    time_signature = '4/4'  # default
    if sequences_cfg and isinstance(sequences_cfg, dict):
        time_signature = sequences_cfg.get('signature', '4/4')
    
    # If --from-text is provided, load exercises from text file instead of generating
    if args.from_text:
        exercises = parse_text_log(args.from_text)
        if not exercises:
            print(f'No exercises loaded from {args.from_text}. Exiting.')
            return
        print(f'Loaded {len(exercises)} exercises from {args.from_text}')
    elif sequences_cfg:
        # Use explicit note sequences if provided
        exercises = parse_sequences_from_config(sequences_cfg)
        if not exercises:
            print('No valid sequences found in config. Exiting.')
            return
        print(f'Loaded {len(exercises)} sequences from config')
        # Feature: combine_sequences_to_one (default true)
        combine_sequences_to_one = True
        if isinstance(sequences_cfg, dict):
            combine_sequences_to_one = sequences_cfg.get('combine_sequences_to_one', True)
    else:
        # Feature: Note-Chains aus vocal_range, wenn weder scale noch sequences im Config stehen
        scale_cfg = cfg.get('scale', {})
        sequences_cfg = cfg.get('sequences', None)
        if not scale_cfg and not sequences_cfg:
            vocal = cfg.get('vocal_range', {})
            lowest = note_name_to_midi(vocal.get('lowest_note', 'A3'))
            highest = note_name_to_midi(vocal.get('highest_note', 'A4'))
            vocal_mode = vocal.get('mode', 'note_chains')
            if vocal_mode == 'scale_step_triads':
                exercises = generate_vocal_range_scale_step_triads(
                    lowest,
                    highest,
                    repetitions_per_step=cfg.get('repetitions_per_exercise', 1),
                )
            elif vocal_mode == 'scale_step_triads_13531':
                exercises = generate_vocal_range_scale_step_triads_13531(
                    lowest,
                    highest,
                    repetitions_per_step=cfg.get('repetitions_per_exercise', 1),
                )
            else:
                exercises = generate_vocal_range_note_chains(
                    lowest,
                    highest,
                    max_note_chain_length=cfg.get('max_note_chain_length', 5),
                    max_interval_length=cfg.get('max_interval_length', 7),
                    num_chains=cfg.get('num_note_chains', 20),
                )
        else:
            # Normal mode: generate exercises from scale and content
            scale_name = scale_cfg.get('name', 'scale')
            if 'notes' in scale_cfg and scale_cfg['notes']:
                custom_notes = [note_name_to_midi(n) for n in scale_cfg['notes']]
                pool = [n for n in custom_notes if lowest <= n <= highest]
                scale_single_octave = sorted(set([n % 12 + 12 for n in custom_notes]))[:7]
            else:
                root = note_name_to_midi(scale_cfg.get('root', 'A3'))
                stype = scale_cfg.get('type', 'natural_minor')
                pool = expand_scale_over_range(root, stype, lowest, highest)
                scale_single_octave = build_scale_notes(root, stype)

            content = cfg.get('content', {})
            intervals_cfg = content.get('intervals', {})
            triads_cfg = content.get('triads', {})
            rhythm_vocal_cfg = content.get('rhythm_vocal', {})

            max_interval_name = intervals_cfg.get('max_interval', 'perfect_octave')
            max_interval = 12
            include_m3 = intervals_cfg.get('include_minor_3rd_even_in_major', True)
            ascending = intervals_cfg.get('ascending', True)
            descending = intervals_cfg.get('descending', True)

            # Generate exercises from config
            exercises = []
            exercises += generate_intervals(pool, ascending=ascending, descending=descending, max_interval=max_interval, include_m3=include_m3)
            if triads_cfg.get('enabled', True):
                tri_types = triads_cfg.get('types', ['major','minor','diminished'])
                triads = generate_triads(
                    scale_single_octave,
                    pool,
                    include_inversions=triads_cfg.get('include_inversions', True),
                    triad_types=tri_types,
                    low=lowest,
                    high=highest,
                )
                exercises += triads
            if rhythm_vocal_cfg.get('enabled', False):
                # Generate rhythm vocal exercises
                base_note = note_name_to_midi(rhythm_vocal_cfg.get('base_note', 'C4'))
                num_exercises = rhythm_vocal_cfg.get('num_exercises', 10)
                max_pattern_length = rhythm_vocal_cfg.get('max_pattern_length', 8)
                rhythm_exercises = generate_rhythm_vocal_exercises(base_note, num_exercises, max_pattern_length)
                exercises += rhythm_exercises

    # Nur mischen, wenn keine sequences verwendet werden (Skalen/Intervalle/Triaden)
    vocal_mode = (cfg.get('vocal_range', {}) or {}).get('mode', None)
    if not sequences_cfg and vocal_mode not in ('scale_step_triads', 'scale_step_triads_13531'):
        random.shuffle(exercises)
    final_list = []
    # Calculate actual repetitions based on max_duration target
    note_duration = cfg.get('timing', {}).get('note_duration', 1.8)
    pause_between_reps = cfg.get('timing', {}).get('pause_between_reps', 1.0)
    # Each exercise takes ~note_duration + pause_between_reps seconds
    time_per_exercise = note_duration + pause_between_reps
    
    # Get configuration for exercise count and repetitions
    exercises_count_cfg = cfg.get('exercises_count', None)
    repetitions_per_exercise_cfg = cfg.get('repetitions_per_exercise', 1)
    
    # Convert exercises_count to integer if provided
    exercises_count = None
    if exercises_count_cfg is not None:
        try:
            exercises_count = int(exercises_count_cfg)
        except Exception:
            exercises_count = None
    
    # Determine how many times to repeat each exercise
    # Priority: repetitions_per_exercise (if > 1) > exercises_count > duration-based calculation
    actual_reps = 1
    max_unique_exercises = len(exercises) if len(exercises) > 0 else 1
    
    if repetitions_per_exercise_cfg > 1:
        # If repetitions_per_exercise is explicitly set, use it
        actual_reps = repetitions_per_exercise_cfg
    elif exercises_count is not None and exercises_count > 0:
        # If exercises_count is set, calculate how many unique exercises to include
        # such that unique_exercises * repetitions = exercises_count
        # For simplicity, use exercises_count as the total count with reps = 1
        actual_reps = 1
        max_unique_exercises = exercises_count
    else:
        # Fall back to duration-based calculation
        max_total_exercises = int(max_duration_seconds / time_per_exercise)
        if max_total_exercises < 1:
            max_total_exercises = 1
        # Calculate how many times to repeat to fill the duration
        if max_unique_exercises > 0:
            actual_reps = max(1, max_total_exercises // max_unique_exercises)
        else:
            actual_reps = 1
    
    # Build final list as cyclic block pattern: repeat all sequences repetitions_per_exercise times, then next block, until max_duration
    final_list = []
    # Track which original exercise each item in final_list came from (for pause_between_blocks)
    exercise_indices = []
    if len(exercises) > 0:
        if args.from_text:
            # When loading from text, use exercises as-is without repetition
            # Respect exercises_count if set
            if exercises_count is not None and exercises_count > 0:
                final_list = exercises[:exercises_count]
                exercise_indices = list(range(len(final_list)))
            else:
                max_count = int(max_duration_seconds / time_per_exercise)
                final_list = exercises[:max(1, max_count)]
                exercise_indices = list(range(len(final_list)))
        elif sequences_cfg:
            # Blockwise repetition for sequences: each sequence repeated n times before moving to next
            for ex_idx, ex in enumerate(exercises):
                for _ in range(repetitions_per_exercise_cfg):
                    final_list.append(ex)
                    exercise_indices.append(ex_idx)
            # Am Ende alle sequences als eine kombinierte Sequenz anhängen, wiederholt
            if combine_sequences_to_one:
                # Kombiniere alle sequences zu einer einzigen
                combined_notes = []
                for ex in exercises:
                    if ex[0] == 'sequence':
                        combined_notes.extend(ex[1])
                combined_ex = ('sequence', combined_notes)
                combined_idx = len(exercises)  # Use a new index for combined sequence
                for _ in range(repetitions_per_exercise_cfg):
                    final_list.append(combined_ex)
                    exercise_indices.append(combined_idx)
        else:
            # For intervals/triads, use duration-based filling
            vocal_mode = (cfg.get('vocal_range', {}) or {}).get('mode', None)
            total_time = 0.0
            while True:
                for ex_idx, ex in enumerate(exercises):
                    reps_for_this_ex = 1 if vocal_mode in ('scale_step_triads', 'scale_step_triads_13531') else actual_reps
                    for _ in range(reps_for_this_ex):
                        if exercises_count is not None and len(final_list) >= exercises_count:
                            break
                        if total_time + time_per_exercise > max_duration_seconds:
                            break
                        final_list.append(ex)
                        exercise_indices.append(ex_idx)
                        total_time += time_per_exercise
                    if exercises_count is not None and len(final_list) >= exercises_count:
                        break
                    if total_time + time_per_exercise > max_duration_seconds:
                        break
                # Abbruch, wenn Zeit oder Anzahl erreicht
                if exercises_count is not None and len(final_list) >= exercises_count:
                    break
                if total_time + time_per_exercise > max_duration_seconds:
                    break
    
    # Calculate estimated final duration
    estimated_duration = len(final_list) * time_per_exercise
    
    if not args.dry_run:
        print(f'Target duration: {max_duration_seconds}s ({max_duration_seconds//60}m {max_duration_seconds%60}s)')
        print(f'Estimated duration: ~{int(estimated_duration)}s ({int(estimated_duration)//60}m {int(estimated_duration)%60}s)')
        print(f'Generated {len(final_list)} exercises from {len(exercises)} unique exercise(s)')
        print()

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_name = args.output or fname_template.format(scale=scale_name.replace(' ', '_'), date=timestamp)

    tmpdir = tempfile.mkdtemp(prefix='intonation_')
    parts = []
    # If dry run requested, write only the text log and exit (no audio rendering)
    if args.dry_run:
        text_path = args.text_file or (os.path.splitext(out_name)[0] + '.txt')
        write_text_log(text_path, final_list, time_signature=time_signature)
        shutil.rmtree(tmpdir)
        return

    # Prepare sound config early (velocity used for MIDI creation)
    sf_cfg = cfg.get('sound', {})
    method = sf_cfg.get('method', 'soundfont')
    sf2_path = sf_cfg.get('soundfont_path', 'piano/SalamanderGrandPiano.sf2')
    velocity = sf_cfg.get('velocity', 90)

    # Also build a combined MIDI file representing the whole session so the
    # user can open it in a MIDI editor. This MIDI is written regardless
    # of whether FluidSynth is used for audio rendering.
    if final_list:
        try:
            session_mid = MidiFile()
            track = MidiTrack()
            session_mid.tracks.append(track)
            tempo_bpm = cfg.get('timing', {}).get('intro_bpm', 120)
            track.append(mido.MetaMessage('set_tempo', tempo=bpm2tempo(tempo_bpm)))
            ticks_per_beat = session_mid.ticks_per_beat
            # helper to convert seconds -> ticks (approx using bpm)
            def secs_to_ticks(s):
                return int(s * (ticks_per_beat * tempo_bpm / 60.0))

            note_dur = cfg.get('timing', {}).get('note_duration', 1.8)
            intra_interval_gap = 0.1  # 100 ms gap between two notes of an interval
            pause_between_reps = cfg.get('timing', {}).get('pause_between_reps', 1.0)
            pause_between_blocks = cfg.get('timing', {}).get('pause_between_blocks', 2.0)

            for i, ex in enumerate(final_list):
                # Determine which pause to use after this exercise
                if i < len(final_list) - 1:
                    # Check if next exercise is from a different block
                    current_ex_idx = exercise_indices[i] if i < len(exercise_indices) else i
                    next_ex_idx = exercise_indices[i + 1] if (i + 1) < len(exercise_indices) else (i + 1)
                    rest_between = pause_between_blocks if current_ex_idx != next_ex_idx else pause_between_reps
                else:
                    # Last exercise, use pause_between_reps
                    rest_between = pause_between_reps

                append_exercise_to_session_track(
                    track,
                    ex,
                    velocity=velocity,
                    secs_to_ticks=secs_to_ticks,
                    note_dur=note_dur,
                    intra_interval_gap=intra_interval_gap,
                    rest_between=rest_between,
                )

            base = os.path.splitext(out_name)[0]
            session_midi_path = base + '.mid'
            session_mid.save(session_midi_path)
            print(f'Wrote session MIDI to {session_midi_path}')
            # Audio rendering removed: this tool now produces MIDI files only.
            # Skip the rest of the audio rendering pipeline (fluidsynth/ffmpeg/pydub).
            if not args.verbose:
                # If user did not request verbose text log, exit now after writing MIDI
                return
            # If verbose requested, fall through to write the text log and then exit
        except Exception as e:
            print(f'Warning: failed to write session MIDI: {e}')

    try:
        # No audio rendering: write the text log using the actual MIDI ticks per beat
        text_path = args.text_file or (os.path.splitext(out_name)[0] + '.txt')
        ticks_val = session_mid.ticks_per_beat if 'session_mid' in locals() else 480
        write_text_log(text_path, final_list, ticks_per_beat=ticks_val, time_signature=time_signature)
        return
    except Exception as e:
        print(f'Warning: failed to write text log: {e}')

    finally:
        shutil.rmtree(tmpdir)


if __name__ == '__main__':
    main()
