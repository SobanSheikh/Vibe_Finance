import {
  Braces,
  Check,
  ChevronRight,
  Database,
  Gauge,
  GitMerge,
  LoaderCircle,
  Sparkles,
  TriangleAlert,
  UsersRound,
  type LucideIcon,
} from 'lucide-react'
import type {
  AnalysisProgress,
  AnalysisProgressPhase,
  AnalysisProgressState,
  AnalysisResult,
} from '../api/analysis'

type RunStatus = 'idle' | 'running' | 'complete' | 'error'
type StageState = 'ready' | 'active' | 'queued' | 'complete' | 'warning' | 'error'

interface WorkflowRailProps {
  analysis: AnalysisResult | null
  companyLabel: string
  progress: AnalysisProgress | null
  profileLabel: string
  runStatus: RunStatus
}

interface Stage {
  agents?: Array<{ label: string; state: AnalysisProgressState }>
  icon: LucideIcon
  label: string
  meta: string
  state: StageState
}

const phaseStage: Record<AnalysisProgressPhase, number> = {
  queued: 0,
  specialists: 1,
  validation: 2,
  synthesis: 3,
  persistence: 4,
  complete: 5,
  failed: -1,
}

function stageState(
  runStatus: RunStatus,
  stageIndex: number,
  degraded = false,
  progress: AnalysisProgress | null = null,
): StageState {
  if (progress) {
    if (progress.phase === 'failed') return stageIndex <= 1 ? 'error' : 'queued'
    const activeStage = phaseStage[progress.phase]
    if (activeStage === 5 || stageIndex < activeStage) return degraded ? 'warning' : 'complete'
    if (stageIndex === activeStage) return 'active'
    return 'queued'
  }
  if (runStatus === 'error') return stageIndex < 2 ? 'error' : 'queued'
  if (runStatus === 'complete') return degraded ? 'warning' : 'complete'
  if (runStatus === 'running') {
    if (stageIndex === 0) return 'complete'
    if (stageIndex === 1) return 'active'
    return 'queued'
  }
  return stageIndex === 0 ? 'ready' : 'queued'
}

function StateIcon({ state }: { state: StageState }) {
  if (state === 'complete') return <Check aria-hidden="true" size={11} />
  if (state === 'active') return <LoaderCircle aria-hidden="true" size={11} />
  if (state === 'warning' || state === 'error') {
    return <TriangleAlert aria-hidden="true" size={11} />
  }
  return <span aria-hidden="true" />
}

export function WorkflowRail({
  analysis,
  companyLabel,
  progress,
  profileLabel,
  runStatus,
}: WorkflowRailProps) {
  const degraded = analysis?.status === 'degraded'
  const degradedAgents = analysis?.agents.filter((agent) => agent.status !== 'completed').length ?? 0
  const maxAgentLatency = analysis
    ? Math.max(...analysis.agents.map((agent) => agent.latency_ms))
    : null
  const agentProgress = progress ? [
    { label: 'Market', state: progress.agents.market_signal },
    { label: 'Filings', state: progress.agents.filing_research },
    { label: 'Portfolio', state: progress.agents.portfolio_risk },
  ] : undefined
  const completedAgentCount = agentProgress?.filter(
    (agent) => ['completed', 'degraded', 'failed'].includes(agent.state),
  ).length ?? 0
  const stages: Stage[] = [
    {
      icon: Braces,
      label: 'Input snapshot',
      meta: companyLabel && profileLabel ? `${companyLabel} · ${profileLabel}` : 'Select research inputs',
      state: stageState(runStatus, 0, false, progress),
    },
    {
      icon: UsersRound,
      label: 'Parallel specialists',
      meta: maxAgentLatency === null
        ? progress
          ? `${completedAgentCount}/3 specialists returned`
          : 'Market · Filing · Portfolio'
        : `3 agents · slowest ${maxAgentLatency}ms`,
      state: stageState(runStatus, 1, degradedAgents > 0, progress),
      agents: agentProgress,
    },
    {
      icon: GitMerge,
      label: 'Validate evidence',
      meta: analysis
        ? `${analysis.metrics.evidence_count} items · ${analysis.conflicts.length} conflicts`
        : 'Citations and conflicts',
      state: stageState(runStatus, 2, degraded, progress),
    },
    {
      icon: Sparkles,
      label: 'Synthesize decision',
      meta: analysis
        ? `${analysis.recommendation.action} · ${Math.round(analysis.recommendation.confidence * 100)}% confidence`
        : 'Personalized recommendation',
      state: stageState(runStatus, 3, degraded, progress),
    },
    {
      icon: Database,
      label: 'Persist and measure',
      meta: analysis
        ? `${analysis.metrics.end_to_end_latency_ms}ms end to end`
        : 'Metrics and audit trail',
      state: stageState(runStatus, 4, degraded, progress),
    },
  ]
  const overallLabel = runStatus === 'running'
    ? 'Workflow executing'
    : runStatus === 'error'
      ? 'Workflow failed'
      : analysis?.status === 'degraded'
        ? 'Completed with limitations'
        : analysis
          ? 'Workflow completed'
          : 'Ready to run'

  return (
    <section
      aria-label="Analysis workflow"
      aria-live="polite"
      className="workflow-rail"
    >
      <header>
        <div>
          <Gauge aria-hidden="true" size={15} />
          <strong>Analysis pipeline</strong>
        </div>
        <span className={`workflow-rail__overall workflow-rail__overall--${runStatus}`}>
          {overallLabel}
        </span>
      </header>
      <div className="workflow-rail__stages">
        {stages.map((stage, index) => {
          const Icon = stage.icon
          return (
            <div className="workflow-rail__segment" key={stage.label}>
              <article className={`workflow-stage workflow-stage--${stage.state}`}>
                <div className="workflow-stage__topline">
                  <span className="workflow-stage__icon"><Icon aria-hidden="true" size={14} /></span>
                  <span className="workflow-stage__state"><StateIcon state={stage.state} /></span>
                </div>
                <strong>{stage.label}</strong>
                <small>{stage.meta}</small>
                {stage.agents && (
                  <div className="workflow-stage__agents">
                    {stage.agents.map((agent) => (
                      <span
                        className={`workflow-agent workflow-agent--${agent.state}`}
                        key={agent.label}
                      >
                        <i aria-hidden="true" />{agent.label}
                      </span>
                    ))}
                  </div>
                )}
              </article>
              {index < stages.length - 1 && (
                <ChevronRight aria-hidden="true" className="workflow-rail__connector" size={14} />
              )}
            </div>
          )
        })}
      </div>
      {runStatus === 'running' && (
        <p>
          Live backend progress · {progress?.phase.replaceAll('_', ' ') ?? 'starting workflow'}
        </p>
      )}
    </section>
  )
}
