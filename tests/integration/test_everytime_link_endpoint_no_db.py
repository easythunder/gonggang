from datetime import datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api import submissions as submissions_api
from src.api.submissions import get_submission_service
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


class _FakeSubmissionService:
    def __init__(self):
        self.last_group_id = None
        self.last_nickname = None
        self.last_everytime_url = None
        self.last_intervals = None
        self.updated_group_id = None

    def create_submission_from_everytime_link(
        self,
        group_id: UUID,
        nickname: str,
        everytime_url: str,
        display_unit_minutes: int,
    ):
        parser = EverytimeTimetableParser()
        extractor = IntervalExtractor(display_unit_minutes=display_unit_minutes)

        pairs = parser.parse_from_url(everytime_url)
        intervals = extractor.extract_intervals_from_pairs(pairs)

        self.last_group_id = group_id
        self.last_nickname = nickname
        self.last_everytime_url = everytime_url
        self.last_intervals = intervals

        submission = SimpleNamespace(
            id=uuid4(),
            status=SimpleNamespace(value="SUCCESS"),
            submitted_at=datetime.utcnow(),
        )
        return submission, intervals

    def update_group_last_activity(self, group_id: UUID):
        self.updated_group_id = group_id


def test_everytime_link_endpoint_validates_flow_without_db(monkeypatch):
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
    monkeypatch.setattr(
        submissions_api,
        "_get_group_or_raise",
        lambda group_uuid: SimpleNamespace(display_unit_minutes=30),
    )

    fake_service = _FakeSubmissionService()
    app = FastAPI()
    app.include_router(submissions_api.router)
    app.dependency_overrides[get_submission_service] = lambda: fake_service
    client = TestClient(app)

    group_id = str(uuid4())
    url = "https://everytime.kr/@PWvoLkEGi9jMjDxtePxB"
    response = client.post(
        "/api/submissions/everytime-link",
        data={
            "group_id": group_id,
            "nickname": "endpoint_tester",
            "everytime_url": url,
        },
    )

    assert response.status_code == 201

    payload = response.json()
    assert payload["group_id"] == group_id
    assert payload["nickname"] == "endpoint_tester"
    assert payload["status"] == "SUCCESS"
    assert payload["interval_count"] == 2

    assert str(fake_service.last_group_id) == group_id
    assert fake_service.last_nickname == "endpoint_tester"
    assert fake_service.last_everytime_url == url
    assert len(fake_service.last_intervals) == 2
    assert str(fake_service.updated_group_id) == group_id
