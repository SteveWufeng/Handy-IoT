import array
import math
import time

import pygame

SAMPLE_RATE = 44100


def _render(notes, volume=0.45):
    buffer = array.array("h")
    for frequency, milliseconds in notes:
        frames = int(SAMPLE_RATE * milliseconds / 1000)
        for index in range(frames):
            attack = min(1.0, index / max(1, SAMPLE_RATE * 0.012))
            release = min(1.0, (frames - index) / max(1, SAMPLE_RATE * 0.09))
            envelope = max(0.0, min(attack, release))
            sample = math.sin(2 * math.pi * frequency * index / SAMPLE_RATE)
            buffer.append(int(32767 * volume * envelope * sample))
    return buffer.tobytes()


class Chime:
    def __init__(self, enabled=True):
        self.enabled = bool(enabled)
        self.sounds = {}
        self._release_at = 0.0
        if self.enabled:
            self.sounds["focus_done"] = _render([(659, 150), (880, 180), (1319, 320)])
            self.sounds["break_done"] = _render([(880, 150), (659, 180), (440, 320)])
            self.sounds["tap"] = _render([(1200, 45)], volume=0.18)

    def play(self, name):
        if not self.enabled:
            return
        payload = self.sounds.get(name)
        if not payload:
            return
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(44100, -16, 1, 512)
            sound = pygame.mixer.Sound(buffer=payload)
            sound.play()
            self._release_at = time.monotonic() + max(0.8, sound.get_length()) + 0.35
        except pygame.error:
            self._release_at = 0.0

    def tick(self):
        if self._release_at and time.monotonic() >= self._release_at:
            try:
                pygame.mixer.quit()
            except pygame.error:
                pass
            self._release_at = 0.0
