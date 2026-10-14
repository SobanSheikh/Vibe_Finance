export type RiskTolerance = 'low' | 'medium' | 'high'
export type SignalTone = 'positive' | 'warning' | 'negative' | 'info'

export interface Signal {
  dimension: 'price_momentum' | 'volume_anomaly' | 'filing_sentiment' | 'portfolio_fit'
  classification: 'positive' | 'neutral' | 'negative' | 'mixed' | 'insufficient_data'
  confidence: number
  rationale: string
  evidence_ids: string[]
}

export interface Evidence {
  id: string
  title: string
  observation: string
  source_name: string
  source_url: string | null
  page_number: number | null
  is_synthetic: boolean
}

export interface AgentResult {
  agent: 'market_signal' | 'filing_research' | 'portfolio_risk'
  status: 'completed' | 'degraded' | 'failed'
  summary: string
  confidence: number
  signals: Signal[]
  evidence: Evidence[]
  latency_ms: number
}

export interface AnalysisResult {
  session_id: string
  status: 'completed' | 'degraded' | 'failed'
  agents: AgentResult[]
  conflicts: Array<{
    dimension: string
    description: string
    agent_names: string[]
    evidence_ids: string[]
  }>
  recommendation: {
    action: 'increase' | 'hold' | 'monitor' | 'reduce' | 'insufficient_evidence'
    confidence: number
    summary: string
    rationale: string[]
    personalized_risks: string[]
    disclaimer: string
  }
  metrics: {
    end_to_end_latency_ms: number
    evidence_count: number
    portfolio_concentration_score: number | null
  }
}

interface AnalysisJob {
  session_id: string
  status: 'pending' | 'running' | 'completed' | 'degraded' | 'failed'
  result: AnalysisResult | null
  error: string | null
}

const apiUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

const profileIds: Record<RiskTolerance, string> = {
  low: 'a7e99bdf-9459-4806-ada5-a596cf4d453c',
  medium: '9c3bfb92-8815-43f7-8316-851c7f8d8ae9',
  high: '16b24f78-e814-4e72-861e-81f4d241fc9d',
}

const wait = (milliseconds: number) =>
  new Promise<void>((resolve) => window.setTimeout(resolve, milliseconds))

export async function runDemoAnalysis(riskTolerance: RiskTolerance): Promise<AnalysisResult> {
  const createResponse = await fetch(`${apiUrl}/api/analysis`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      company: {
        id: 'ebce53d4-8628-4df2-8aa9-b5f1ddbd94f8',
        symbol: 'RELIANCE',
        exchange: 'NSE',
      },
      investor_profile: {
        id: profileIds[riskTolerance],
        risk_tolerance: riskTolerance,
        investment_horizon_years: riskTolerance === 'low' ? 5 : 8,
      },
      as_of_date: new Date().toISOString().slice(0, 10),
    }),
  })

  if (!createResponse.ok) throw new Error('Could not start the analysis workflow.')
  const accepted = (await createResponse.json()) as { session_id: string }

  for (let attempt = 0; attempt < 30; attempt += 1) {
    const jobResponse = await fetch(`${apiUrl}/api/analysis/${accepted.session_id}`)
    if (!jobResponse.ok) throw new Error('Could not retrieve the analysis result.')
    const job = (await jobResponse.json()) as AnalysisJob

    if ((job.status === 'completed' || job.status === 'degraded') && job.result) {
      return job.result
    }
    if (job.status === 'failed') throw new Error(job.error ?? 'The analysis workflow failed.')
    await wait(300)
  }

  throw new Error('The analysis did not complete within the expected time.')
}
