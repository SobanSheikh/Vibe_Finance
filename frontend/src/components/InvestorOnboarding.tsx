import {
  ArrowLeft,
  ArrowRight,
  BriefcaseBusiness,
  Check,
  ShieldCheck,
  UserPlus,
  X,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import {
  createHolding,
  createProfile,
  type Company,
  type Holding,
  type InvestorProfile,
  type RiskTolerance,
} from '../api/catalog'
import { Button } from './Button'
import { CustomSelect } from './CustomSelect'

interface InvestorOnboardingProps {
  companies: Company[]
  onClose: () => void
  onComplete: (
    profile: InvestorProfile,
    holding: Holding | null,
    warning: string | null,
  ) => void
}

const riskOptions = [
  { value: 'low', label: 'Conservative', description: 'Prioritize downside protection' },
  { value: 'medium', label: 'Balanced', description: 'Balance growth and risk' },
  { value: 'high', label: 'Aggressive', description: 'Accept larger price swings' },
]

export function InvestorOnboarding({
  companies,
  onClose,
  onComplete,
}: InvestorOnboardingProps) {
  const [step, setStep] = useState<1 | 2>(1)
  const [name, setName] = useState('')
  const [riskTolerance, setRiskTolerance] = useState<RiskTolerance>('medium')
  const [horizon, setHorizon] = useState('5')
  const [maxPosition, setMaxPosition] = useState('10')
  const [maxSector, setMaxSector] = useState('35')
  const [addPosition, setAddPosition] = useState(false)
  const [companyId, setCompanyId] = useState('')
  const [quantity, setQuantity] = useState('')
  const [averageCost, setAverageCost] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !submitting) onClose()
    }
    document.addEventListener('keydown', closeOnEscape)
    return () => document.removeEventListener('keydown', closeOnEscape)
  }, [onClose, submitting])

  const horizonValue = Number(horizon)
  const maxPositionValue = Number(maxPosition)
  const maxSectorValue = Number(maxSector)
  const policyValid = Boolean(name.trim()) &&
    Number.isFinite(horizonValue) && horizonValue >= 1 && horizonValue <= 100 &&
    Number.isFinite(maxPositionValue) && maxPositionValue > 0 && maxPositionValue <= 100 &&
    Number.isFinite(maxSectorValue) && maxSectorValue > 0 && maxSectorValue <= 100 &&
    maxSectorValue >= maxPositionValue
  const positionValid = !addPosition || (
    Boolean(companyId) && Number(quantity) > 0 && Number(averageCost) >= 0 &&
    quantity !== '' && averageCost !== ''
  )
  const companyOptions = companies.map((company) => ({
    value: company.id,
    label: `${company.symbol} · ${company.exchange}`,
    description: company.name,
  }))

  const submit = async () => {
    if (!policyValid || !positionValid) return
    setSubmitting(true)
    setError(null)
    try {
      const profile = await createProfile({
        name: name.trim(),
        risk_tolerance: riskTolerance,
        investment_horizon_years: horizonValue,
        max_position_percent: maxPositionValue,
        max_sector_percent: maxSectorValue,
      })
      let holding: Holding | null = null
      let warning: string | null = null
      if (addPosition) {
        try {
          holding = await createHolding(profile.id, {
            company_id: companyId,
            quantity: Number(quantity),
            average_cost: Number(averageCost),
          })
        } catch {
          warning = 'The investor was created, but the starting position could not be added.'
        }
      }
      onComplete(profile, holding, warning)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not create the investor profile.')
      setSubmitting(false)
    }
  }

  return (
    <div
      className="onboarding-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !submitting) onClose()
      }}
    >
      <section
        aria-labelledby="onboarding-title"
        aria-modal="true"
        className="onboarding-dialog"
        role="dialog"
      >
        <aside className="onboarding-guide">
          <span className="onboarding-guide__icon"><UserPlus aria-hidden="true" size={21} /></span>
          <span className="eyebrow">Investor onboarding</span>
          <h2 id="onboarding-title">Build a personalized decision policy</h2>
          <p>
            These limits are used by the portfolio-risk agent whenever this investor runs an
            analysis.
          </p>
          <ol>
            <li className={step === 1 ? 'onboarding-step onboarding-step--active' : 'onboarding-step onboarding-step--done'}>
              <span>{step === 2 ? <Check aria-hidden="true" size={13} /> : '1'}</span>
              <div><strong>Risk policy</strong><small>Goals and concentration limits</small></div>
            </li>
            <li className={step === 2 ? 'onboarding-step onboarding-step--active' : 'onboarding-step'}>
              <span>2</span>
              <div><strong>Starting portfolio</strong><small>Optional initial position</small></div>
            </li>
          </ol>
        </aside>

        <div className="onboarding-form">
          <header>
            <div>
              <span>{step === 1 ? 'Step 1 of 2' : 'Step 2 of 2'}</span>
              <h3>{step === 1 ? 'Investor and risk policy' : 'Starting portfolio'}</h3>
            </div>
            <button aria-label="Close onboarding" disabled={submitting} onClick={onClose} type="button">
              <X aria-hidden="true" size={17} />
            </button>
          </header>

          {step === 1 ? (
            <div className="onboarding-fields">
              <label className="portfolio-field portfolio-field--wide">
                <span>Investor name</span>
                <input
                  autoFocus
                  maxLength={120}
                  onChange={(event) => setName(event.target.value)}
                  placeholder="e.g. Maria"
                  value={name}
                />
              </label>
              <div className="portfolio-field portfolio-field--wide">
                <span>Risk tolerance</span>
                <CustomSelect
                  ariaLabel="New investor risk tolerance"
                  onChange={(value) => setRiskTolerance(value as RiskTolerance)}
                  options={riskOptions}
                  value={riskTolerance}
                  variant="field"
                />
              </div>
              <label className="portfolio-field">
                <span>Investment horizon (years)</span>
                <input min="1" max="100" onChange={(event) => setHorizon(event.target.value)} type="number" value={horizon} />
              </label>
              <label className="portfolio-field">
                <span>Maximum position (%)</span>
                <input min="0.01" max="100" onChange={(event) => setMaxPosition(event.target.value)} step="0.01" type="number" value={maxPosition} />
              </label>
              <label className="portfolio-field portfolio-field--wide">
                <span>Maximum sector exposure (%)</span>
                <input min="0.01" max="100" onChange={(event) => setMaxSector(event.target.value)} step="0.01" type="number" value={maxSector} />
                {maxSectorValue < maxPositionValue && <small>Sector limit must be at least the position limit.</small>}
              </label>
            </div>
          ) : (
            <div className="onboarding-position">
              <div className="onboarding-position__intro">
                <span><BriefcaseBusiness aria-hidden="true" size={18} /></span>
                <div>
                  <strong>Does this investor already own a position?</strong>
                  <p>Add one now, or start empty and build the portfolio later.</p>
                </div>
              </div>
              <label className="onboarding-toggle">
                <input checked={addPosition} onChange={(event) => setAddPosition(event.target.checked)} type="checkbox" />
                <span aria-hidden="true" />
                Add a starting position
              </label>
              {addPosition && (
                <div className="onboarding-fields">
                  <div className="portfolio-field portfolio-field--wide">
                    <span>Company</span>
                    <CustomSelect
                      ariaLabel="Starting position company"
                      onChange={setCompanyId}
                      options={companyOptions}
                      placeholder="Choose a company"
                      value={companyId}
                      variant="field"
                    />
                  </div>
                  <label className="portfolio-field">
                    <span>Shares</span>
                    <input min="0.0001" onChange={(event) => setQuantity(event.target.value)} step="any" type="number" value={quantity} />
                  </label>
                  <label className="portfolio-field">
                    <span>Average cost</span>
                    <input min="0" onChange={(event) => setAverageCost(event.target.value)} step="any" type="number" value={averageCost} />
                  </label>
                </div>
              )}
              {!addPosition && (
                <div className="onboarding-empty-position">
                  <ShieldCheck aria-hidden="true" size={18} />
                  <span>The profile will start with zero concentration risk.</span>
                </div>
              )}
            </div>
          )}

          {error && <div className="error-notice" role="alert">{error}</div>}
          <footer>
            {step === 2 ? (
              <Button disabled={submitting} icon={<ArrowLeft aria-hidden="true" size={15} />} onClick={() => setStep(1)} variant="secondary">Back</Button>
            ) : <span />}
            {step === 1 ? (
              <Button disabled={!policyValid} icon={<ArrowRight aria-hidden="true" size={15} />} onClick={() => setStep(2)}>Continue</Button>
            ) : (
              <Button disabled={submitting || !positionValid} icon={<Check aria-hidden="true" size={15} />} onClick={submit}>
                {submitting ? 'Creating investor…' : 'Create investor'}
              </Button>
            )}
          </footer>
        </div>
      </section>
    </div>
  )
}
