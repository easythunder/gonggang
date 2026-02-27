from src.services.everytime_parser import EverytimeTimetableParser


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
