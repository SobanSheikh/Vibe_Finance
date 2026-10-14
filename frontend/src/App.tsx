import {
  Activity,
  BriefcaseBusiness,
  Building2,
  ChevronDown,
  FileSearch,
  LayoutDashboard,
  Search,
  ShieldAlert,
  Sparkles,
  TrendingUp,
  UserRound,
  Waves,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import './App.css'
import {
  runDemoAnalysis,
  type AnalysisResult,
  type RiskTolerance,
  type Signal,
  type SignalTone,
} from './api/analysis'
import { AgentCard } from './components/AgentCard'
import { Button } from './components/Button'
import { CitationCard } from './components/CitationCard'
import { RecommendationBanner } from './components/RecommendationBanner'
import { SignalCard } from './components/SignalCard'

type ApiStatus = 'checking' | 'connected' | 'unavailable'
type RunStatus = 'idle' | 'running' | 'complete' | 'error'

const apiUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const navigation = [
  { label: 'Workspace', icon: LayoutDashboard, active: true },
  { label: 'Research', icon: Search },
  { label: 'Portfolio', icon: BriefcaseBusiness },
  { label: 'Evaluation', icon: Activity },
]

const profileLabels: Record<RiskTolerance, string> = {
  low: 'Ananya · Conservative',
  medium: 'Mira · Balanced',
  high: 'Aarav · Aggressive',
}

const agentPresentation = {
  market_signal: { name: 'Market Signal Agent', icon: TrendingUp },
  filing_research: { name: 'Filing Research Agent', icon: FileSearch },
  portfolio_risk: { name: 'Portfolio Risk Agent', icon: ShieldAlert },
} as const

const signalPresentation = {
  price_momentum: { label: 'Price momentum', icon: TrendingUp },
  volume_anomaly: { label: 'Volume anomaly', icon: Waves },
  filing_sentiment: { label: 'Filing sentiment', icon: FileSearch },
  portfolio_fit: { label: 'Portfolio fit', icon: ShieldAlert },
} as const

function signalTone(classification: Signal['classification']): SignalTone {
  if (classification === 'positive') return 'positive'
  if (classification === 'negative') return 'negative'
  if (classification === 'mixed') return 'warning'
  return 'info'
}

function signalValue(classification: Signal['classification']): string {
  const labels: Record<Signal['classification'], string> = {
    positive: 'Positive',
    neutral: 'Neutral',
    negative: 'High risk',
    mixed: 'Mixed',
    insufficient_data: 'Unavailable',
  }
  return labels[classification]
}

function App() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>('checking')
  const [runStatus, setRunStatus] = useState<RunStatus>('idle')
  const [riskTolerance, setRiskTolerance] = useState<RiskTolerance>('low')
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    fetch(`${apiUrl}/api/health`, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error('API health check failed')
        return response.json()
      })
      .then(() => setApiStatus('connected'))
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === 'AbortError') return
        setApiStatus('unavailable')
      })
    return () => controller.abort()
  }, [])

  const signals = useMemo(
    () => analysis?.agents.flatMap((agent) => agent.signals) ?? [],
    [analysis],
  )
  const evidence = useMemo(
    () => analysis?.agents.flatMap((agent) => agent.evidence) ?? [],
    [analysis],
  )
  const hasLiveMarketEvidence = evidence.some(
    (item) => !item.is_synthetic && item.source_name === 'Yahoo Finance',
  )

  const toggleProfile = () => {
    setRiskTolerance((current) => (current === 'low' ? 'high' : 'low'))
    setAnalysis(null)
    setRunStatus('idle')
    setError(null)
  }

  const runAnalysis = async () => {
    setRunStatus('running')
    setError(null)
    try {
      setAnalysis(await runDemoAnalysis(riskTolerance))
      setRunStatus('complete')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The analysis workflow failed.')
      setRunStatus('error')
    }
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="/" aria-label="VibeFinance home">
          <span className="brand__mark">V</span>
          <span>VibeFinance</span>
        </a>
        <nav className="sidebar__nav" aria-label="Primary navigation">
          {navigation.map(({ label, icon: Icon, active }) => (
            <a className={active ? 'nav-item nav-item--active' : 'nav-item'} href="#" key={label}>
              <Icon aria-hidden="true" size={17} />
              <span>{label}</span>
            </a>
          ))}
        </nav>
        <section className="system-card" aria-label="System status">
          <header>
            <span>System</span>
            <span className={`status-dot status-dot--${apiStatus}`} />
          </header>
          <strong>
            {apiStatus === 'connected'
              ? '3 agents ready'
              : apiStatus === 'checking'
                ? 'Connecting to engine'
                : 'Engine unavailable'}
          </strong>
          <span>Deterministic demo adapters</span>
        </section>
      </aside>

      <main className="workspace">
        <header className="workspace-header">
          <div>
            <span className="eyebrow">Intelligence workspace</span>
            <h1>Research decision room</h1>
          </div>
          <div className="workspace-header__actions">
            <button className="selector" type="button">
              <Building2 aria-hidden="true" size={15} />
              <span>Reliance · NSE</span>
              <ChevronDown aria-hidden="true" size={14} />
            </button>
            <button
              className="selector"
              onClick={toggleProfile}
              title="Switch demo investor profile"
              type="button"
            >
              <UserRound aria-hidden="true" size={15} />
              <span>{profileLabels[riskTolerance]}</span>
              <ChevronDown aria-hidden="true" size={14} />
            </button>
            <Button
              disabled={runStatus === 'running' || apiStatus !== 'connected'}
              icon={<Sparkles aria-hidden="true" size={16} />}
              onClick={runAnalysis}
            >
              {runStatus === 'running' ? 'Running agents…' : 'Run intelligence'}
            </Button>
          </div>
        </header>

        <div className="demo-notice" role="note">
          {hasLiveMarketEvidence
            ? 'Hybrid mode: market observations are live; filings and portfolio holdings remain synthetic.'
            : 'Demo mode: market observations, filing excerpts, and portfolio holdings are synthetic.'}
        </div>
        {error && <div className="error-notice" role="alert">{error}</div>}

        <RecommendationBanner
          confidence={Math.round((analysis?.recommendation.confidence ?? 0) * 100)}
          detail={
            analysis?.recommendation.rationale.join(' ') ??
            'Choose a demo profile and run the three-agent workflow to generate a recommendation.'
          }
          title={analysis?.recommendation.summary ?? 'Ready for evidence-backed analysis'}
        />

        <div className="workspace-grid">
          <div className="analysis-column">
            <section className="section-block">
              <header className="section-heading">
                <h2>Market signals</h2>
                <span>{analysis ? `${signals.length} classified dimensions` : 'Awaiting analysis'}</span>
              </header>
              <div className="signal-grid">
                {signals.length ? signals.map((signal) => {
                  const presentation = signalPresentation[signal.dimension]
                  return (
                    <SignalCard
                      confidence={Math.round(signal.confidence * 100)}
                      evidence={signal.rationale}
                      icon={presentation.icon}
                      key={signal.dimension}
                      label={presentation.label}
                      tone={signalTone(signal.classification)}
                      value={signalValue(signal.classification)}
                    />
                  )
                }) : <p className="empty-state">Signals will appear after the workflow completes.</p>}
              </div>
            </section>

            <section className="section-block">
              <header className="section-heading">
                <h2>Agent synthesis</h2>
                <span className="positive-text">
                  {analysis
                    ? `Parallel execution · ${analysis.metrics.end_to_end_latency_ms}ms`
                    : 'Three-agent fan-out ready'}
                </span>
              </header>
              <div className="agent-list">
                {analysis ? analysis.agents.map((agent) => {
                  const presentation = agentPresentation[agent.agent]
                  return (
                    <AgentCard
                      confidence={Math.round(agent.confidence * 100)}
                      evidenceCount={agent.evidence.length}
                      icon={presentation.icon}
                      key={agent.agent}
                      latency={`${agent.latency_ms}ms`}
                      name={presentation.name}
                      summary={agent.summary}
                    />
                  )
                }) : <p className="empty-state">Agent outputs will appear here.</p>}
              </div>
            </section>
          </div>

          <aside className="evidence-column">
            <section className="section-block">
              <header className="section-heading">
                <h2>Source evidence</h2>
                <span className="info-text">{evidence.length} sources</span>
              </header>
              <div className="citation-list">
                {evidence.length ? evidence.map((item) => (
                  <CitationCard
                    document={item.title}
                    key={item.id}
                    quote={item.observation}
                    source={`${item.source_name}${item.page_number ? ` · p.${item.page_number}` : ''}`}
                  />
                )) : <p className="empty-state">Cited evidence will appear here.</p>}
              </div>
            </section>

            <section className="conflict-card">
              <h3>Evidence conflict map</h3>
              <div className="conflict-list">
                {signals.length ? signals.map((signal) => (
                  <div className="conflict-row" key={signal.dimension}>
                    <span>{signalPresentation[signal.dimension].label}</span>
                    <strong className={`tone-${signalTone(signal.classification)}`}>
                      <span className="conflict-row__dot" />
                      {signalValue(signal.classification)}
                    </strong>
                  </div>
                )) : <p className="empty-state">No evidence has been compared yet.</p>}
              </div>
            </section>

            {analysis && (
              <section className="metrics-card">
                <h3>Session evaluation</h3>
                <span>{analysis.metrics.evidence_count} evidence items</span>
                <span>
                  {Math.round((analysis.metrics.portfolio_concentration_score ?? 0) * 100)}% concentration risk
                </span>
                <span>{analysis.conflicts.length} detected conflict</span>
              </section>
            )}

            <p className="disclaimer">
              {analysis?.recommendation.disclaimer ??
                'Decision support only. VibeFinance does not provide financial advice.'}
            </p>
          </aside>
        </div>
      </main>
    </div>
  )
}

export default App
