from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def request_payload(risk_tolerance: str = "low") -> dict[str, object]:
    return {
        "company": {"id": str(uuid4()), "symbol": "RELIANCE", "exchange": "NSE"},
        "investor_profile": {
            "id": str(uuid4()),
            "risk_tolerance": risk_tolerance,
            "investment_horizon_years": 5,
        },
        "as_of_date": "2026-10-14",
    }


def test_analysis_runs_end_to_end_in_background() -> None:
    create_response = client.post("/api/analysis", json=request_payload())

    assert create_response.status_code == 202
    accepted = create_response.json()
    assert accepted["status"] == "pending"

    job_response = client.get(f"/api/analysis/{accepted['session_id']}")
    assert job_response.status_code == 200
    job = job_response.json()
    assert job["status"] == "completed"
    assert len(job["result"]["agents"]) == 3
    assert len(job["result"]["agents"][0]["signals"]) == 3
    assert job["result"]["metrics"]["evidence_count"] == 5
    assert job["result"]["metrics"]["portfolio_concentration_score"] == 0.41
    assert job["result"]["metrics"]["signal_accuracy_30d"] == 0.64
    assert job["result"]["recommendation"]["action"] == "monitor"
    assert job["result"]["conflicts"]


def test_identical_market_input_is_personalized_by_risk_profile() -> None:
    conservative = client.post("/api/analysis", json=request_payload("low")).json()
    aggressive = client.post("/api/analysis", json=request_payload("high")).json()

    conservative_job = client.get(f"/api/analysis/{conservative['session_id']}").json()
    aggressive_job = client.get(f"/api/analysis/{aggressive['session_id']}").json()

    assert conservative_job["result"]["recommendation"]["action"] == "monitor"
    assert aggressive_job["result"]["recommendation"]["action"] == "hold"


def test_unknown_analysis_returns_404() -> None:
    response = client.get(f"/api/analysis/{uuid4()}")

    assert response.status_code == 404
