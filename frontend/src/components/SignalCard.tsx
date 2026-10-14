import type { LucideIcon } from 'lucide-react'

interface SignalCardProps {
  label: string
  value: string
  evidence: string
  confidence: number
  tone: 'positive' | 'warning' | 'negative' | 'info'
  icon: LucideIcon
}

export function SignalCard({
  label,
  value,
  evidence,
  confidence,
  tone,
  icon: Icon,
}: SignalCardProps) {
  return (
    <article className={`signal-card signal-card--${tone}`}>
      <header className="signal-card__header">
        <span>{label}</span>
        <Icon aria-hidden="true" size={18} strokeWidth={1.8} />
      </header>
      <strong className="signal-card__value">{value}</strong>
      <span className="signal-card__evidence">{evidence}</span>
      <footer className="signal-card__footer">
        <span>Confidence</span>
        <strong>{confidence}%</strong>
      </footer>
    </article>
  )
}
