import datetime as dt
import threading
from dataclasses import dataclass
from pathlib import Path

import icalendar
import recurring_ical_events
import requests

LOCAL_TZ = dt.datetime.now().astimezone().tzinfo
CACHE_PATH = Path.home() / ".cache" / "handy-iot" / "calendar.ics"
USER_AGENT = "HandyIoT/1.0 (+https://github.com/)"


@dataclass(frozen=True)
class Event:
    summary: str
    start: dt.datetime
    end: dt.datetime
    all_day: bool
    location: str = ""

    @property
    def start_date(self):
        return self.start.date()

    @property
    def end_date(self):
        return self.end.date()

    @property
    def ongoing(self):
        return self.start <= dt.datetime.now().astimezone() < self.end

    def time_label(self):
        if self.all_day:
            return "All day"
        if self.start.date() == self.end.date():
            return f"{self.start:%H:%M} - {self.end:%H:%M}"
        return f"{self.start:%b %d} - {self.end:%b %d}"


def _local(value):
    if isinstance(value, dt.datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=LOCAL_TZ)
        return value.astimezone(LOCAL_TZ)
    return value


def _event_from_component(component):
    start_prop = component.get("DTSTART")
    if start_prop is None:
        return None
    raw_start = start_prop.dt
    end_prop = component.get("DTEND")
    duration_prop = component.get("DURATION")
    summary = str(component.get("SUMMARY") or "(No title)").strip()
    location = str(component.get("LOCATION") or "").strip()

    if isinstance(raw_start, dt.datetime):
        start = _local(raw_start)
        if end_prop is not None:
            end = _local(end_prop.dt)
        elif duration_prop is not None:
            end = start + duration_prop.dt
        else:
            end = start
        end = max(end, start)
        return Event(summary, start, end, False, location)

    start_date = raw_start
    if end_prop is not None:
        end_date = end_prop.dt
        if isinstance(end_date, dt.datetime):
            end_date = end_date.date()
    elif duration_prop is not None:
        end_date = start_date + duration_prop.dt
    else:
        end_date = start_date + dt.timedelta(days=1)
    if end_date <= start_date:
        end_date = start_date + dt.timedelta(days=1)
    start = dt.datetime.combine(start_date, dt.time.min, tzinfo=LOCAL_TZ)
    end = dt.datetime.combine(end_date, dt.time.min, tzinfo=LOCAL_TZ)
    if end <= start:
        end = start + dt.timedelta(days=1)
    return Event(summary, start, end, True, location)


class CalendarService:
    def __init__(self, config):
        self.config = config
        self.events = []
        self.updated = None
        self.error = None
        self._lock = threading.Lock()
        self.load_cache()

    @property
    def url(self):
        return (self.config.get("calendar.ics_url", "") or "").strip()

    @property
    def days_ahead(self):
        return int(self.config.get("calendar.days_ahead", 14) or 14)

    @property
    def max_events(self):
        return int(self.config.get("calendar.max_events", 40) or 40)

    @property
    def refresh_minutes(self):
        return int(self.config.get("calendar.refresh_minutes", 15) or 15)

    def _window(self):
        now = dt.datetime.now().astimezone()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + dt.timedelta(days=self.days_ahead)
        return start, end

    def _parse(self, payload):
        calendar = icalendar.Calendar.from_ical(payload)
        start, end = self._window()
        occurrences = recurring_ical_events.of(calendar).between(start, end)
        events = []
        for component in occurrences:
            if component.name != "VEVENT":
                continue
            status = str(component.get("STATUS", "")).upper()
            if status == "CANCELLED":
                continue
            event = _event_from_component(component)
            if event is not None and event.end > start:
                events.append(event)
        events.sort(key=lambda item: (item.start, item.end, item.summary.lower()))
        return events

    def load_cache(self):
        try:
            payload = CACHE_PATH.read_bytes()
            events = self._parse(payload)
        except (OSError, ValueError, KeyError):
            return
        with self._lock:
            self.events = events
            self.updated = dt.datetime.fromtimestamp(CACHE_PATH.stat().st_mtime).astimezone()

    def refresh(self):
        url = self.url
        if not url:
            self.error = "No calendar URL configured"
            return self.events
        if url.startswith("webcal://"):
            url = "https://" + url[len("webcal://"):]
        try:
            response = requests.get(url, timeout=20, headers={"User-Agent": USER_AGENT})
            response.raise_for_status()
            events = self._parse(response.content)
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "?"
            self.error = f"Calendar server returned {status}"
            raise
        except requests.RequestException:
            self.error = "Network unavailable"
            raise
        except Exception:
            self.error = "Could not read calendar feed"
            raise
        try:
            CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            CACHE_PATH.write_bytes(response.content)
        except OSError:
            pass
        with self._lock:
            self.events = events
            self.updated = dt.datetime.now().astimezone()
            self.error = None
        return events

    def upcoming(self):
        now = dt.datetime.now().astimezone()
        with self._lock:
            events = list(self.events)
        return [event for event in events if event.end > now][:self.max_events]

    def next_event(self):
        events = self.upcoming()
        return events[0] if events else None

    def stale(self):
        if self.updated is None:
            return True
        age = (dt.datetime.now().astimezone() - self.updated).total_seconds()
        return age > self.refresh_minutes * 60

    def updated_label(self):
        if self.updated is None:
            return "Not synced"
        age = (dt.datetime.now().astimezone() - self.updated).total_seconds()
        if age < 60:
            return "Updated just now"
        if age < 3600:
            return f"Updated {int(age // 60)}m ago"
        if age < 86400:
            return f"Updated {int(age // 3600)}h ago"
        return self.updated.strftime("Updated %b %d")
