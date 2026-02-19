"""
voice_leading.py — Voice leading algorithm for smooth chord transitions.

The magic sauce. When you change chords, this finds the voicing that
minimizes total voice movement — so transitions sound smooth and musical
instead of jumpy and robotic. This is what makes the Orchid special.
"""

from itertools import permutations


def smooth_voice_lead(previous_notes, new_chord_tones, anchor_octave=4):
    """
    Given the previous sounding notes and the new chord's pitch classes,
    return a list of MIDI note numbers that minimizes total voice movement.

    Args:
        previous_notes: List of MIDI note numbers currently sounding.
                       Empty list on first chord.
        new_chord_tones: List of pitch classes (0-11) for the new chord.
        anchor_octave: Default octave when there are no previous notes.

    Returns:
        List of MIDI note numbers for the new chord voicing.
    """
    if not new_chord_tones:
        return []

    # First chord — no voice leading needed, just place around anchor
    if not previous_notes:
        return _place_in_octave(new_chord_tones, anchor_octave)

    # Generate candidate voicings for each new pitch class:
    # For each pitch class, consider it in multiple octaves near the previous notes
    center = sum(previous_notes) / len(previous_notes)
    center_octave = int(center) // 12

    # Generate all candidate MIDI notes for each pitch class (within ±1 octave of center)
    candidates_per_tone = []
    for pc in new_chord_tones:
        candidates = []
        for oct in range(max(0, center_octave - 1), min(9, center_octave + 2)):
            note = oct * 12 + pc
            if 24 <= note <= 96:  # Keep in reasonable piano range
                candidates.append(note)
        if not candidates:
            candidates = [anchor_octave * 12 + pc]
        candidates_per_tone.append(candidates)

    # If same number of voices, try to match each new note to a previous note
    if len(new_chord_tones) == len(previous_notes):
        return _match_voices(previous_notes, candidates_per_tone)

    # Different voice count — use greedy placement
    return _greedy_place(previous_notes, candidates_per_tone, center)


def _place_in_octave(pitch_classes, octave):
    """Place pitch classes in a given octave. Simple default voicing."""
    notes = []
    for pc in pitch_classes:
        note = octave * 12 + pc
        # Keep in MIDI range
        while note < 36:
            note += 12
        while note > 84:
            note -= 12
        notes.append(note)
    return sorted(notes)


def _match_voices(previous_notes, candidates_per_tone):
    """
    Match new chord tones to previous notes minimizing total movement.
    Uses Hungarian-style greedy matching for speed (exact solution for ≤4 voices).
    """
    n = len(previous_notes)

    if n <= 4:
        # For small voice counts, try all permutations (at most 24)
        best_voicing = None
        best_cost = float("inf")

        for perm in permutations(range(n)):
            voicing = []
            cost = 0
            valid = True
            for i, j in enumerate(perm):
                # Pick the candidate for tone j closest to previous_notes[i]
                prev = previous_notes[i]
                candidates = candidates_per_tone[j]
                nearest = min(candidates, key=lambda c: abs(c - prev))
                voicing.append(nearest)
                cost += abs(nearest - prev)
            if cost < best_cost:
                best_cost = cost
                best_voicing = voicing[:]

        return sorted(best_voicing)
    else:
        # Greedy for larger voicings
        return _greedy_place(previous_notes, candidates_per_tone,
                             sum(previous_notes) / len(previous_notes))


def _greedy_place(previous_notes, candidates_per_tone, center):
    """Greedy voice placement — each new tone picks its closest candidate to center/prev."""
    result = []
    used_prev = set()

    for candidates in candidates_per_tone:
        if previous_notes:
            # Find the closest (candidate, prev_note) pair
            best_note = None
            best_dist = float("inf")
            for c in candidates:
                for i, p in enumerate(previous_notes):
                    if i not in used_prev:
                        dist = abs(c - p)
                        if dist < best_dist:
                            best_dist = dist
                            best_note = c
                            best_prev_idx = i
                # Also consider placement near center if no prev available
                dist_to_center = abs(c - center)
                if dist_to_center < best_dist and len(used_prev) >= len(previous_notes):
                    best_dist = dist_to_center
                    best_note = c

            if best_note is not None:
                result.append(best_note)
                if 'best_prev_idx' in dir():
                    used_prev.add(best_prev_idx)
            else:
                result.append(candidates[len(candidates) // 2])
        else:
            result.append(candidates[len(candidates) // 2])

    return sorted(result)


def apply_spread(notes, spread_amount):
    """
    Apply spread/voicing width to a set of notes.

    Args:
        notes: List of MIDI note numbers (sorted).
        spread_amount: 0.0 = tight (close voicing), 1.0 = wide (open voicing, 2+ octaves).

    Returns:
        Adjusted list of MIDI note numbers.
    """
    if len(notes) <= 1 or spread_amount <= 0:
        return notes

    result = [notes[0]]  # Keep root

    for i, note in enumerate(notes[1:], 1):
        # Spread upper voices upward based on spread_amount
        # At spread=0, keep as-is. At spread=1, move each voice up by i*12 semitones
        offset = int(spread_amount * i * 6)  # Up to 6 semitones per voice per spread unit
        new_note = note + offset
        # Clamp to MIDI range
        new_note = min(max(new_note, 0), 127)
        result.append(new_note)

    return result


def apply_inversion(notes, inversion):
    """
    Apply chord inversion.

    Args:
        notes: Sorted list of MIDI note numbers.
        inversion: 0=root, 1=first, 2=second, 3=third.

    Returns:
        Inverted chord notes.
    """
    if not notes or inversion <= 0:
        return notes

    result = list(notes)
    for _ in range(min(inversion, len(result) - 1)):
        # Move lowest note up an octave
        lowest = result.pop(0)
        result.append(lowest + 12)

    return sorted(result)
