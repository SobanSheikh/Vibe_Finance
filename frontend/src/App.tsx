import { useEffect, useState } from 'react'
import './App.css'

type ApiStatus = 'checking' | 'connected' | 'unavailable'

interface HealthResponse {
  status: 'ok'
  service: string
  environment: string
}

const apiUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

function App() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>('checking')
  const [health, setHealth] = useState<HealthResponse | null>(null)

  useEffect(() => {
    const controller = new AbortController()

    fetch(`${apiUrl}/api/health`, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error('API health check failed')
        return response.json() as Promise<HealthResponse>
      })
      .then((data) => {
        setHealth(data)
        setApiStatus('connected')
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') return
        setApiStatus('unavailable')
      })

    return () => controller.abort()
  }, [])

  return (
    <main className="shell">
      <nav className="nav">
        <a className="brand" href="/" aria-label="VibeFinance home">
          <span className="brand-mark">V</span>
          VibeFinance
        </a>
        <span className={`status status--${apiStatus}`}>
          <span className="status-dot" />
          {apiStatus === 'connected'
            ? 'Intelligence engine online'
            : apiStatus === 'checking'
              ? 'Connecting to engine'
              : 'Engine unavailable'}
        </span>
      </nav>

      <section className="hero">
        <p className="eyebrow">Evidence-first investment intelligence</p>
        <h1>See the signal.<br />Understand the risk.</h1>
        <p className="lede">
          VibeFinance combines market signals, financial filings, and your
          portfolio context into transparent, personalized research.
        </p>
        <div className="actions">
          <button type="button">Open intelligence workspace</button>
          <a href={`${apiUrl}/docs`}>Explore the API</a>
        </div>
      </section>

      <section className="capabilities" aria-label="Core intelligence agents">
        <article>
          <span>01</span>
          <h2>Market signals</h2>
          <p>Momentum, volume anomalies, volatility, and sentiment.</p>
        </article>
        <article>
          <span>02</span>
          <h2>Filing evidence</h2>
          <p>Grounded research with citations back to source documents.</p>
        </article>
        <article>
          <span>03</span>
          <h2>Portfolio fit</h2>
          <p>Risk-aware analysis shaped by exposure and investment horizon.</p>
        </article>
      </section>

      <footer>
        <span>Decision support, not financial advice.</span>
        {health && <span>{health.service} · {health.environment}</span>}
      </footer>
    </main>
  )
}

export default App
