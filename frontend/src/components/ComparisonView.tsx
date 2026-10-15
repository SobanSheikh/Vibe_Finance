import {
  Activity,
  CheckCircle2,
  GitCompareArrows,
  ShieldAlert,
  Sparkles,
  TriangleAlert,
  UserRound,
} from 'lucide-react'
import { useState } from 'react'
import { runAnalysis, type AnalysisResult } from '../api/analysis'
import type { Company, InvestorProfile, RiskTolerance } from '../api/catalog'
import { Button } from './Button'
import { CustomSelect } from './CustomSelect'

interface ComparisonViewProps {
  apiConnected: boolean
  company: Company | undefined
  initialProfileId: string
  profiles: InvestorProfile[]
}

interface ComparisonResults {
  companyId: string
  left: AnalysisResult
  right: AnalysisResult
}

const riskLabels: Record<RiskTolerance, string> = {
  low: 'Conservative',
  medium: 'Balanced',
  high: 'Aggressive',
}

function marketFingerprint(result: AnalysisResult): string | null {
  const market = result.agents.find((agent) => agent.agent === 'market_signal')
  if (!market?.evidence.length) return null
  return JSON.stringify(
    market.evidence.map((item) => ({
      observation: item.observation,
      source: item.source_name,
      title: item.title,
    })),
  )
}

function portfolioClassification(result: AnalysisResult): string | null {
  return result.agents
    .flatMap((agent) => agent.signals)
    .find((signal) => signal.dimension === 'portfolio_fit')?.classification ?? null
}

function comparisonProfileOptions(profiles: InvestorProfile[]) {
  return profiles.map((profile) => ({
    value: profile.id,
    label: `${profile.name} · ${riskLabels[profile.risk_tolerance]}`,
    description: `${profile.investment_horizon_years}y horizon · ${Number(profile.max_position_percent)}% max position`,
  }))
}

function formatMetric(value: number | null, suffix: string): string {
  return value === null ? 'Unavailable' : `${Math.round(value * 100)}% ${suffix}`
}

function ResultCard({
  profile,
  result,
}: {
  profile: InvestorProfile
  result: AnalysisResult
}) {
  const portfolioSignal = result.agents
    .flatMap((agent) => agent.signals)
    .find((signal) => signal.dimension === 'portfolio_fit')
  const completedAgents = result.agents.filter((agent) => agent.status === 'completed').length

  return (
    <article className="comparison-result">
      <header className="comparison-result__header">
        <div>
          <span className="comparison-result__avatar"><UserRound aria-hidden="true" size={16} /></span>
          <div>
            <strong>{profile.name}</strong>
            <span>{riskLabels[profile.risk_tolerance]} · {profile.investment_horizon_years}y horizon</span>
          </div>
        </div>
        <span className={`comparison-result__status comparison-result__status--${result.status}`}>
          {result.status}
        </span>
      </header>

      <div className="comparison-result__decision">
        <span>{result.recommendation.action.replaceAll('_', ' ')}</span>
        <strong>{Math.round(result.recommendation.confidence * 100)}%</strong>
        <small>Recommendation confidence</small>
      </div>

      <h3>{result.recommendation.summary}</h3>
      <ul className="comparison-result__rationale">
        {result.recommendation.rationale.slice(0, 3).map((reason) => (
          <li key={reason}>{reason}</li>
        ))}
      </ul>

      <section className="comparison-result__portfolio">
        <div>
          <ShieldAlert aria-hidden="true" size={14} />
          <strong>Portfolio fit</strong>
        </div>
        <span>{portfolioSignal?.classification.replaceAll('_', ' ') ?? 'Unavailable'}</span>
        <p>{portfolioSignal?.rationale ?? 'No portfolio-fit signal was returned.'}</p>
      </section>

      <dl className="comparison-result__metrics">
        <div>
          <dt>Concentration</dt>
          <dd>{formatMetric(result.metrics.portfolio_concentration_score, 'risk')}</dd>
        </div>
        <div>
          <dt>Signal accuracy</dt>
          <dd>{formatMetric(result.metrics.signal_accuracy_30d, 'historical')}</dd>
        </div>
        <div>
          <dt>Evidence</dt>
          <dd>{result.metrics.evidence_count} cited items</dd>
        </div>
        <div>
          <dt>Execution</dt>
          <dd>{result.metrics.end_to_end_latency_ms}ms · {completedAgents}/3 agents</dd>
        </div>
      </dl>

      <footer>
        <span>{result.conflicts.length} conflicts</span>
        <span>Session {result.session_id.slice(0, 8)}</span>
      </footer>
    </article>
  )
}

export function ComparisonView({
  apiConnected,
  company,
  initialProfileId,
  profiles,
}: ComparisonViewProps) {
  const [leftSelection, setLeftSelection] = useState('')
  const [rightSelection, setRightSelection] = useState('')
  const [results, setResults] = useState<ComparisonResults | null>(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const profileOptions = comparisonProfileOptions(profiles)
  const leftId = leftSelection || initialProfileId || profiles[0]?.id || ''
  const rightId = rightSelection || profiles.find((profile) => profile.id !== leftId)?.id || ''
  const leftProfile = profiles.find((profile) => profile.id === leftId)
  const rightProfile = profiles.find((profile) => profile.id === rightId)
  const currentResults = results?.companyId === company?.id ? results : null
  const leftMarketFingerprint = currentResults ? marketFingerprint(currentResults.left) : null
  const rightMarketFingerprint = currentResults ? marketFingerprint(currentResults.right) : null
  const marketEvidenceState = leftMarketFingerprint === null || rightMarketFingerprint === null
    ? 'unavailable'
    : leftMarketFingerprint === rightMarketFingerprint
      ? 'matching'
      : 'changed'
  const personalized = currentResults
    ? currentResults.left.recommendation.action !== currentResults.right.recommendation.action ||
      currentResults.left.metrics.portfolio_concentration_score !==
        currentResults.right.metrics.portfolio_concentration_score ||
      portfolioClassification(currentResults.left) !== portfolioClassification(currentResults.right)
    : false

  const runComparison = async () => {
    if (!company || !leftProfile || !rightProfile || leftProfile.id === rightProfile.id) return
    setRunning(true)
    setError(null)
    setResults(null)
    try {
      const [left, right] = await Promise.all([
        runAnalysis(company, leftProfile),
        runAnalysis(company, rightProfile),
      ])
      setResults({ companyId: company.id, left, right })
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Profile comparison failed.')
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="comparison-view">
      <section className="comparison-setup">
        <div className="comparison-setup__copy">
          <span className="comparison-setup__icon"><GitCompareArrows aria-hidden="true" size={19} /></span>
          <div>
            <span className="eyebrow">Personalization proof</span>
            <h2>Compare the same company across two investor profiles</h2>
            <p>
              Both workflows launch together. Market and filing evidence stay company-specific;
              portfolio limits and risk tolerance change the final decision.
            </p>
          </div>
        </div>
        <div className="comparison-setup__controls">
          <CustomSelect
            ariaLabel="First investor profile"
            disabled={running || !apiConnected}
            icon={<UserRound aria-hidden="true" size={15} />}
            onChange={(value) => {
              setLeftSelection(value)
              if (value === rightId) setRightSelection('')
              setResults(null)
            }}
            options={profileOptions}
            placeholder="First profile"
            value={leftId}
          />
          <span className="comparison-setup__versus">VS</span>
          <CustomSelect
            ariaLabel="Second investor profile"
            disabled={running || !apiConnected}
            icon={<UserRound aria-hidden="true" size={15} />}
            onChange={(value) => {
              setRightSelection(value)
              setResults(null)
            }}
            options={profileOptions}
            placeholder="Second profile"
            value={rightId}
          />
          <Button
            disabled={
              running || !apiConnected || !company || !leftProfile || !rightProfile ||
              leftProfile.id === rightProfile.id
            }
            icon={<Sparkles aria-hidden="true" size={16} />}
            onClick={runComparison}
          >
            {running ? 'Running six agents…' : 'Run comparison'}
          </Button>
        </div>
      </section>

      {error && <div className="error-notice" role="alert">{error}</div>}

      {running && (
        <section className="comparison-running" aria-live="polite">
          <Activity aria-hidden="true" size={18} />
          <div>
            <strong>Two analysis graphs are running in parallel</strong>
            <span>Market, filing, and portfolio specialists are executing for each profile.</span>
          </div>
        </section>
      )}

      {currentResults && leftProfile && rightProfile && (
        <>
          <section className={`comparison-proof comparison-proof--${marketEvidenceState === 'matching' && personalized ? 'success' : 'warning'}`}>
            {marketEvidenceState === 'matching' && personalized
              ? <CheckCircle2 aria-hidden="true" size={18} />
              : <TriangleAlert aria-hidden="true" size={18} />}
            <div>
              <strong>
                {marketEvidenceState === 'unavailable'
                  ? 'Market evidence was unavailable for this comparison'
                  : marketEvidenceState === 'matching'
                    ? 'Matching market evidence confirmed'
                    : 'Market observations changed between workflows'}
              </strong>
              <span>
                {marketEvidenceState === 'unavailable'
                  ? 'Portfolio and filing-grounded outcomes remain comparable, but identical market evidence could not be verified.'
                  : marketEvidenceState === 'changed'
                    ? 'Outcome differences cannot be attributed only to investor context; rerun when both workflows use matching market observations.'
                    : personalized
                      ? 'The recommendation or portfolio outcome changed because the investor context changed.'
                      : 'These profiles produced the same decision for this company; their risk metrics remain visible below.'}
              </span>
            </div>
          </section>
          <div className="comparison-results">
            <ResultCard profile={leftProfile} result={currentResults.left} />
            <ResultCard profile={rightProfile} result={currentResults.right} />
          </div>
        </>
      )}

      {!running && !currentResults && (
        <section className="comparison-empty">
          <GitCompareArrows aria-hidden="true" size={24} />
          <strong>Ready for a controlled personalization comparison</strong>
          <span>Select two different profiles and run both workflows against {company?.symbol ?? 'one company'}.</span>
        </section>
      )}
    </div>
  )
}
