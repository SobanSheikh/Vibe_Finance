import type { Company, InvestorProfile } from './catalog'

export type SignalTone = 'positive' | 'warning' | 'negative' | 'info'

export interface Signal {
  dimension:
    | 'price_momentum'
    | 'volume_anomaly'
    | 'price_volatility'
    | 'filing_sentiment'
    | 'portfolio_fit'
  classification: 'positive' | 'neutral' | 'negative' | 'mixed' | 'insufficient_data'
  confidence: number
  rationale: string
  evidence_ids: string[]
}

export interface Evidence {
  id: string
  kind: 'market_observation' | 'document_excerpt' | 'portfolio_calculation'
  title: string
  observation: string
  source_name: string
  source_url: string | null
  page_number: number | null
  relevance: number | null
  is_synthetic: boolean
}

export interface AgentResult {
  agent: 'market_signal' | 'filing_research' | 'portfolio_risk'
  status: 'completed' | 'degraded' | 'failed'
  summary: string
  confidence: number
  signals: Signal[]
  evidence: Evidence[]
  warnings: string[]
  metrics: Record<string, number>
  latency_ms: number
}

export type AnalysisProgressPhase =
  | 'queued'
  | 'specialists'
  | 'validation'
  | 'synthesis'
  | 'persistence'
  | 'complete'
  | 'failed'

export type AnalysisProgressState = 'queued' | 'running' | 'completed' | 'degraded' | 'failed'

export interface AnalysisProgress {
  phase: AnalysisProgressPhase
  agents: Record<AgentResult['agent'], AnalysisProgressState>
  completed_nodes: string[]
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
    supporting_evidence_ids: string[]
    opposing_evidence_ids: string[]
    personalized_risks: string[]
    disclaimer: string
  }
  metrics: {
    end_to_end_latency_ms: number
    evidence_count: number
    portfolio_concentration_score: number | null
    signal_accuracy_30d: number | null
  }
}

interface AnalysisJob {
  session_id: string
  status: 'pending' | 'running' | 'completed' | 'degraded' | 'failed'
  progress: AnalysisProgress
  result: AnalysisResult | null
  error: string | null
}

export interface AnalysisHistoryItem {
  session_id: string
  status: AnalysisJob['status']
  company_id: string
  profile_id: string
  company_symbol: string
  as_of_date: string
  started_at: string
  completed_at: string | null
  recommendation_action: AnalysisResult['recommendation']['action'] | null
  recommendation_summary: string | null
  recommendation_confidence: number | null
  end_to_end_latency_ms: number | null
  evidence_count: number | null
  portfolio_concentration_score: number | null
  signal_accuracy_30d: number | null
}

const apiUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

const wait = (milliseconds: number) =>
  new Promise<void>((resolve) => window.setTimeout(resolve, milliseconds))

const analysisPollDelay = (attempt: number) => {
  if (attempt < 2) return 500
  if (attempt < 5) return 1000
  return 2000
}

export async function runAnalysis(
  company: Company,
  investorProfile: InvestorProfile,
  onProgress?: (progress: AnalysisProgress) => void,
): Promise<AnalysisResult> {
  const createResponse = await fetch(`${apiUrl}/api/analysis`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      company: {
        id: company.id,
        symbol: company.symbol,
        exchange: company.exchange,
      },
      investor_profile: {
        id: investorProfile.id,
        risk_tolerance: investorProfile.risk_tolerance,
        investment_horizon_years: investorProfile.investment_horizon_years,
      },
      as_of_date: new Date().toISOString().slice(0, 10),
    }),
  })

  if (!createResponse.ok) throw new Error('Could not start the analysis workflow.')
  const accepted = (await createResponse.json()) as { session_id: string }
  onProgress?.({
    phase: 'queued',
    agents: {
      market_signal: 'queued',
      filing_research: 'queued',
      portfolio_risk: 'queued',
    },
    completed_nodes: [],
  })

  for (let attempt = 0; attempt < 24; attempt += 1) {
    await wait(analysisPollDelay(attempt))
    const jobResponse = await fetch(`${apiUrl}/api/analysis/${accepted.session_id}`)
    if (!jobResponse.ok) throw new Error('Could not retrieve the analysis result.')
    const job = (await jobResponse.json()) as AnalysisJob
    onProgress?.(job.progress)

    if ((job.status === 'completed' || job.status === 'degraded') && job.result) {
      return job.result
    }
    if (job.status === 'failed') throw new Error(job.error ?? 'The analysis workflow failed.')
  }

  throw new Error('The analysis did not complete within the expected time.')
}

export async function getAnalysisHistory(filters: {
  companyId?: string
  profileId?: string
  limit?: number
} = {}): Promise<AnalysisHistoryItem[]> {
  const params = new URLSearchParams()
  if (filters.companyId) params.set('company_id', filters.companyId)
  if (filters.profileId) params.set('profile_id', filters.profileId)
  params.set('limit', String(filters.limit ?? 30))
  const response = await fetch(`${apiUrl}/api/analysis?${params}`)
  if (!response.ok) throw new Error('Could not load analysis history.')
  return response.json() as Promise<AnalysisHistoryItem[]>
}

export async function getSavedAnalysis(sessionId: string): Promise<AnalysisResult> {
  const response = await fetch(`${apiUrl}/api/analysis/${sessionId}`)
  if (!response.ok) throw new Error('Could not load the saved analysis.')
  const job = (await response.json()) as AnalysisJob
  if (!job.result) throw new Error('This analysis does not have a completed result yet.')
  return job.result
}
