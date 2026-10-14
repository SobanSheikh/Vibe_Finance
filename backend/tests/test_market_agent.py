from datetime import date, timedelta
from uuid import uuid4

from app.analysis.contracts import (
    AgentStatus,
    AnalysisRequest,
    CompanyRef,
    InvestorProfileRef,
    RiskTolerance,
    SignalClassification,
)
from app.analysis.state import AnalysisState
from app.market.agent import build_market_agent
from app.market.models import MarketBar, MarketDataError


class StubProvider:
    name = "Test market provider"

    def history(self, symbol: str, exchange: str) -> list[MarketBar]:
        assert (symbol, exchange) == ("RELIANCE", "NSE")
        first_day = date(2026, 1, 1)
        bars = [
            MarketBar(first_day + timedelta(days=index), 100 + index, 1_000 + index)
            for index in range(31)
        ]
        bars[-1] = MarketBar(bars[-1].trading_date, 140, 5_000)
        return bars


class FailingProvider:
    name = "Unavailable provider"

    def history(self, symbol: str, exchange: str) -> list[MarketBar]:
        raise MarketDataError("provider timed out")


def state() -> AnalysisState:
    return {
        "request": AnalysisRequest(
            company=CompanyRef(id=uuid4(), symbol="RELIANCE", exchange="NSE"),
            investor_profile=InvestorProfileRef(
                id=uuid4(), risk_tolerance=RiskTolerance.LOW, investment_horizon_years=5
            ),
            as_of_date=date(2026, 10, 14),
        )
    }


def test_market_agent_returns_cited_deterministic_signals() -> None:
    result = build_market_agent(StubProvider())(state())["market_result"]

    assert result.status == AgentStatus.COMPLETED
    assert len(result.signals) == 2
    assert result.signals[0].classification == SignalClassification.POSITIVE
    assert result.signals[1].classification == SignalClassification.POSITIVE
    assert {item.source_name for item in result.evidence} == {"Test market provider"}
    assert all(not item.is_synthetic for item in result.evidence)


def test_market_agent_degrades_without_uncited_output() -> None:
    result = build_market_agent(FailingProvider())(state())["market_result"]

    assert result.status == AgentStatus.DEGRADED
    assert result.signals == []
    assert result.evidence == []
    assert result.confidence == 0
