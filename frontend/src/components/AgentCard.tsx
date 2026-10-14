import type { LucideIcon } from 'lucide-react'

interface AgentCardProps {
  name: string
  summary: string
  confidence: number
  latency: string
  evidenceCount: number
  icon: LucideIcon
}

export function AgentCard({
  name,
  summary,
  confidence,
  latency,
  evidenceCount,
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
          <span>Complete · {latency}</span>
        </header>
        <p>{summary}</p>
        <footer>
          <span>{evidenceCount} evidence points</span>
          <strong>{confidence}% conf.</strong>
        </footer>
      </div>
    </article>
  )
}
