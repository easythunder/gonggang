import pytest

from src.services.everytime_parser import EverytimeTimetableParser, EverytimeParserError


class _MockHTTPResponse:
  def __init__(self, body: str):
    self._body = body

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc, tb):
    return False

  def read(self):
    return self._body.encode("utf-8")


def test_parse_html_to_pairs_extracts_weekday_subject_blocks():
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
            <td><div class="subject" style="height: 60px; top: 600px;"></div></td>
          </tr>
        </tbody>
      </table>
    </div>
    """

    parser = EverytimeTimetableParser()
    pairs = parser.parse_html_to_pairs(html)

    assert pairs == [
        (0, 600, 660),
        (1, 630, 720),
    ]


def test_validate_everytime_url():
    parser = EverytimeTimetableParser()

    assert parser.validate_everytime_url("https://everytime.kr/@PWvoLkEGi9jMjDxtePxB")
    assert not parser.validate_everytime_url("https://google.com/@PWvoLkEGi9jMjDxtePxB")
    assert not parser.validate_everytime_url("ftp://everytime.kr/@PWvoLkEGi9jMjDxtePxB")


def test_parse_from_url_falls_back_to_api_when_html_has_no_subject(monkeypatch):
    html_without_subject = """
    <html>
      <body>
        <div class="tablebody"></div>
      </body>
    </html>
    """

    xml_from_api = """
    <?xml version="1.0" encoding="UTF-8"?>
    <response>
      <table>
        <subject>
          <time>
            <data day="0" starttime="126" endtime="136" />
          </time>
        </subject>
        <subject>
          <time>
            <data day="2" starttime="150" endtime="160" />
          </time>
        </subject>
      </table>
    </response>
    """

    def _mock_urlopen(request, timeout=5):
        url = request.full_url
        if "api.everytime.kr/find/timetable/table/friend" in url:
            return _MockHTTPResponse(xml_from_api)
        return _MockHTTPResponse(html_without_subject)

    monkeypatch.setattr("src.services.everytime_parser.urlopen", _mock_urlopen)

    parser = EverytimeTimetableParser()
    pairs = parser.parse_from_url("https://everytime.kr/@PWvoLkEGi9jMjDxtePxB")

    assert pairs == [
        (0, 630, 680),
        (2, 750, 800),
    ]


def test_parse_from_url_keeps_html_error_when_api_also_fails(monkeypatch):
    html_without_subject = """
    <html>
      <body>
        <div class="tablebody"></div>
      </body>
    </html>
    """

    empty_api_xml = "<response><table></table></response>"

    def _mock_urlopen(request, timeout=5):
        url = request.full_url
        if "api.everytime.kr/find/timetable/table/friend" in url:
            return _MockHTTPResponse(empty_api_xml)
        return _MockHTTPResponse(html_without_subject)

    monkeypatch.setattr("src.services.everytime_parser.urlopen", _mock_urlopen)

    parser = EverytimeTimetableParser()
    with pytest.raises(EverytimeParserError, match="Timetable columns not found in HTML"):
        parser.parse_from_url("https://everytime.kr/@PWvoLkEGi9jMjDxtePxB")
