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
import type { AnalysisResult } from '../api/analysis'

type RunStatus = 'idle' | 'running' | 'complete' | 'error'
type StageState = 'ready' | 'active' | 'queued' | 'complete' | 'warning' | 'error'

interface WorkflowRailProps {
  analysis: AnalysisResult | null
  companyLabel: string
  profileLabel: string
  runStatus: RunStatus
}

interface Stage {
  icon: LucideIcon
  label: string
  meta: string
  state: StageState
}

function stageState(
  runStatus: RunStatus,
  stageIndex: number,
  degraded = false,
): StageState {
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
  profileLabel,
  runStatus,
}: WorkflowRailProps) {
  const degraded = analysis?.status === 'degraded'
  const degradedAgents = analysis?.agents.filter((agent) => agent.status !== 'completed').length ?? 0
  const maxAgentLatency = analysis
    ? Math.max(...analysis.agents.map((agent) => agent.latency_ms))
    : null
  const stages: Stage[] = [
    {
      icon: Braces,
      label: 'Input snapshot',
      meta: companyLabel && profileLabel ? `${companyLabel} · ${profileLabel}` : 'Select research inputs',
      state: stageState(runStatus, 0),
    },
    {
      icon: UsersRound,
      label: 'Parallel specialists',
      meta: maxAgentLatency === null
        ? 'Market · Filing · Portfolio'
        : `3 agents · slowest ${maxAgentLatency}ms`,
      state: stageState(runStatus, 1, degradedAgents > 0),
    },
    {
      icon: GitMerge,
      label: 'Validate evidence',
      meta: analysis
        ? `${analysis.metrics.evidence_count} items · ${analysis.conflicts.length} conflicts`
        : 'Citations and conflicts',
      state: stageState(runStatus, 2, degraded),
    },
    {
      icon: Sparkles,
      label: 'Synthesize decision',
      meta: analysis
        ? `${analysis.recommendation.action} · ${Math.round(analysis.recommendation.confidence * 100)}% confidence`
        : 'Personalized recommendation',
      state: stageState(runStatus, 3, degraded),
    },
    {
      icon: Database,
      label: 'Persist and measure',
      meta: analysis
        ? `${analysis.metrics.end_to_end_latency_ms}ms end to end`
        : 'Metrics and audit trail',
      state: stageState(runStatus, 4, degraded),
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
              </article>
              {index < stages.length - 1 && (
                <ChevronRight aria-hidden="true" className="workflow-rail__connector" size={14} />
              )}
            </div>
          )
        })}
      </div>
      {runStatus === 'running' && (
        <p>Node-level results become available together when the validated graph completes.</p>
      )}
    </section>
  )
}
