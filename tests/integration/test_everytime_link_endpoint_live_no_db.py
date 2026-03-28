from datetime import datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api import submissions as submissions_api
from src.api.submissions import get_submission_service


LIVE_EVERYTIME_URL = "https://everytime.kr/@PWvoLkEGi9jMjDxtePxB"


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
        from src.services.everytime_parser import EverytimeTimetableParser
        from src.services.interval_extractor import IntervalExtractor

        parser = EverytimeTimetableParser()
        extractor = IntervalExtractor(display_unit_minutes=display_unit_minutes)

        pairs = parser.parse_from_url(everytime_url, timeout_seconds=10)
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


@pytest.mark.integration
def test_everytime_link_endpoint_live_network_no_db(monkeypatch):
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
    response = client.post(
        "/api/submissions/everytime-link",
        data={
            "group_id": group_id,
            "nickname": "live_network_tester",
            "everytime_url": LIVE_EVERYTIME_URL,
        },
    )

    assert response.status_code == 201

    payload = response.json()
    assert payload["group_id"] == group_id
    assert payload["nickname"] == "live_network_tester"
    assert payload["status"] == "SUCCESS"
    assert payload["interval_count"] > 0

    assert str(fake_service.last_group_id) == group_id
    assert fake_service.last_nickname == "live_network_tester"
    assert fake_service.last_everytime_url == LIVE_EVERYTIME_URL
    assert len(fake_service.last_intervals) > 0
    assert str(fake_service.updated_group_id) == group_id
