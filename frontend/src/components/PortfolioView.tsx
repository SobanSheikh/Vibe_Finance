import {
  BriefcaseBusiness,
  Eye,
  Plus,
  Save,
  ShieldCheck,
  Trash2,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import {
  createHolding,
  createWatchlistItem,
  deleteHolding,
  deleteWatchlistItem,
  getHoldings,
  getWatchlist,
  updateHolding,
  updateProfile,
  type Company,
  type Holding,
  type InvestorProfile,
  type RiskTolerance,
  type WatchlistItem,
} from '../api/catalog'
import { Button } from './Button'
import { CustomSelect } from './CustomSelect'

interface PortfolioViewProps {
  apiConnected: boolean
  companies: Company[]
  onHoldingsChanged: (holdings: Holding[]) => void
  onProfileChanged: (profile: InvestorProfile) => void
  profile: InvestorProfile | undefined
}

const riskOptions = [
  { value: 'low', label: 'Conservative', description: 'Prioritize downside protection' },
  { value: 'medium', label: 'Balanced', description: 'Balance growth and risk' },
  { value: 'high', label: 'Aggressive', description: 'Accept larger price swings' },
]

function HoldingEditor({
  holding,
  onDeleted,
  onSaved,
  profileId,
}: {
  holding: Holding
  onDeleted: (holdingId: string) => void
  onSaved: (holding: Holding) => void
  profileId: string
}) {
  const [quantity, setQuantity] = useState(String(holding.quantity))
  const [averageCost, setAverageCost] = useState(String(holding.average_cost))
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const numericQuantity = Number(quantity)
  const numericAverageCost = Number(averageCost)
  const changed = numericQuantity !== Number(holding.quantity) ||
    numericAverageCost !== Number(holding.average_cost)

  const save = async () => {
    if (
      quantity === '' || averageCost === '' ||
      !Number.isFinite(numericQuantity) || !Number.isFinite(numericAverageCost)
    ) return
    setBusy(true)
    setError(null)
    try {
      onSaved(await updateHolding(profileId, holding.id, {
        quantity: numericQuantity,
        average_cost: numericAverageCost,
      }))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not update holding.')
    } finally {
      setBusy(false)
    }
  }

  const remove = async () => {
    if (!window.confirm(`Remove ${holding.company.symbol} from this portfolio?`)) return
    setBusy(true)
    setError(null)
    try {
      await deleteHolding(profileId, holding.id)
      onDeleted(holding.id)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not remove holding.')
      setBusy(false)
    }
  }

  return (
    <div className="portfolio-holding-row">
      <div className="portfolio-holding-row__company">
        <strong>{holding.company.symbol}</strong>
        <span>{holding.company.name}</span>
      </div>
      <label>
        <span>Shares</span>
        <input
          disabled={busy}
          min="0"
          onChange={(event) => setQuantity(event.target.value)}
          step="any"
          type="number"
          value={quantity}
        />
      </label>
      <label>
        <span>Average cost</span>
        <input
          disabled={busy}
          min="0"
          onChange={(event) => setAverageCost(event.target.value)}
          step="any"
          type="number"
          value={averageCost}
        />
      </label>
      <div className="portfolio-holding-row__value">
        <span>Cost basis</span>
        <strong>{(numericQuantity * numericAverageCost).toLocaleString(undefined, {
          maximumFractionDigits: 2,
        })}</strong>
      </div>
      <div className="portfolio-holding-row__actions">
        <button
          aria-label={`Save ${holding.company.symbol} holding`}
          disabled={
            busy || !changed || quantity === '' || averageCost === '' ||
            numericQuantity < 0 || numericAverageCost < 0
          }
          onClick={save}
          title="Save holding"
          type="button"
        >
          <Save aria-hidden="true" size={14} />
        </button>
        <button
          aria-label={`Remove ${holding.company.symbol} holding`}
          className="danger-action"
          disabled={busy}
          onClick={remove}
          title="Remove holding"
          type="button"
        >
          <Trash2 aria-hidden="true" size={14} />
        </button>
      </div>
      {error && <small className="portfolio-row-error">{error}</small>}
    </div>
  )
}

export function PortfolioView({
  apiConnected,
  companies,
  onHoldingsChanged,
  onProfileChanged,
  profile,
}: PortfolioViewProps) {
  const [holdings, setHoldings] = useState<Holding[]>([])
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([])
  const [loading, setLoading] = useState(Boolean(profile))
  const [savingProfile, setSavingProfile] = useState(false)
  const [addingHolding, setAddingHolding] = useState(false)
  const [addingWatchlist, setAddingWatchlist] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [name, setName] = useState(profile?.name ?? '')
  const [riskTolerance, setRiskTolerance] = useState<RiskTolerance>(
    profile?.risk_tolerance ?? 'medium',
  )
  const [horizon, setHorizon] = useState(String(profile?.investment_horizon_years ?? 5))
  const [maxPosition, setMaxPosition] = useState(String(profile?.max_position_percent ?? 10))
  const [maxSector, setMaxSector] = useState(String(profile?.max_sector_percent ?? 35))
  const [newHoldingCompanyId, setNewHoldingCompanyId] = useState('')
  const [newQuantity, setNewQuantity] = useState('')
  const [newAverageCost, setNewAverageCost] = useState('')
  const [newWatchlistCompanyId, setNewWatchlistCompanyId] = useState('')

  useEffect(() => {
    if (!profile) return
    let cancelled = false
    Promise.all([getHoldings(profile.id), getWatchlist(profile.id)])
      .then(([holdingRows, watchlistRows]) => {
        if (cancelled) return
        setHoldings(holdingRows)
        setWatchlist(watchlistRows)
        onHoldingsChanged(holdingRows)
      })
      .catch((reason: unknown) => {
        if (!cancelled) {
          setError(reason instanceof Error ? reason.message : 'Could not load portfolio data.')
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [profile, onHoldingsChanged])

  const holdingCompanyIds = useMemo(
    () => new Set(holdings.map((holding) => holding.company.id)),
    [holdings],
  )
  const watchlistCompanyIds = useMemo(
    () => new Set(watchlist.map((item) => item.company.id)),
    [watchlist],
  )
  const holdingCompanyOptions = companies
    .filter((company) => !holdingCompanyIds.has(company.id))
    .map((company) => ({
      value: company.id,
      label: `${company.symbol} · ${company.exchange}`,
      description: company.name,
    }))
  const watchlistCompanyOptions = companies
    .filter((company) => !watchlistCompanyIds.has(company.id))
    .map((company) => ({
      value: company.id,
      label: `${company.symbol} · ${company.exchange}`,
      description: company.name,
    }))
  const holdingSelection = newHoldingCompanyId || holdingCompanyOptions[0]?.value || ''
  const watchlistSelection = newWatchlistCompanyId || watchlistCompanyOptions[0]?.value || ''
  const totalCostBasis = holdings.reduce(
    (total, holding) => total + Number(holding.quantity) * Number(holding.average_cost),
    0,
  )

  const replaceHolding = (updated: Holding) => {
    const next = holdings.map((holding) => holding.id === updated.id ? updated : holding)
    setHoldings(next)
    onHoldingsChanged(next)
    setNotice(`${updated.company.symbol} holding updated.`)
  }

  const removeHolding = (holdingId: string) => {
    const next = holdings.filter((holding) => holding.id !== holdingId)
    setHoldings(next)
    onHoldingsChanged(next)
    setNotice('Holding removed.')
  }

  const saveProfile = async () => {
    if (!profile) return
    setSavingProfile(true)
    setError(null)
    setNotice(null)
    try {
      const updated = await updateProfile(profile.id, {
        name: name.trim(),
        risk_tolerance: riskTolerance,
        investment_horizon_years: Number(horizon),
        max_position_percent: Number(maxPosition),
        max_sector_percent: Number(maxSector),
      })
      onProfileChanged(updated)
      setNotice('Investor policy saved. New analyses will use these limits.')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not update the profile.')
    } finally {
      setSavingProfile(false)
    }
  }

  const addHolding = async () => {
    if (!profile || !holdingSelection) return
    setAddingHolding(true)
    setError(null)
    setNotice(null)
    try {
      const holding = await createHolding(profile.id, {
        company_id: holdingSelection,
        quantity: Number(newQuantity),
        average_cost: Number(newAverageCost),
      })
      const next = [...holdings, holding].sort((left, right) =>
        left.company.symbol.localeCompare(right.company.symbol))
      setHoldings(next)
      onHoldingsChanged(next)
      setNewHoldingCompanyId('')
      setNewQuantity('')
      setNewAverageCost('')
      setNotice(`${holding.company.symbol} added to the portfolio.`)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not add the holding.')
    } finally {
      setAddingHolding(false)
    }
  }

  const addWatchlistItem = async () => {
    if (!profile || !watchlistSelection) return
    setAddingWatchlist(true)
    setError(null)
    setNotice(null)
    try {
      const item = await createWatchlistItem(profile.id, watchlistSelection)
      setWatchlist((current) => [...current, item].sort((left, right) =>
        left.company.symbol.localeCompare(right.company.symbol)))
      setNewWatchlistCompanyId('')
      setNotice(`${item.company.symbol} added to the watchlist.`)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not update the watchlist.')
    } finally {
      setAddingWatchlist(false)
    }
  }

  const removeWatchlistItem = async (item: WatchlistItem) => {
    if (!profile) return
    try {
      await deleteWatchlistItem(profile.id, item.id)
      setWatchlist((current) => current.filter((row) => row.id !== item.id))
      setNotice(`${item.company.symbol} removed from the watchlist.`)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not update the watchlist.')
    }
  }

  if (!profile) {
    return <p className="empty-state">Select an investor profile to manage its portfolio.</p>
  }

  return (
    <div className="portfolio-manager">
      {error && <div className="error-notice" role="alert">{error}</div>}
      {notice && <div className="portfolio-notice" role="status">{notice}</div>}

      <section className="portfolio-summary-grid">
        <article>
          <BriefcaseBusiness aria-hidden="true" size={17} />
          <span>Recorded holdings</span>
          <strong>{holdings.length}</strong>
        </article>
        <article>
          <ShieldCheck aria-hidden="true" size={17} />
          <span>Portfolio cost basis</span>
          <strong>{totalCostBasis.toLocaleString(undefined, { maximumFractionDigits: 0 })}</strong>
        </article>
        <article>
          <Eye aria-hidden="true" size={17} />
          <span>Watchlist companies</span>
          <strong>{watchlist.length}</strong>
        </article>
      </section>

      <div className="portfolio-manager__grid">
        <section className="portfolio-panel portfolio-policy">
          <header>
            <div>
              <span className="eyebrow">Investor policy</span>
              <h2>Risk profile and concentration limits</h2>
            </div>
            <span>{profile.is_demo ? 'Demo profile' : 'Custom profile'}</span>
          </header>
          <div className="portfolio-form-grid">
            <label className="portfolio-field portfolio-field--wide">
              <span>Profile name</span>
              <input onChange={(event) => setName(event.target.value)} value={name} />
            </label>
            <div className="portfolio-field">
              <span>Risk tolerance</span>
              <CustomSelect
                ariaLabel="Risk tolerance"
                onChange={(value) => setRiskTolerance(value as RiskTolerance)}
                options={riskOptions}
                value={riskTolerance}
                variant="field"
              />
            </div>
            <label className="portfolio-field">
              <span>Investment horizon (years)</span>
              <input min="1" onChange={(event) => setHorizon(event.target.value)} type="number" value={horizon} />
            </label>
            <label className="portfolio-field">
              <span>Maximum position (%)</span>
              <input min="0.01" onChange={(event) => setMaxPosition(event.target.value)} step="0.01" type="number" value={maxPosition} />
            </label>
            <label className="portfolio-field">
              <span>Maximum sector (%)</span>
              <input min="0.01" onChange={(event) => setMaxSector(event.target.value)} step="0.01" type="number" value={maxSector} />
            </label>
          </div>
          <Button
            disabled={savingProfile || !apiConnected || !name.trim()}
            icon={<Save aria-hidden="true" size={15} />}
            onClick={saveProfile}
          >
            {savingProfile ? 'Saving policy…' : 'Save investor policy'}
          </Button>
        </section>

        <section className="portfolio-panel portfolio-watchlist">
          <header>
            <div>
              <span className="eyebrow">Monitoring</span>
              <h2>Research watchlist</h2>
            </div>
            <span>{watchlist.length} tracked</span>
          </header>
          <div className="portfolio-watchlist__add">
            <CustomSelect
              ariaLabel="Company to watch"
              disabled={addingWatchlist || !apiConnected}
              onChange={setNewWatchlistCompanyId}
              options={watchlistCompanyOptions}
              placeholder="All companies tracked"
              value={watchlistSelection}
              variant="field"
            />
            <button
              aria-label="Add company to watchlist"
              disabled={!watchlistSelection || addingWatchlist}
              onClick={addWatchlistItem}
              type="button"
            >
              <Plus aria-hidden="true" size={15} />
            </button>
          </div>
          <div className="portfolio-watchlist__items">
            {watchlist.map((item) => (
              <div key={item.id}>
                <span><strong>{item.company.symbol}</strong>{item.company.name}</span>
                <button
                  aria-label={`Remove ${item.company.symbol} from watchlist`}
                  onClick={() => removeWatchlistItem(item)}
                  type="button"
                >
                  <Trash2 aria-hidden="true" size={13} />
                </button>
              </div>
            ))}
            {!watchlist.length && !loading && <p>No companies are being monitored yet.</p>}
          </div>
        </section>
      </div>

      <section className="portfolio-panel portfolio-holdings">
        <header>
          <div>
            <span className="eyebrow">Portfolio ledger</span>
            <h2>Holdings used by the risk agent</h2>
          </div>
          <span>{loading ? 'Loading…' : `${holdings.length} positions`}</span>
        </header>
        <div className="portfolio-holdings__add">
          <CustomSelect
            ariaLabel="Company to add"
            disabled={addingHolding || !apiConnected}
            onChange={setNewHoldingCompanyId}
            options={holdingCompanyOptions}
            placeholder="All companies held"
            value={holdingSelection}
            variant="field"
          />
          <label>
            <span>Shares</span>
            <input min="0" onChange={(event) => setNewQuantity(event.target.value)} step="any" type="number" value={newQuantity} />
          </label>
          <label>
            <span>Average cost</span>
            <input min="0" onChange={(event) => setNewAverageCost(event.target.value)} step="any" type="number" value={newAverageCost} />
          </label>
          <Button
            disabled={
              addingHolding || !holdingSelection || !newQuantity || !newAverageCost ||
              Number(newQuantity) < 0 || Number(newAverageCost) < 0
            }
            icon={<Plus aria-hidden="true" size={15} />}
            onClick={addHolding}
          >
            {addingHolding ? 'Adding…' : 'Add holding'}
          </Button>
        </div>
        <div className="portfolio-holdings__list">
          {holdings.map((holding) => (
            <HoldingEditor
              holding={holding}
              key={holding.id}
              onDeleted={removeHolding}
              onSaved={replaceHolding}
              profileId={profile.id}
            />
          ))}
          {!holdings.length && !loading && <p className="empty-state">No holdings recorded for this investor.</p>}
        </div>
      </section>
    </div>
  )
}
