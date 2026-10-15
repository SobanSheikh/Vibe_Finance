import type { LucideIcon } from 'lucide-react'

interface AgentCardProps {
  name: string
  summary: string
  confidence: number
  latency: string
  evidenceCount: number
  status: 'completed' | 'degraded' | 'failed'
  warnings: string[]
  icon: LucideIcon
}

export function AgentCard({
  name,
  summary,
  confidence,
  latency,
  evidenceCount,
  status,
  warnings,
  icon: Icon,
}: AgentCardProps) {
  return (
    <article className="agent-card">
      <div className="agent-card__icon">
        <Icon aria-hidden="true" size={17} />
      </div>
      <div className="agent-card__body">
        <header>
          <strong>{name}</strong>
          <span className={`agent-card__status agent-card__status--${status}`}>
            {status} · {latency}
          </span>
        </header>
        <p>{summary}</p>
        {warnings.length > 0 && (
          <ul className="agent-card__warnings">
            {warnings.map((warning) => <li key={warning}>{warning}</li>)}
          </ul>
        )}
        <footer>
          <span>{evidenceCount} evidence points</span>
          <strong>{confidence}% conf.</strong>
        </footer>
      </div>
    </article>
  )
}
