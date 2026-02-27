"""Everytime timetable parser service.

Fetches public Everytime timetable HTML and extracts lecture blocks to
normalized interval pairs.
"""
import logging
import re
from typing import List, Tuple
from html.parser import HTMLParser
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

logger = logging.getLogger(__name__)

PIXELS_PER_HOUR = 60
MINUTES_PER_DAY = 1440


class EverytimeParserError(Exception):
    """Raised when Everytime link parsing fails."""


class EverytimeTimetableParser:
    """Parser for public Everytime timetable pages."""

    def validate_everytime_url(self, url: str) -> bool:
        """Validate URL format for Everytime timetable share links."""
        try:
            parsed = urlparse(url)
            if parsed.scheme not in {"http", "https"}:
                return False
            if not parsed.netloc.endswith("everytime.kr"):
                return False
            if not parsed.path.startswith("/@"):
                return False
            return True
        except Exception:
            return False

    def fetch_html(self, url: str, timeout_seconds: int = 5) -> str:
        """Fetch HTML from Everytime share URL."""
        if not self.validate_everytime_url(url):
            raise EverytimeParserError("Invalid Everytime timetable URL")

        try:
            request = Request(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    )
                },
            )
            with urlopen(request, timeout=timeout_seconds) as response:
                return response.read().decode("utf-8", errors="ignore")
        except (URLError, HTTPError, TimeoutError) as exc:
            raise EverytimeParserError(f"Failed to fetch Everytime HTML: {exc}") from exc

    def parse_html_to_pairs(self, html: str) -> List[Tuple[int, int, int]]:
        """Parse Everytime HTML and return (day_of_week, start_minute, end_minute)."""
        parser = _EverytimeHTMLSubjectParser()
        parser.feed(html)

        if not parser.subject_styles:
            raise EverytimeParserError("Timetable columns not found in HTML")

        interval_pairs: List[Tuple[int, int, int]] = []
        for day_index, style in parser.subject_styles:
            start_minute, end_minute = self._px_style_to_minutes(style)
            if start_minute is None or end_minute is None:
                continue

            start_minute = self._align_to_5min(start_minute)
            end_minute = self._align_to_5min(end_minute)

            if start_minute < 0:
                start_minute = 0
            if end_minute > MINUTES_PER_DAY:
                end_minute = MINUTES_PER_DAY

            if start_minute >= end_minute:
                continue

            interval_pairs.append((day_index, start_minute, end_minute))

        return interval_pairs

    def parse_from_url(self, url: str, timeout_seconds: int = 5) -> List[Tuple[int, int, int]]:
        """Fetch Everytime link and parse timetable interval pairs."""
        html = self.fetch_html(url, timeout_seconds=timeout_seconds)
        return self.parse_html_to_pairs(html)

    @staticmethod
    def _align_to_5min(minute: int) -> int:
        return (minute // 5) * 5

    @staticmethod
    def _px_style_to_minutes(style: str):
        top_match = re.search(r"top:\s*(\d+)px", style)
        height_match = re.search(r"height:\s*(\d+)px", style)
        if not top_match or not height_match:
            return None, None

        top_px = int(top_match.group(1))
        height_px = int(height_match.group(1))

        start_hour = top_px / PIXELS_PER_HOUR
        duration_hour = height_px / PIXELS_PER_HOUR

        start_minute = int(start_hour * 60)
        end_minute = int((start_hour + duration_hour) * 60)

        return start_minute, end_minute


class _EverytimeHTMLSubjectParser(HTMLParser):
    """Extract weekday subject style strings from Everytime timetable HTML."""

    def __init__(self):
        super().__init__()
        self.subject_styles: List[Tuple[int, str]] = []
        self._in_tablebody = False
        self._in_tr = False
        self._table_depth = 0
        self._tr_depth = 0
        self._weekday_td_index = -1
        self._current_td_is_hidden = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        classes = set(attrs_dict.get("class", "").split())

        if tag == "table" and "tablebody" in classes:
            self._in_tablebody = True
            self._table_depth += 1
            return

        if self._in_tablebody and tag == "table":
            self._table_depth += 1
            return

        if self._in_tablebody and tag == "tr" and not self._in_tr:
            self._in_tr = True
            self._tr_depth = 1
            self._weekday_td_index = -1
            return
        elif self._in_tr and tag == "tr":
            self._tr_depth += 1
            return

        if self._in_tr and tag == "td":
            self._weekday_td_index += 1
            style = attrs_dict.get("style", "")
            self._current_td_is_hidden = "display: none" in style
            return

        if self._in_tr and tag == "div" and "subject" in classes:
            style = attrs_dict.get("style")
            if (
                style
                and 0 <= self._weekday_td_index <= 4
                and not self._current_td_is_hidden
            ):
                self.subject_styles.append((self._weekday_td_index, style))

    def handle_endtag(self, tag):
        if self._in_tr and tag == "td":
            self._current_td_is_hidden = False
            return

        if self._in_tr and tag == "tr":
            self._tr_depth -= 1
            if self._tr_depth <= 0:
                self._in_tr = False
                self._weekday_td_index = -1
            return

        if self._in_tablebody and tag == "table":
            self._table_depth -= 1
            if self._table_depth <= 0:
                self._in_tablebody = False
