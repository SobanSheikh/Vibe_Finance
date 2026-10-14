import { ExternalLink } from 'lucide-react'

interface CitationCardProps {
  document: string
  quote: string
  source: string
}

export function CitationCard({ document, quote, source }: CitationCardProps) {
  return (
    <article className="citation-card">
      <header>
        <span>{document}</span>
        <ExternalLink aria-hidden="true" size={15} />
      </header>
      <blockquote>{quote}</blockquote>
      <p>{source}</p>
    </article>
  )
}
