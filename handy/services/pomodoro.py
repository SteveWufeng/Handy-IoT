class PomodoroTimer:
    def __init__(self, config, on_phase_end=None):
        self.config = config
        self.on_phase_end = on_phase_end
        self.phase = "work"
        self.running = False
        self.completed = 0
        self.remaining = self.duration()
        self.last_started_phase = None

    def minutes(self, phase):
        mapping = {
            "work": self.config.get("pomodoro.work_minutes", 25),
            "short_break": self.config.get("pomodoro.break_minutes", 5),
            "long_break": self.config.get("pomodoro.long_break_minutes", 15),
        }
        return max(1, int(mapping.get(phase, 25) or 25))

    def duration(self, phase=None):
        return self.minutes(phase or self.phase) * 60

    def cycles(self):
        return max(1, int(self.config.get("pomodoro.cycles", 4) or 4))

    def auto_start(self):
        return bool(self.config.get("pomodoro.auto_start", True))

    def toggle(self):
        if self.remaining <= 0:
            self.remaining = self.duration()
        self.running = not self.running
        if self.running:
            self.last_started_phase = self.phase

    def start(self):
        if not self.running:
            self.toggle()

    def pause(self):
        self.running = False

    def reset(self):
        self.running = False
        self.remaining = self.duration()
        self.last_started_phase = None

    def reset_all(self):
        self.phase = "work"
        self.completed = 0
        self.reset()

    def skip(self):
        finished = self.phase
        self._advance(count_work=False)
        if self.on_phase_end:
            self.on_phase_end(finished, self.phase, True)

    def _advance(self, count_work=True):
        if self.phase == "work":
            if count_work:
                self.completed += 1
            long_break = self.completed > 0 and self.completed % self.cycles() == 0
            self.phase = "long_break" if long_break else "short_break"
        else:
            self.phase = "work"
        self.remaining = self.duration()
        self.running = self.auto_start()
        self.last_started_phase = self.phase if self.running else None

    def update(self, dt):
        if not self.running:
            return
        self.remaining -= dt
        if self.remaining <= 0:
            finished = self.phase
            self._advance(count_work=True)
            if self.on_phase_end:
                self.on_phase_end(finished, self.phase, False)

    @property
    def progress(self):
        total = self.duration()
        if total <= 0:
            return 0.0
        return min(1.0, max(0.0, 1.0 - self.remaining / total))

    def phase_label(self):
        return {
            "work": "Focus",
            "short_break": "Short break",
            "long_break": "Long break",
        }.get(self.phase, self.phase)

    def summary(self):
        if self.running:
            return f"{self.phase_label()} - {self.clock()} left"
        if self.last_started_phase and self.remaining < self.duration():
            return f"Paused - {self.clock()} left"
        return f"{self.minutes('work')} min focus / {self.minutes('short_break')} min break"

    def clock(self):
        seconds = max(0, int(self.remaining + 0.999))
        minutes, secs = divmod(seconds, 60)
        return f"{minutes:02d}:{secs:02d}"

    def session_label(self):
        cycle = (self.completed % self.cycles()) + 1
        if self.completed and self.completed % self.cycles() == 0 and self.phase != "work":
            cycle = self.cycles()
        return f"Session {cycle} of {self.cycles()}"
