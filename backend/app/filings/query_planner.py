from dataclasses import dataclass
from enum import StrEnum

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.analysis.contracts import CompanyRef, InvestorProfileRef, RiskTolerance


class QueryDimension(StrEnum):
    PERFORMANCE = "performance"
    BALANCE_SHEET = "balance_sheet"
    MATERIAL_RISKS = "material_risks"
    OUTLOOK = "outlook"
    COMPANY_SPECIFIC = "company_specific"


@dataclass(frozen=True)
class RetrievalQuery:
    dimension: QueryDimension
    query: str


class QueryExpansion(BaseModel):
    query: str = Field(min_length=10, max_length=500)


class FilingQueryPlanner:
    def __init__(self, chat_model: BaseChatModel | None = None) -> None:
        self._chat_model = chat_model

    def plan(
        self,
        company: CompanyRef,
        profile: InvestorProfileRef,
    ) -> list[RetrievalQuery]:
        symbol = company.symbol.upper()
        queries = [
            RetrievalQuery(
                QueryDimension.PERFORMANCE,
                f"{symbol} revenue growth profitability operating margins and cash flow trends",
            ),
            RetrievalQuery(
                QueryDimension.BALANCE_SHEET,
                f"{symbol} debt leverage liquidity finance costs and capital expenditure",
            ),
            RetrievalQuery(
                QueryDimension.MATERIAL_RISKS,
                f"{symbol} material regulatory operational market and going concern risks",
            ),
            RetrievalQuery(
                QueryDimension.OUTLOOK,
                self._personalized_outlook_query(symbol, profile),
            ),
        ]
        expansion = self._expand(company, profile, queries)
        if expansion and expansion.query.casefold() not in {
            item.query.casefold() for item in queries
        }:
            queries.append(expansion)
        return queries[:5]

    def _expand(
        self,
        company: CompanyRef,
        profile: InvestorProfileRef,
        existing: list[RetrievalQuery],
    ) -> RetrievalQuery | None:
        if self._chat_model is None:
            return None
        structured_model = self._chat_model.with_structured_output(QueryExpansion)
        existing_text = "\n".join(f"- {item.query}" for item in existing)
        try:
            response = structured_model.invoke(
                [
                    SystemMessage(
                        content=(
                            "You generate one precise semantic-search query for company filings. "
                            "Cover a company-specific issue not duplicated by the supplied "
                            "queries. "
                            "Do not make claims, predict returns, or ask for investment advice."
                        )
                    ),
                    HumanMessage(
                        content=(
                            f"Company: {company.symbol} ({company.exchange})\n"
                            f"Investor risk tolerance: {profile.risk_tolerance.value}\n"
                            f"Investment horizon: {profile.investment_horizon_years} years\n"
                            f"Existing queries:\n{existing_text}"
                        )
                    ),
                ]
            )
            parsed = (
                response
                if isinstance(response, QueryExpansion)
                else QueryExpansion.model_validate(response)
            )
        except Exception:
            return None
        return RetrievalQuery(QueryDimension.COMPANY_SPECIFIC, parsed.query.strip())

    @staticmethod
    def _personalized_outlook_query(
        symbol: str,
        profile: InvestorProfileRef,
    ) -> str:
        if profile.risk_tolerance == RiskTolerance.LOW:
            focus = (
                "downside resilience contingent liabilities dividend stability "
                "and risk mitigation"
            )
        elif profile.risk_tolerance == RiskTolerance.HIGH:
            focus = "long-term growth investments expansion catalysts and execution risk"
        else:
            focus = "management outlook growth catalysts downside risks and capital allocation"
        return f"{symbol} {focus} over a {profile.investment_horizon_years}-year horizon"
