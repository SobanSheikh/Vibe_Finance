import { ShieldCheck } from 'lucide-react'

interface RecommendationBannerProps {
  title: string
  detail: string
  confidence: number
}

export function RecommendationBanner({
  title,
  detail,
  confidence,
}: RecommendationBannerProps) {
  return (
    <section className="recommendation">
      <span className="recommendation__icon">
        <ShieldCheck aria-hidden="true" size={22} />
      </span>
      <div className="recommendation__copy">
        <span>Personalized decision support</span>
        <h2>{title}</h2>
        <p>{detail}</p>
      </div>
      <strong className="recommendation__confidence">
        {confidence}%
        <span>Confidence</span>
      </strong>
    </section>
  )
}
