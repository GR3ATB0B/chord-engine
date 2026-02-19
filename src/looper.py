"""
looper.py — Loop recorder with overdub support.

Records MIDI events with timestamps, plays them back in a loop,
and supports layered overdubbing. Each layer remembers its instrument.
"""

import time
import threading


class LoopEvent:
    """A single recorded MIDI event."""
    __slots__ = ('time', 'event_type', 'channel', 'note', 'velocity', 'program')

    def __init__(self, time, event_type, channel, note, velocity, program):
        self.time = time          # seconds from loop start
        self.event_type = event_type  # 'note_on' or 'note_off'
        self.channel = channel
        self.note = note
        self.velocity = velocity
        self.program = program    # GM program at time of recording


class LoopLayer:
    """A single layer of recorded events."""
    def __init__(self, program):
        self.events = []
        self.program = program  # primary instrument for this layer

    def add(self, event):
        self.events.append(event)


class Looper:
    """
    Loop recorder with overdub.

    Usage:
        looper = Looper(synth_engine)
        looper.toggle_record(current_program)  # start recording
        looper.record_event(...)               # feed MIDI events
        looper.toggle_record(current_program)  # stop & start playback
        looper.toggle_record(current_program)  # overdub new layer
    """

    # States
    IDLE = 'idle'
    RECORDING = 'recording'
    PLAYING = 'playing'
    PAUSED = 'paused'
    OVERDUBBING = 'overdubbing'

    def __init__(self, synth):
        self.synth = synth  # SynthEngine instance (needs noteon/noteoff on arbitrary channels)
        self.state = self.IDLE
        self.layers = []
        self.loop_length = 0.0  # seconds
        self._record_start = 0.0
        self._current_layer = None
        self._playback_thread = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        # Channel allocation for playback layers (use channels 1-8 to avoid 0=live, 9=drums)
        self._layer_channels = list(range(1, 9))

    def toggle_record(self, current_program):
        """Toggle recording. Returns new state string."""
        with self._lock:
            if self.state == self.IDLE:
                # First recording ever
                self._start_recording(current_program)
                # print("⏺️  Recording...")
                return self.RECORDING

            elif self.state == self.RECORDING:
                # Stop first recording, set loop length, start playback
                self._stop_recording()
                self.loop_length = time.monotonic() - self._record_start
                # print(f"⏹️  Loop recorded ({self.loop_length:.1f}s)")
                self._start_playback()
                # print("▶️  Playing")
                return self.PLAYING

            elif self.state == self.PLAYING:
                # Start overdub
                self._start_recording(current_program)
                self.state = self.OVERDUBBING
                # print("⏺️  Overdubbing...")
                return self.OVERDUBBING

            elif self.state == self.OVERDUBBING:
                # Stop overdub, continue playback
                self._stop_recording()
                self.state = self.PLAYING
                # print("⏹️  Layer added")
                return self.PLAYING

            elif self.state == self.PAUSED:
                # Resume and start overdub
                self._start_recording(current_program)
                self._start_playback()
                self.state = self.OVERDUBBING
                # print("⏺️  Overdubbing...")
                return self.OVERDUBBING

    def toggle_play_pause(self):
        """Toggle play/pause."""
        with self._lock:
            if self.state == self.PLAYING or self.state == self.OVERDUBBING:
                if self.state == self.OVERDUBBING:
                    self._stop_recording()
                self._stop_playback()
                self.state = self.PAUSED
                # print("⏸️  Paused")
                return self.PAUSED
            elif self.state == self.PAUSED:
                self._start_playback()
                # print("▶️  Playing")
                return self.PLAYING
            return self.state

    def undo_layer(self):
        """Remove the last recorded layer."""
        with self._lock:
            if self.layers:
                self.layers.pop()
                # print(f"↩️  Undo layer ({len(self.layers)} remaining)")
                if not self.layers:
                    self._stop_playback()
                    self.loop_length = 0.0
                    self.state = self.IDLE
                    print("🗑️  All layers removed")
            return self.state

    def clear_all(self):
        """Clear everything."""
        with self._lock:
            self._stop_playback()
            if self.state == self.RECORDING or self.state == self.OVERDUBBING:
                self._current_layer = None
            self.layers.clear()
            self.loop_length = 0.0
            self.state = self.IDLE
            print("🗑️  Cleared")
            return self.IDLE

    def record_event(self, event_type, channel, note, velocity, program):
        """Record a MIDI event into the current layer."""
        if self._current_layer is None:
            return
        t = time.monotonic() - self._record_start
        # Wrap time to loop length for overdubs
        if self.loop_length > 0:
            t = t % self.loop_length
        self._current_layer.add(LoopEvent(t, event_type, channel, note, velocity, program))

    def is_recording(self):
        return self.state in (self.RECORDING, self.OVERDUBBING)

    # --- Internal ---

    def _start_recording(self, program):
        self._current_layer = LoopLayer(program)
        if self.state == self.IDLE:
            self._record_start = time.monotonic()
        else:
            # Overdub: sync to existing loop
            self._record_start = time.monotonic()
        self.state = self.RECORDING

    def _stop_recording(self):
        if self._current_layer and self._current_layer.events:
            self.layers.append(self._current_layer)
        self._current_layer = None

    def _start_playback(self):
        self._stop_event.clear()
        self.state = self.PLAYING
        self._playback_thread = threading.Thread(target=self._playback_loop, daemon=True)
        self._playback_thread.start()

    def _stop_playback(self):
        self._stop_event.set()
        if self._playback_thread:
            self._playback_thread.join(timeout=2.0)
            self._playback_thread = None
        # Kill any lingering playback notes
        self._silence_playback_channels()

    def _silence_playback_channels(self):
        """Send all-notes-off on playback channels."""
        if not self.synth or not hasattr(self.synth, 'fs') or not self.synth.fs:
            return
        for ch in self._layer_channels:
            self.synth.fs.cc(ch, 123, 0)  # All Notes Off
        # Also drum channel
        self.synth.fs.cc(9, 123, 0)

    def _playback_loop(self):
        """Background thread: loop through recorded layers."""
        if self.loop_length <= 0:
            return

        fs = self.synth.fs
        sfid = self.synth.sfid
        if not fs or sfid is None:
            return

        while not self._stop_event.is_set():
            loop_start = time.monotonic()

            # Build a merged, time-sorted event list from all layers
            all_events = []
            layers_snapshot = list(self.layers)  # snapshot to avoid lock issues
            for i, layer in enumerate(layers_snapshot):
                # Assign playback channel per layer (cycle through available)
                ch_map = {}  # original_channel -> playback_channel
                for ev in layer.events:
                    if ev.channel == 9:
                        play_ch = 9  # drums stay on 9
                    else:
                        if ev.channel not in ch_map:
                            ch_map[ev.channel] = self._layer_channels[i % len(self._layer_channels)]
                        play_ch = ch_map[ev.channel]
                    all_events.append((ev.time, ev, play_ch, layer.program))

            all_events.sort(key=lambda x: x[0])

            # Set up programs for each layer's channel
            programs_set = set()
            for i, layer in enumerate(layers_snapshot):
                ch = self._layer_channels[i % len(self._layer_channels)]
                key = (ch, layer.program)
                if key not in programs_set:
                    fs.program_select(ch, sfid, 0, layer.program)
                    programs_set.add(key)

            # Play events
            for evt_time, ev, play_ch, program in all_events:
                if self._stop_event.is_set():
                    self._silence_playback_channels()
                    return

                # Wait until it's time
                target = loop_start + evt_time
                now = time.monotonic()
                if target > now:
                    self._stop_event.wait(target - now)
                    if self._stop_event.is_set():
                        self._silence_playback_channels()
                        return

                # For drum events, use channel 9 directly
                if ev.channel == 9:
                    if ev.event_type == 'note_on':
                        fs.noteon(9, ev.note, ev.velocity)
                    else:
                        fs.noteoff(9, ev.note)
                else:
                    # Set program for this specific event if it differs
                    if ev.program != program:
                        fs.program_select(play_ch, sfid, 0, ev.program)
                    if ev.event_type == 'note_on':
                        fs.noteon(play_ch, ev.note, ev.velocity)
                    else:
                        fs.noteoff(play_ch, ev.note)

            # Wait for remainder of loop
            elapsed = time.monotonic() - loop_start
            remaining = self.loop_length - elapsed
            if remaining > 0:
                self._stop_event.wait(remaining)

            # Silence between loops
            self._silence_playback_channels()
