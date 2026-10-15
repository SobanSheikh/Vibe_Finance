import {
  Activity,
  Archive,
  Check,
  Clock3,
  ExternalLink,
  FileSearch,
  GitCompareArrows,
  Search,
  ShieldCheck,
  UserRound,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import {
  getAnalysisHistory,
  getSavedAnalysis,
  type AnalysisHistoryItem,
  type AnalysisResult,
} from '../api/analysis'
import type { Company, InvestorProfile } from '../api/catalog'
import { CustomSelect } from './CustomSelect'

interface ResearchHistoryViewProps {
  apiConnected: boolean
  companies: Company[]
  profiles: InvestorProfile[]
}

const percent = (value: number | null) => value === null ? '—' : `${Math.round(value * 100)}%`

const formatDate = (value: string) => new Intl.DateTimeFormat('en', {
  day: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  month: 'short',
  year: 'numeric',
}).format(new Date(value))

export function ResearchHistoryView({
  apiConnected,
  companies,
  profiles,
}: ResearchHistoryViewProps) {
  const [companyId, setCompanyId] = useState('all')
  const [profileId, setProfileId] = useState('all')
  const [history, setHistory] = useState<AnalysisHistoryItem[]>([])
  const [selectedId, setSelectedId] = useState('')
  const [comparisonIds, setComparisonIds] = useState<string[]>([])
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [detailLoading, setDetailLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const companyNames = useMemo(
    () => new Map(companies.map((company) => [company.id, company.name])),
    [companies],
  )
  const profileNames = useMemo(
    () => new Map(profiles.map((profile) => [profile.id, profile.name])),
    [profiles],
  )
  const compared = comparisonIds
    .map((id) => history.find((item) => item.session_id === id))
    .filter((item): item is AnalysisHistoryItem => Boolean(item))

  useEffect(() => {
    if (!apiConnected) return
    let cancelled = false
    getAnalysisHistory({
      companyId: companyId === 'all' ? undefined : companyId,
      profileId: profileId === 'all' ? undefined : profileId,
    })
      .then((items) => {
        if (cancelled) return
        setHistory(items)
        setComparisonIds([])
        setSelectedId('')
        setAnalysis(null)
      })
      .catch((reason: unknown) => {
        if (!cancelled) setError(reason instanceof Error ? reason.message : 'History failed to load.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [apiConnected, companyId, profileId])

  const openAnalysis = async (sessionId: string) => {
    setSelectedId(sessionId)
    setDetailLoading(true)
    setAnalysis(null)
    setError(null)
    try {
      setAnalysis(await getSavedAnalysis(sessionId))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Saved analysis failed to load.')
    } finally {
      setDetailLoading(false)
    }
  }

  const toggleComparison = (sessionId: string) => {
    setComparisonIds((current) => current.includes(sessionId)
      ? current.filter((id) => id !== sessionId)
      : [...current.slice(-1), sessionId])
  }

  return (
    <div className="research-history">
      <section className="research-toolbar">
        <div className="research-toolbar__copy">
          <span className="research-toolbar__icon"><Archive aria-hidden="true" size={19} /></span>
          <div>
            <span className="eyebrow">Persisted decision trail</span>
            <h2>Reopen evidence without rerunning the workflow</h2>
            <p>Filter saved sessions, inspect their complete evidence, or select two decisions to compare.</p>
          </div>
        </div>
        <div className="research-toolbar__filters">
          <CustomSelect
            ariaLabel="Filter by company"
            disabled={!apiConnected || loading}
            icon={<Search aria-hidden="true" size={15} />}
            onChange={(value) => {
              setLoading(true)
              setError(null)
              setCompanyId(value)
            }}
            options={[
              { value: 'all', label: 'All companies', description: 'Every saved company' },
              ...companies.map((company) => ({
                value: company.id,
                label: `${company.symbol} · ${company.exchange}`,
                description: company.name,
              })),
            ]}
            value={companyId}
          />
          <CustomSelect
            ariaLabel="Filter by investor"
            disabled={!apiConnected || loading}
            icon={<UserRound aria-hidden="true" size={15} />}
            onChange={(value) => {
              setLoading(true)
              setError(null)
              setProfileId(value)
            }}
            options={[
              { value: 'all', label: 'All investors', description: 'Every saved profile' },
              ...profiles.map((profile) => ({
                value: profile.id,
                label: profile.name,
                description: `${profile.risk_tolerance} risk · ${profile.investment_horizon_years}y horizon`,
              })),
            ]}
            value={profileId}
          />
        </div>
      </section>

      {error && <div className="error-notice" role="alert">{error}</div>}

      {compared.length === 2 && (
        <section className="history-comparison">
          <header>
            <GitCompareArrows aria-hidden="true" size={17} />
            <div><strong>Decision comparison</strong><span>Two persisted sessions, no new agent run</span></div>
          </header>
          <div className="history-comparison__grid">
            {compared.map((item) => (
              <article key={item.session_id}>
                <span>{item.company_symbol} · {profileNames.get(item.profile_id) ?? 'Unknown investor'}</span>
                <strong>{item.recommendation_action?.replaceAll('_', ' ') ?? item.status}</strong>
                <p>{item.recommendation_summary ?? 'No completed recommendation.'}</p>
                <dl>
                  <div><dt>Confidence</dt><dd>{percent(item.recommendation_confidence)}</dd></div>
                  <div><dt>Concentration</dt><dd>{percent(item.portfolio_concentration_score)}</dd></div>
                  <div><dt>Evidence</dt><dd>{item.evidence_count ?? '—'}</dd></div>
                </dl>
              </article>
            ))}
          </div>
        </section>
      )}

      <div className="history-layout">
        <section className="history-list" aria-busy={loading}>
          <header className="section-heading">
            <h2>Saved analyses</h2>
            <span>{loading ? 'Loading…' : `${history.length} sessions`}</span>
          </header>
          {!loading && history.length === 0 && (
            <div className="history-empty"><Archive aria-hidden="true" size={22} /><strong>No saved sessions</strong><span>Run intelligence in the Workspace to create one.</span></div>
          )}
          {history.map((item) => {
            const selectedForComparison = comparisonIds.includes(item.session_id)
            return (
              <article className={`history-row${selectedId === item.session_id ? ' history-row--active' : ''}`} key={item.session_id}>
                <button className="history-row__open" onClick={() => openAnalysis(item.session_id)} type="button">
                  <span className="history-row__topline">
                    <strong>{item.company_symbol}</strong>
                    <span className={`history-status history-status--${item.status}`}>{item.status}</span>
                  </span>
                  <span>{profileNames.get(item.profile_id) ?? 'Unknown investor'} · {companyNames.get(item.company_id) ?? item.company_symbol}</span>
                  <b>{item.recommendation_action?.replaceAll('_', ' ') ?? 'Awaiting result'}</b>
                  <small><Clock3 aria-hidden="true" size={12} />{formatDate(item.started_at)}</small>
                </button>
                <button
                  aria-label={`${selectedForComparison ? 'Remove' : 'Add'} ${item.company_symbol} session ${item.session_id.slice(0, 8)} ${selectedForComparison ? 'from' : 'to'} comparison`}
                  className={`history-row__compare${selectedForComparison ? ' history-row__compare--active' : ''}`}
                  disabled={!item.recommendation_action}
                  onClick={() => toggleComparison(item.session_id)}
                  title="Select up to two sessions"
                  type="button"
                >
                  {selectedForComparison ? <Check aria-hidden="true" size={13} /> : <GitCompareArrows aria-hidden="true" size={13} />}
                </button>
              </article>
            )
          })}
        </section>

        <section className="history-detail" aria-busy={detailLoading}>
          {detailLoading ? (
            <div className="history-empty"><Activity aria-hidden="true" size={22} /><strong>Opening saved result…</strong></div>
          ) : analysis ? (
            <>
              <header className="history-detail__hero">
                <div>
                  <span className="eyebrow">Saved recommendation</span>
                  <h2>{analysis.recommendation.summary}</h2>
                  <p>{analysis.recommendation.rationale.join(' ')}</p>
                </div>
                <div><strong>{Math.round(analysis.recommendation.confidence * 100)}%</strong><span>confidence</span></div>
              </header>
              <dl className="history-detail__metrics">
                <div><dt>Decision</dt><dd>{analysis.recommendation.action.replaceAll('_', ' ')}</dd></div>
                <div><dt>Evidence</dt><dd>{analysis.metrics.evidence_count} cited items</dd></div>
                <div><dt>Concentration</dt><dd>{percent(analysis.metrics.portfolio_concentration_score)}</dd></div>
                <div><dt>Execution</dt><dd>{analysis.metrics.end_to_end_latency_ms}ms</dd></div>
              </dl>
              <section className="history-detail__section">
                <header><ShieldCheck aria-hidden="true" size={16} /><h3>Agent record</h3></header>
                <div className="history-agent-list">
                  {analysis.agents.map((agent) => (
                    <article key={agent.agent}>
                      <div><strong>{agent.agent.replaceAll('_', ' ')}</strong><span>{agent.status} · {agent.latency_ms}ms</span></div>
                      <p>{agent.summary}</p>
                    </article>
                  ))}
                </div>
              </section>
              <section className="history-detail__section">
                <header><FileSearch aria-hidden="true" size={16} /><h3>Source evidence</h3></header>
                <div className="history-evidence-list">
                  {analysis.agents.flatMap((agent) => agent.evidence).map((item) => (
                    <article key={`${item.id}-${item.title}`}>
                      <div><strong>{item.title}</strong><span>{item.source_name}</span></div>
                      <p>{item.observation}</p>
                      {item.source_url && <a href={item.source_url} rel="noreferrer" target="_blank">Open source <ExternalLink aria-hidden="true" size={12} /></a>}
                    </article>
                  ))}
                </div>
              </section>
            </>
          ) : (
            <div className="history-empty"><Search aria-hidden="true" size={22} /><strong>Select a saved analysis</strong><span>Its recommendation, agent outputs, and cited evidence will appear here.</span></div>
          )}
        </section>
      </div>
    </div>
  )
}
