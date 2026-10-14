from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import RiskTolerance


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class CompanyResponse(ApiModel):
    id: UUID
    symbol: str
    name: str
    sector: str
    exchange: str


class ProfileCreate(ApiModel):
    name: str = Field(min_length=1, max_length=120)
    risk_tolerance: RiskTolerance
    investment_horizon_years: int = Field(gt=0, le=100)
    max_position_percent: Decimal = Field(gt=0, le=100)
    max_sector_percent: Decimal = Field(gt=0, le=100)


class ProfileUpdate(ApiModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    risk_tolerance: RiskTolerance | None = None
    investment_horizon_years: int | None = Field(default=None, gt=0, le=100)
    max_position_percent: Decimal | None = Field(default=None, gt=0, le=100)
    max_sector_percent: Decimal | None = Field(default=None, gt=0, le=100)


class ProfileResponse(ProfileCreate):
    id: UUID
    is_demo: bool


class HoldingCreate(ApiModel):
    company_id: UUID
    quantity: Decimal = Field(ge=0)
    average_cost: Decimal = Field(ge=0)


class HoldingUpdate(ApiModel):
    quantity: Decimal | None = Field(default=None, ge=0)
    average_cost: Decimal | None = Field(default=None, ge=0)


class HoldingResponse(ApiModel):
    id: UUID
    profile_id: UUID
    company: CompanyResponse
    quantity: Decimal
    average_cost: Decimal


class WatchlistCreate(ApiModel):
    company_id: UUID


class WatchlistResponse(ApiModel):
    id: UUID
    profile_id: UUID
    company: CompanyResponse
