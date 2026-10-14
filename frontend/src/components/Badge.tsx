import type { ReactNode } from 'react'

interface BadgeProps {
  children: ReactNode
  tone?: 'positive' | 'warning' | 'negative' | 'info' | 'neutral'
}

export function Badge({ children, tone = 'neutral' }: BadgeProps) {
  return (
    <span className={`badge badge--${tone}`}>
      <span className="badge__dot" aria-hidden="true" />
      {children}
    </span>
  )
}
