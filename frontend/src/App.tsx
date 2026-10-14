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
import { useEffect, useState } from 'react'
import './App.css'
import { AgentCard } from './components/AgentCard'
import { Button } from './components/Button'
import { CitationCard } from './components/CitationCard'
import { RecommendationBanner } from './components/RecommendationBanner'
import { SignalCard } from './components/SignalCard'

type ApiStatus = 'checking' | 'connected' | 'unavailable'

interface HealthResponse {
  status: 'ok'
  service: string
  environment: string
}

const apiUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

const navigation = [
  { label: 'Workspace', icon: LayoutDashboard, active: true },
  { label: 'Research', icon: Search },
  { label: 'Portfolio', icon: BriefcaseBusiness },
  { label: 'Evaluation', icon: Activity },
]

const conflicts = [
  { label: 'Momentum', value: 'Positive', tone: 'positive' },
  { label: 'Volume', value: 'Positive', tone: 'positive' },
  { label: 'Fundamentals', value: 'Mixed', tone: 'warning' },
  { label: 'Portfolio fit', value: 'High risk', tone: 'negative' },
] as const

function App() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>('checking')

  useEffect(() => {
    const controller = new AbortController()

    fetch(`${apiUrl}/api/health`, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error('API health check failed')
        return response.json() as Promise<HealthResponse>
      })
      .then(() => setApiStatus('connected'))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') return
        setApiStatus('unavailable')
      })

    return () => controller.abort()
  }, [])

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
          <span>Market data current</span>
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
            <button className="selector" type="button">
              <UserRound aria-hidden="true" size={15} />
              <span>Ananya · Conservative</span>
              <ChevronDown aria-hidden="true" size={14} />
            </button>
            <Button icon={<Sparkles aria-hidden="true" size={16} />}>Run intelligence</Button>
          </div>
        </header>

        <RecommendationBanner
          confidence={72}
          detail="Positive market momentum is outweighed by your existing sector concentration and short investment horizon."
          title="Monitor the position — avoid increasing exposure"
        />

        <div className="workspace-grid">
          <div className="analysis-column">
            <section className="section-block">
              <header className="section-heading">
                <h2>Market signals</h2>
                <span>As of 14 Oct 2026 · 15:30 IST</span>
              </header>
              <div className="signal-grid">
                <SignalCard
                  confidence={81}
                  evidence="30-day return +8.42%"
                  icon={TrendingUp}
                  label="Price momentum"
                  tone="positive"
                  value="Bullish"
                />
                <SignalCard
                  confidence={74}
                  evidence="Z-score +2.31"
                  icon={Waves}
                  label="Volume anomaly"
                  tone="warning"
                  value="Elevated"
                />
                <SignalCard
                  confidence={68}
                  evidence="6 positive · 4 risk"
                  icon={FileSearch}
                  label="Filing sentiment"
                  tone="warning"
                  value="Mixed"
                />
              </div>
            </section>

            <section className="section-block">
              <header className="section-heading">
                <h2>Agent synthesis</h2>
                <span className="positive-text">Parallel execution · 2.4s total</span>
              </header>
              <div className="agent-list">
                <AgentCard
                  confidence={78}
                  evidenceCount={4}
                  icon={TrendingUp}
                  latency="1.2s"
                  name="Market Signal Agent"
                  summary="Momentum and unusual volume support a positive signal, with volatility limiting confidence."
                />
                <AgentCard
                  confidence={71}
                  evidenceCount={5}
                  icon={FileSearch}
                  latency="2.1s"
                  name="Filing Research Agent"
                  summary="Revenue resilience is offset by higher finance costs and leverage disclosed in the latest filing."
                />
                <AgentCard
                  confidence={88}
                  evidenceCount={4}
                  icon={ShieldAlert}
                  latency="0.8s"
                  name="Portfolio Risk Agent"
                  summary="Existing energy exposure exceeds the profile limit; increasing this position would deepen concentration."
                />
              </div>
            </section>
          </div>

          <aside className="evidence-column">
            <section className="section-block">
              <header className="section-heading">
                <h2>Source evidence</h2>
                <span className="info-text">4 sources</span>
              </header>
              <CitationCard
                document="Annual report · FY2025"
                quote="Revenue growth remained resilient while finance costs increased during the reporting period."
                source="Reliance Industries · p.84 · Borrowings"
              />
            </section>

            <section className="conflict-card">
              <h3>Evidence conflict map</h3>
              <div className="conflict-list">
                {conflicts.map((item) => (
                  <div className="conflict-row" key={item.label}>
                    <span>{item.label}</span>
                    <strong className={`tone-${item.tone}`}>
                      <span className="conflict-row__dot" />
                      {item.value}
                    </strong>
                  </div>
                ))}
              </div>
            </section>

            <p className="disclaimer">
              Decision support only. VibeFinance does not provide financial advice.
            </p>
          </aside>
        </div>
      </main>
    </div>
  )
}

export default App
