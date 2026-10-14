from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.catalog.contracts import (
    CompanyResponse,
    HoldingCreate,
    HoldingResponse,
    HoldingUpdate,
    ProfileCreate,
    ProfileResponse,
    ProfileUpdate,
    WatchlistCreate,
    WatchlistResponse,
)
from app.db.models import Company, Holding, InvestorProfile, WatchlistItem
from app.db.session import get_db

router = APIRouter(prefix="/api", tags=["catalog"])


def _profile_or_404(session: Session, profile_id: UUID) -> InvestorProfile:
    profile = session.get(InvestorProfile, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Investor profile not found")
    return profile


def _company_or_404(session: Session, company_id: UUID) -> Company:
    company = session.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


@router.get("/companies", response_model=list[CompanyResponse])
def list_companies(
    query: str | None = Query(default=None, alias="q", max_length=100),
    session: Session = Depends(get_db),
) -> list[Company]:
    statement = select(Company).order_by(Company.symbol).limit(50)
    if query:
        pattern = f"%{query.strip()}%"
        statement = statement.where(
            or_(Company.symbol.ilike(pattern), Company.name.ilike(pattern))
        )
    return list(session.scalars(statement))


@router.get("/companies/{company_id}", response_model=CompanyResponse)
def get_company(company_id: UUID, session: Session = Depends(get_db)) -> Company:
    return _company_or_404(session, company_id)


@router.get("/profiles", response_model=list[ProfileResponse])
def list_profiles(session: Session = Depends(get_db)) -> list[InvestorProfile]:
    return list(session.scalars(select(InvestorProfile).order_by(InvestorProfile.name)))


@router.post("/profiles", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
def create_profile(payload: ProfileCreate, session: Session = Depends(get_db)) -> InvestorProfile:
    profile = InvestorProfile(**payload.model_dump(), is_demo=False)
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile


@router.get("/profiles/{profile_id}", response_model=ProfileResponse)
def get_profile(profile_id: UUID, session: Session = Depends(get_db)) -> InvestorProfile:
    return _profile_or_404(session, profile_id)


@router.patch("/profiles/{profile_id}", response_model=ProfileResponse)
def update_profile(
    profile_id: UUID,
    payload: ProfileUpdate,
    session: Session = Depends(get_db),
) -> InvestorProfile:
    profile = _profile_or_404(session, profile_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    session.commit()
    session.refresh(profile)
    return profile


@router.delete("/profiles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(profile_id: UUID, session: Session = Depends(get_db)) -> Response:
    profile = _profile_or_404(session, profile_id)
    session.delete(profile)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/profiles/{profile_id}/holdings", response_model=list[HoldingResponse])
def list_holdings(profile_id: UUID, session: Session = Depends(get_db)) -> list[HoldingResponse]:
    _profile_or_404(session, profile_id)
    rows = session.execute(
        select(Holding, Company)
        .join(Company, Company.id == Holding.company_id)
        .where(Holding.profile_id == profile_id)
        .order_by(Company.symbol)
    )
    return [
        HoldingResponse(
            id=holding.id,
            profile_id=holding.profile_id,
            company=CompanyResponse.model_validate(company),
            quantity=holding.quantity,
            average_cost=holding.average_cost,
        )
        for holding, company in rows
    ]


@router.post(
    "/profiles/{profile_id}/holdings",
    response_model=HoldingResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_holding(
    profile_id: UUID,
    payload: HoldingCreate,
    session: Session = Depends(get_db),
) -> HoldingResponse:
    _profile_or_404(session, profile_id)
    company = _company_or_404(session, payload.company_id)
    holding = Holding(profile_id=profile_id, **payload.model_dump())
    session.add(holding)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="Holding already exists") from exc
    session.refresh(holding)
    return HoldingResponse(
        id=holding.id,
        profile_id=profile_id,
        company=CompanyResponse.model_validate(company),
        quantity=holding.quantity,
        average_cost=holding.average_cost,
    )


@router.patch(
    "/profiles/{profile_id}/holdings/{holding_id}", response_model=HoldingResponse
)
def update_holding(
    profile_id: UUID,
    holding_id: UUID,
    payload: HoldingUpdate,
    session: Session = Depends(get_db),
) -> HoldingResponse:
    row = session.execute(
        select(Holding, Company)
        .join(Company, Company.id == Holding.company_id)
        .where(Holding.id == holding_id, Holding.profile_id == profile_id)
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Holding not found")
    holding, company = row
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(holding, field, value)
    session.commit()
    session.refresh(holding)
    return HoldingResponse(
        id=holding.id,
        profile_id=profile_id,
        company=CompanyResponse.model_validate(company),
        quantity=holding.quantity,
        average_cost=holding.average_cost,
    )


@router.delete(
    "/profiles/{profile_id}/holdings/{holding_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_holding(
    profile_id: UUID,
    holding_id: UUID,
    session: Session = Depends(get_db),
) -> Response:
    holding = session.scalar(
        select(Holding).where(Holding.id == holding_id, Holding.profile_id == profile_id)
    )
    if holding is None:
        raise HTTPException(status_code=404, detail="Holding not found")
    session.delete(holding)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/profiles/{profile_id}/watchlist", response_model=list[WatchlistResponse])
def list_watchlist(
    profile_id: UUID, session: Session = Depends(get_db)
) -> list[WatchlistResponse]:
    _profile_or_404(session, profile_id)
    rows = session.execute(
        select(WatchlistItem, Company)
        .join(Company, Company.id == WatchlistItem.company_id)
        .where(WatchlistItem.profile_id == profile_id)
        .order_by(Company.symbol)
    )
    return [
        WatchlistResponse(
            id=item.id,
            profile_id=item.profile_id,
            company=CompanyResponse.model_validate(company),
        )
        for item, company in rows
    ]


@router.post(
    "/profiles/{profile_id}/watchlist",
    response_model=WatchlistResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_watchlist_item(
    profile_id: UUID,
    payload: WatchlistCreate,
    session: Session = Depends(get_db),
) -> WatchlistResponse:
    _profile_or_404(session, profile_id)
    company = _company_or_404(session, payload.company_id)
    item = WatchlistItem(profile_id=profile_id, company_id=payload.company_id)
    session.add(item)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="Company is already on the watchlist") from exc
    session.refresh(item)
    return WatchlistResponse(
        id=item.id,
        profile_id=profile_id,
        company=CompanyResponse.model_validate(company),
    )


@router.delete(
    "/profiles/{profile_id}/watchlist/{item_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_watchlist_item(
    profile_id: UUID,
    item_id: UUID,
    session: Session = Depends(get_db),
) -> Response:
    item = session.scalar(
        select(WatchlistItem).where(
            WatchlistItem.id == item_id,
            WatchlistItem.profile_id == profile_id,
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Watchlist item not found")
    session.delete(item)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
