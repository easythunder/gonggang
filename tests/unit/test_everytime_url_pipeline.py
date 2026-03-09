from src.services.everytime_parser import EverytimeTimetableParser
from src.services.interval_extractor import IntervalExtractor


class _MockHTTPResponse:
    def __init__(self, body: str):
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self._body.encode("utf-8")


def test_parse_from_url_with_mocked_crawling(monkeypatch):
    html = """
    <div class="tablebody">
      <table class="tablebody">
        <tbody>
          <tr>
            <th></th>
            <td><div class="subject" style="height: 60px; top: 600px;"></div></td>
            <td><div class="subject" style="height: 90px; top: 630px;"></div></td>
            <td></td>
            <td></td>
            <td></td>
          </tr>
        </tbody>
      </table>
    </div>
    """

    def _mock_urlopen(request, timeout=5):
        return _MockHTTPResponse(html)

    monkeypatch.setattr("src.services.everytime_parser.urlopen", _mock_urlopen)

    parser = EverytimeTimetableParser()
    pairs = parser.parse_from_url("https://everytime.kr/@abc123")

    assert pairs == [
        (0, 600, 660),
        (1, 630, 720),
    ]


def test_url_to_interval_extraction_time_calculation(monkeypatch):
    html = """
    <div class="tablebody">
      <table class="tablebody">
        <tbody>
          <tr>
            <th></th>
            <td><div class="subject" style="height: 60px; top: 600px;"></div></td>
            <td><div class="subject" style="height: 90px; top: 630px;"></div></td>
            <td></td>
            <td></td>
            <td></td>
          </tr>
        </tbody>
      </table>
    </div>
    """

    def _mock_urlopen(request, timeout=5):
        return _MockHTTPResponse(html)

    monkeypatch.setattr("src.services.everytime_parser.urlopen", _mock_urlopen)

    parser = EverytimeTimetableParser()
    extractor = IntervalExtractor(display_unit_minutes=30)

    pairs = parser.parse_from_url("https://everytime.kr/@abc123")
    intervals = extractor.extract_intervals_from_pairs(pairs)

    assert [i.to_dict() for i in intervals] == [
        {"day_of_week": 0, "start_minute": 600, "end_minute": 630},
        {"day_of_week": 0, "start_minute": 630, "end_minute": 660},
        {"day_of_week": 1, "start_minute": 630, "end_minute": 660},
        {"day_of_week": 1, "start_minute": 660, "end_minute": 690},
        {"day_of_week": 1, "start_minute": 690, "end_minute": 720},
    ]
