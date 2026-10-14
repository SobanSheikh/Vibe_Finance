import { ExternalLink } from 'lucide-react'

interface CitationCardProps {
  document: string
  quote: string
  source: string
  sourceUrl?: string | null
}

export function CitationCard({ document, quote, source, sourceUrl }: CitationCardProps) {
  return (
    <article className="citation-card">
      <header>
        <span>{document}</span>
        {sourceUrl ? (
          <a
            aria-label={`Open source for ${document}`}
            href={sourceUrl}
            rel="noreferrer"
            target="_blank"
          >
            <ExternalLink aria-hidden="true" size={15} />
          </a>
        ) : <ExternalLink aria-hidden="true" size={15} />}
      </header>
      <blockquote>{quote}</blockquote>
      <p>{source}</p>
    </article>
  )
}
