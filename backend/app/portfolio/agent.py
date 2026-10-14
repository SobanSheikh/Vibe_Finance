from collections.abc import Callable
from decimal import Decimal
from math import ceil
from time import perf_counter

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.analysis.contracts import (
    AgentName,
    AgentResult,
    AgentStatus,
    Evidence,
    EvidenceKind,
    Signal,
    SignalClassification,
    SignalDimension,
)
from app.analysis.state import AnalysisState
from app.db.models import Company, Holding, InvestorProfile


def build_portfolio_agent(
    session_factory: sessionmaker[Session],
    fallback: Callable[[AnalysisState], dict[str, AgentResult]] | None = None,
) -> Callable[[AnalysisState], dict[str, AgentResult]]:
    def portfolio_agent(state: AnalysisState) -> dict[str, AgentResult]:
        started_at = perf_counter()
        request = state["request"]

        try:
            with session_factory() as session:
                profile = session.get(InvestorProfile, request.investor_profile.id)
                company = session.get(Company, request.company.id)
                rows = session.execute(
                    select(Holding, Company)
                    .join(Company, Company.id == Holding.company_id)
                    .where(Holding.profile_id == request.investor_profile.id)
                ).all()
        except SQLAlchemyError:
            if fallback is not None:
                return fallback(state)
            return _unavailable_result(
                started_at,
                "The portfolio ledger is temporarily unavailable.",
            )

        if profile is None or company is None:
            return _unavailable_result(
                started_at,
                "The selected company or investor profile was not found in the portfolio ledger.",
            )

        values = [
            (holding, holding_company, holding.quantity * holding.average_cost)
            for holding, holding_company in rows
        ]
        total_value = sum((value for _, _, value in values), start=Decimal(0))
        if total_value <= 0:
            return _unavailable_result(
                started_at,
                "The selected profile has no valued holdings to calculate concentration.",
            )

        sector_value = sum(
            (value for _, held_company, value in values if held_company.sector == company.sector),
            start=Decimal(0),
        )
        position_value = sum(
            (value for holding, _, value in values if holding.company_id == company.id),
            start=Decimal(0),
        )
        sector_percent = float(sector_value / total_value * 100)
        position_percent = float(position_value / total_value * 100)
        sector_limit = float(profile.max_sector_percent)
        position_limit = float(profile.max_position_percent)
        breaches = []
        if sector_percent > sector_limit:
            breaches.append("sector")
        if position_percent > position_limit:
            breaches.append("position")
        classification = (
            SignalClassification.NEGATIVE if breaches else SignalClassification.NEUTRAL
        )
        observation = (
            f"{company.sector} represents {sector_percent:.1f}% of portfolio cost basis "
            f"(limit {sector_limit:.1f}%); {company.symbol} represents "
            f"{position_percent:.1f}% (limit {position_limit:.1f}%)."
        )
        evidence = Evidence(
            id=f"portfolio-{profile.id}-{company.id}-concentration",
            kind=EvidenceKind.PORTFOLIO_CALCULATION,
            title="Portfolio concentration from recorded holdings",
            observation=observation,
            source_name="VibeFinance portfolio ledger",
        )
        summary = (
            f"Recorded holdings exceed the profile's {', '.join(breaches)} concentration limit."
            if breaches
            else "Recorded holdings remain within this profile's concentration limits."
        )
        return {
            "portfolio_result": AgentResult(
                agent=AgentName.PORTFOLIO,
                status=AgentStatus.COMPLETED,
                summary=summary,
                confidence=0.92,
                signals=[
                    Signal(
                        dimension=SignalDimension.PORTFOLIO_FIT,
                        classification=classification,
                        confidence=0.92,
                        rationale=observation,
                        evidence_ids=[evidence.id],
                    )
                ],
                evidence=[evidence],
                latency_ms=ceil((perf_counter() - started_at) * 1000),
            )
        }

    return portfolio_agent


def _unavailable_result(started_at: float, reason: str) -> dict[str, AgentResult]:
    evidence = Evidence(
        id="portfolio-insufficient-data",
        kind=EvidenceKind.PORTFOLIO_CALCULATION,
        title="Portfolio concentration unavailable",
        observation=reason,
        source_name="VibeFinance portfolio ledger",
    )
    return {
        "portfolio_result": AgentResult(
            agent=AgentName.PORTFOLIO,
            status=AgentStatus.DEGRADED,
            summary=reason,
            confidence=0.2,
            signals=[
                Signal(
                    dimension=SignalDimension.PORTFOLIO_FIT,
                    classification=SignalClassification.INSUFFICIENT_DATA,
                    confidence=0.2,
                    rationale=reason,
                    evidence_ids=[evidence.id],
                )
            ],
            evidence=[evidence],
            warnings=[reason],
            latency_ms=ceil((perf_counter() - started_at) * 1000),
        )
    }
