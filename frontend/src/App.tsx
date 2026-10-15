import {
  Activity,
  BriefcaseBusiness,
  Building2,
  Download,
  FileSearch,
  FileText,
  LayoutDashboard,
  Search,
  ShieldAlert,
  Sparkles,
  TrendingUp,
  UserRound,
  Waves,
  Upload,
  RefreshCw,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import './App.css'
import {
  runAnalysis as requestAnalysis,
  type AnalysisResult,
  type Signal,
  type SignalTone,
} from './api/analysis'
import {
  getCompanies,
  getHoldings,
  getProfiles,
  type Company,
  type Holding,
  type InvestorProfile,
  type RiskTolerance,
} from './api/catalog'
import {
  getFilingDownloadUrl,
  getFilingDocuments,
  retryFilingDocument,
  syncSecFilings,
  uploadFiling,
  type FilingDocument,
  type SecSyncJob,
} from './api/filings'
import { AgentCard } from './components/AgentCard'
import { Button } from './components/Button'
import { CitationCard } from './components/CitationCard'
import { CustomSelect } from './components/CustomSelect'
import { RecommendationBanner } from './components/RecommendationBanner'
import { SignalCard } from './components/SignalCard'
import { WorkflowRail } from './components/WorkflowRail'

type ApiStatus = 'checking' | 'connected' | 'unavailable'
type RunStatus = 'idle' | 'running' | 'complete' | 'error'

const apiUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const navigation = [
  { label: 'Workspace', icon: LayoutDashboard, active: true },
  { label: 'Research', icon: Search },
  { label: 'Portfolio', icon: BriefcaseBusiness },
  { label: 'Evaluation', icon: Activity },
]

const riskLabels: Record<RiskTolerance, string> = {
  low: 'Conservative',
  medium: 'Balanced',
  high: 'Aggressive',
}

const filingTypeOptions = [
  { value: 'annual_report', label: 'Annual report', description: 'Full-year audited disclosure' },
  { value: 'quarterly_report', label: 'Quarterly report', description: 'Interim financial disclosure' },
  { value: 'earnings_release', label: 'Earnings release', description: 'Results and management commentary' },
  { value: 'investor_presentation', label: 'Investor presentation', description: 'Official investor materials' },
  { value: 'regulatory_filing', label: 'Regulatory filing', description: 'Other official filing' },
]

const agentPresentation = {
  market_signal: { name: 'Market Signal Agent', icon: TrendingUp },
  filing_research: { name: 'Filing Research Agent', icon: FileSearch },
  portfolio_risk: { name: 'Portfolio Risk Agent', icon: ShieldAlert },
} as const

const signalPresentation = {
  price_momentum: { label: 'Price momentum', icon: TrendingUp },
  volume_anomaly: { label: 'Volume anomaly', icon: Waves },
  price_volatility: { label: 'Volatility risk', icon: Activity },
  filing_sentiment: { label: 'Filing sentiment', icon: FileSearch },
  portfolio_fit: { label: 'Portfolio fit', icon: ShieldAlert },
} as const

function signalTone(classification: Signal['classification']): SignalTone {
  if (classification === 'positive') return 'positive'
  if (classification === 'negative') return 'negative'
  if (classification === 'mixed') return 'warning'
  return 'info'
}

function signalValue(signal: Signal): string {
  if (signal.dimension === 'price_volatility') {
    const volatilityLabels: Record<Signal['classification'], string> = {
      positive: 'Low risk',
      neutral: 'Moderate',
      negative: 'High risk',
      mixed: 'Mixed',
      insufficient_data: 'Unavailable',
    }
    return volatilityLabels[signal.classification]
  }
  const labels: Record<Signal['classification'], string> = {
    positive: 'Positive',
    neutral: 'Neutral',
    negative: 'High risk',
    mixed: 'Mixed',
    insufficient_data: 'Unavailable',
  }
  return labels[signal.classification]
}

function App() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>('checking')
  const [runStatus, setRunStatus] = useState<RunStatus>('idle')
  const [companies, setCompanies] = useState<Company[]>([])
  const [profiles, setProfiles] = useState<InvestorProfile[]>([])
  const [selectedCompanyId, setSelectedCompanyId] = useState('')
  const [selectedProfileId, setSelectedProfileId] = useState('')
  const [holdings, setHoldings] = useState<Holding[]>([])
  const [filingDocuments, setFilingDocuments] = useState<FilingDocument[]>([])
  const [filingFile, setFilingFile] = useState<File | null>(null)
  const [filingTitle, setFilingTitle] = useState('')
  const [filingDocumentType, setFilingDocumentType] = useState('annual_report')
  const [filingReportingPeriod, setFilingReportingPeriod] = useState('')
  const [filingPublishedAt, setFilingPublishedAt] = useState('')
  const [filingSourceName, setFilingSourceName] = useState('Company investor relations')
  const [filingSourceUrl, setFilingSourceUrl] = useState('')
  const [uploadProgress, setUploadProgress] = useState<number | null>(null)
  const [uploadInputKey, setUploadInputKey] = useState(0)
  const [secSyncJob, setSecSyncJob] = useState<SecSyncJob | null>(null)
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const activeFilingIds = filingDocuments
    .filter(
      (document) => document.processing_status === 'pending' ||
        document.processing_status === 'processing',
    )
    .map((document) => document.id)
    .sort()
    .join(',')

  useEffect(() => {
    const controller = new AbortController()
    Promise.all([
      fetch(`${apiUrl}/api/health`, { signal: controller.signal }).then((response) => {
        if (!response.ok) throw new Error('API health check failed')
        return response.json()
      }),
      getCompanies(),
      getProfiles(),
    ])
      .then(([, companyRows, profileRows]) => {
        setCompanies(companyRows)
        setProfiles(profileRows)
        setSelectedCompanyId(
          companyRows.find((company) => company.symbol === 'GOOGL')?.id ??
            companyRows[0]?.id ??
            '',
        )
        setSelectedProfileId(
          profileRows.find((profile) => profile.name === 'Ananya')?.id ??
            profileRows[0]?.id ??
            '',
        )
        setApiStatus('connected')
      })
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === 'AbortError') return
        setApiStatus('unavailable')
        setError('Could not load companies and investor profiles from the database.')
      })
    return () => controller.abort()
  }, [])

  useEffect(() => {
    if (!selectedProfileId) return
    getHoldings(selectedProfileId)
      .then(setHoldings)
      .catch(() => setError('Could not load portfolio holdings for this profile.'))
  }, [selectedProfileId])

  useEffect(() => {
    if (!selectedCompanyId) return
    let cancelled = false
    getFilingDocuments(selectedCompanyId)
      .then((documents) => {
        if (!cancelled) setFilingDocuments(documents)
      })
      .catch(() => {
        if (!cancelled) setError('Could not load indexed filings for this company.')
      })
    return () => {
      cancelled = true
    }
  }, [selectedCompanyId])

  useEffect(() => {
    if (!selectedCompanyId || !activeFilingIds) return

    let cancelled = false
    let timer: number | undefined

    const pollDocuments = async () => {
      try {
        const documents = await getFilingDocuments(selectedCompanyId)
        if (cancelled) return
        setFilingDocuments(documents)
        const stillProcessing = documents.some(
          (document) => document.processing_status === 'pending' ||
            document.processing_status === 'processing',
        )
        if (stillProcessing) {
          timer = window.setTimeout(pollDocuments, 4000)
        }
      } catch {
        if (!cancelled) timer = window.setTimeout(pollDocuments, 8000)
      }
    }

    timer = window.setTimeout(pollDocuments, 4000)
    return () => {
      cancelled = true
      if (timer !== undefined) window.clearTimeout(timer)
    }
  }, [activeFilingIds, selectedCompanyId])

  const selectedCompany = companies.find((company) => company.id === selectedCompanyId)
  const selectedProfile = profiles.find((profile) => profile.id === selectedProfileId)
  const companyOptions = companies.map((company) => ({
    value: company.id,
    label: `${company.symbol} · ${company.exchange}`,
    description: company.name,
  }))
  const profileOptions = profiles.map((profile) => ({
    value: profile.id,
    label: `${profile.name} · ${riskLabels[profile.risk_tolerance]}`,
    description: `${profile.investment_horizon_years}y horizon · ${Number(profile.max_position_percent)}% max position`,
  }))
  const hasReadyFiling = filingDocuments.some(
    (document) => document.processing_status === 'completed',
  )

  const signals = useMemo(
    () => analysis?.agents.flatMap((agent) => agent.signals) ?? [],
    [analysis],
  )
  const evidence = useMemo(
    () => analysis?.agents.flatMap((agent) => agent.evidence) ?? [],
    [analysis],
  )
  const supportingEvidenceIds = new Set(
    analysis?.recommendation.supporting_evidence_ids ?? [],
  )
  const opposingEvidenceIds = new Set(
    analysis?.recommendation.opposing_evidence_ids ?? [],
  )
  const degradedWarnings = analysis?.agents.flatMap((agent) => agent.warnings) ?? []
  const hasLiveMarketEvidence = evidence.some(
    (item) => !item.is_synthetic && item.source_name === 'Yahoo Finance',
  )
  const hasRealFilingEvidence = evidence.some(
    (item) => item.kind === 'document_excerpt' && !item.is_synthetic && item.source_url,
  )

  const resetAnalysis = () => {
    setAnalysis(null)
    setRunStatus('idle')
    setError(null)
  }

  const runSelectedAnalysis = async () => {
    if (!selectedCompany || !selectedProfile) return
    setRunStatus('running')
    setError(null)
    try {
      setAnalysis(await requestAnalysis(selectedCompany, selectedProfile))
      setRunStatus('complete')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The analysis workflow failed.')
      setRunStatus('error')
    }
  }

  const uploadSelectedFiling = async () => {
    if (!selectedCompany || !filingFile) return
    setUploadProgress(0)
    setError(null)
    try {
      const document = await uploadFiling(
        selectedCompany,
        filingFile,
        {
          title: filingTitle,
          documentType: filingDocumentType,
          reportingPeriod: filingReportingPeriod,
          publishedAt: filingPublishedAt,
          sourceName: filingSourceName,
          sourceUrl: filingSourceUrl,
        },
        setUploadProgress,
      )
      setFilingDocuments((current) => [
        document,
        ...current.filter((item) => item.id !== document.id),
      ])
      setFilingFile(null)
      setFilingTitle('')
      setFilingReportingPeriod('')
      setFilingPublishedAt('')
      setFilingSourceUrl('')
      setUploadInputKey((current) => current + 1)
      setUploadProgress(null)
    } catch (reason) {
      setUploadProgress(null)
      setError(reason instanceof Error ? reason.message : 'Filing upload failed.')
    }
  }

  const retryFiling = async (documentId: string) => {
    setError(null)
    try {
      const document = await retryFilingDocument(documentId)
      setFilingDocuments((current) => current.map(
        (item) => item.id === document.id ? document : item,
      ))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not retry the filing.')
    }
  }

  const syncSelectedCompanyFilings = async () => {
    if (!selectedCompany) return
    setError(null)
    setSecSyncJob({
      job_id: '',
      status: 'pending',
      discovered_count: 0,
      completed_count: 0,
      skipped_count: 0,
      failed_count: 0,
      document_ids: [],
      error: null,
    })
    try {
      const job = await syncSecFilings(selectedCompany.id, setSecSyncJob)
      setFilingDocuments(await getFilingDocuments(selectedCompany.id))
      if (job.status === 'failed') {
        setError(job.error ?? 'SEC filing sync failed.')
      }
    } catch (reason) {
      setSecSyncJob(null)
      setError(reason instanceof Error ? reason.message : 'SEC filing sync failed.')
    }
  }

  const secSyncRunning = secSyncJob !== null && [
    'pending',
    'discovering',
    'processing',
  ].includes(secSyncJob.status)

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="/" aria-label="VibeFinance home">
          <span className="brand__mark">V</span>
          <span>VibeFinance</span>
        </a>
        <nav className="sidebar__nav" aria-label="Primary navigation">
          {navigation.map(({ label, icon: Icon, active }) => (
            <a className={active ? 'nav-item nav-item--active' : 'nav-item'} href="#" key={label}>
              <Icon aria-hidden="true" size={17} />
              <span>{label}</span>
            </a>
          ))}
        </nav>
        <section className="system-card" aria-label="System status">
          <header>
            <span>System</span>
            <span className={`status-dot status-dot--${apiStatus}`} />
          </header>
          <strong>
            {apiStatus === 'connected'
              ? '3 agents ready'
              : apiStatus === 'checking'
                ? 'Connecting to engine'
                : 'Engine unavailable'}
          </strong>
          <span>Deterministic demo adapters</span>
        </section>
      </aside>

      <main className="workspace">
        <header className="workspace-header">
          <div>
            <span className="eyebrow">Intelligence workspace</span>
            <h1>Research decision room</h1>
          </div>
          <div className="workspace-header__actions">
            <CustomSelect
              ariaLabel="Company"
              disabled={apiStatus !== 'connected'}
              icon={<Building2 aria-hidden="true" size={15} />}
              onChange={(value) => {
                setFilingDocuments([])
                setSelectedCompanyId(value)
                resetAnalysis()
              }}
              options={companyOptions}
              placeholder="Select company"
              value={selectedCompanyId}
            />
            <CustomSelect
              ariaLabel="Investor profile"
              disabled={apiStatus !== 'connected'}
              icon={<UserRound aria-hidden="true" size={15} />}
              onChange={(value) => {
                setHoldings([])
                setSelectedProfileId(value)
                resetAnalysis()
              }}
              options={profileOptions}
              placeholder="Select investor"
              value={selectedProfileId}
            />
            <Button
              disabled={
                runStatus === 'running' ||
                apiStatus !== 'connected' ||
                !selectedCompany ||
                !selectedProfile
              }
              icon={<Sparkles aria-hidden="true" size={16} />}
              onClick={runSelectedAnalysis}
            >
              {runStatus === 'running' ? 'Running agents…' : 'Run intelligence'}
            </Button>
          </div>
        </header>

        <div className="demo-notice" role="note">
          {hasLiveMarketEvidence && hasRealFilingEvidence
            ? 'Live evidence: market observations, indexed filings, and stored portfolio holdings are active.'
            : hasLiveMarketEvidence
              ? 'Hybrid mode: market observations and stored holdings are active; ingest a filing to enable document evidence.'
              : 'Ready: run intelligence to retrieve market, filing, and portfolio evidence.'}
        </div>
        {error && <div className="error-notice" role="alert">{error}</div>}
        {analysis?.status === 'degraded' && (
          <div className="degraded-notice" role="status">
            <strong>Analysis completed with limited evidence.</strong>
            {degradedWarnings.length > 0 && ` ${degradedWarnings.join(' ')}`}
          </div>
        )}

        <WorkflowRail
          analysis={analysis}
          companyLabel={selectedCompany?.symbol ?? ''}
          profileLabel={selectedProfile?.name ?? ''}
          runStatus={runStatus}
        />

        <RecommendationBanner
          confidence={Math.round((analysis?.recommendation.confidence ?? 0) * 100)}
          detail={
            analysis?.recommendation.rationale.join(' ') ??
            'Choose a company and investor profile, then run the three-agent workflow.'
          }
          title={analysis?.recommendation.summary ?? 'Ready for evidence-backed analysis'}
        />

        <div className="workspace-grid">
          <div className="analysis-column">
            <section className="section-block">
              <header className="section-heading">
                <h2>Market signals</h2>
                <span>{analysis ? `${signals.length} classified dimensions` : 'Awaiting analysis'}</span>
              </header>
              <div className="signal-grid">
                {signals.length ? signals.map((signal) => {
                  const presentation = signalPresentation[signal.dimension]
                  return (
                    <SignalCard
                      confidence={Math.round(signal.confidence * 100)}
                      evidence={signal.rationale}
                      icon={presentation.icon}
                      key={signal.dimension}
                      label={presentation.label}
                      tone={signalTone(signal.classification)}
                      value={signalValue(signal)}
                    />
                  )
                }) : <p className="empty-state">Signals will appear after the workflow completes.</p>}
              </div>
            </section>

            <section className="section-block">
              <header className="section-heading">
                <h2>Agent synthesis</h2>
                <span className="positive-text">
                  {analysis
                    ? `Parallel execution · ${analysis.metrics.end_to_end_latency_ms}ms`
                    : 'Three-agent fan-out ready'}
                </span>
              </header>
              <div className="agent-list">
                {analysis ? analysis.agents.map((agent) => {
                  const presentation = agentPresentation[agent.agent]
                  return (
                    <AgentCard
                      confidence={Math.round(agent.confidence * 100)}
                      evidenceCount={agent.evidence.length}
                      icon={presentation.icon}
                      key={agent.agent}
                      latency={`${agent.latency_ms}ms`}
                      name={presentation.name}
                      status={agent.status}
                      summary={agent.summary}
                      warnings={agent.warnings}
                    />
                  )
                }) : <p className="empty-state">Agent outputs will appear here.</p>}
              </div>
            </section>
          </div>

          <aside className="evidence-column">
            <section className="filing-upload-card">
              <header className="section-heading">
                <h2>Company filings</h2>
                <span className={hasReadyFiling ? 'positive-text' : ''}>
                  {hasReadyFiling ? 'Evidence ready' : 'Upload PDF'}
                </span>
              </header>
              <label className="filing-dropzone">
                <Upload aria-hidden="true" size={18} />
                <span>{filingFile?.name ?? 'Choose an annual report or filing'}</span>
                <input
                  accept="application/pdf,.pdf"
                  disabled={uploadProgress !== null}
                  key={uploadInputKey}
                  onChange={(event) => {
                    const file = event.target.files?.[0] ?? null
                    setFilingFile(file)
                    if (file && !filingTitle) {
                      setFilingTitle(file.name.replace(/\.pdf$/i, '').replaceAll('-', ' '))
                    }
                  }}
                  type="file"
                />
              </label>
              <div className="filing-metadata">
                <label>
                  <span>Document title</span>
                  <input
                    disabled={uploadProgress !== null}
                    onChange={(event) => setFilingTitle(event.target.value)}
                    placeholder="Alphabet 2024 Annual Report"
                    required
                    type="text"
                    value={filingTitle}
                  />
                </label>
                <div className="filing-metadata__row">
                  <div className="filing-field">
                    <span>Document type</span>
                    <CustomSelect
                      ariaLabel="Document type"
                      disabled={uploadProgress !== null}
                      onChange={setFilingDocumentType}
                      options={filingTypeOptions}
                      value={filingDocumentType}
                      variant="field"
                    />
                  </div>
                  <label>
                    <span>Reporting period</span>
                    <input
                      disabled={uploadProgress !== null}
                      onChange={(event) => setFilingReportingPeriod(event.target.value)}
                      placeholder="FY 2024"
                      required
                      type="text"
                      value={filingReportingPeriod}
                    />
                  </label>
                </div>
                <div className="filing-metadata__row">
                  <label>
                    <span>Source name</span>
                    <input
                      disabled={uploadProgress !== null}
                      onChange={(event) => setFilingSourceName(event.target.value)}
                      required
                      type="text"
                      value={filingSourceName}
                    />
                  </label>
                  <label>
                    <span>Published</span>
                    <input
                      disabled={uploadProgress !== null}
                      onChange={(event) => setFilingPublishedAt(event.target.value)}
                      type="date"
                      value={filingPublishedAt}
                    />
                  </label>
                </div>
                <label>
                  <span>Official source URL</span>
                  <input
                    disabled={uploadProgress !== null}
                    onChange={(event) => setFilingSourceUrl(event.target.value)}
                    placeholder="https://www.sec.gov/Archives/..."
                    required
                    type="url"
                    value={filingSourceUrl}
                  />
                </label>
              </div>
              {uploadProgress !== null && (
                <div className="upload-progress" aria-label={`Upload ${uploadProgress}%`}>
                  <span style={{ width: `${uploadProgress}%` }} />
                </div>
              )}
              <div className="filing-actions">
                <Button
                  disabled={
                    !filingFile ||
                    !filingTitle.trim() ||
                    !filingReportingPeriod.trim() ||
                    !filingSourceName.trim() ||
                    !filingSourceUrl.startsWith('https://') ||
                    uploadProgress !== null ||
                    secSyncRunning ||
                    !selectedCompany
                  }
                  icon={<Upload aria-hidden="true" size={15} />}
                  onClick={uploadSelectedFiling}
                >
                  {uploadProgress !== null ? `Uploading ${uploadProgress}%` : 'Upload filing'}
                </Button>
                <Button
                  disabled={!selectedCompany || secSyncRunning || uploadProgress !== null}
                  icon={<RefreshCw aria-hidden="true" size={15} />}
                  onClick={syncSelectedCompanyFilings}
                >
                  {secSyncRunning ? 'Syncing SEC…' : 'Sync SEC'}
                </Button>
              </div>
              {secSyncJob && (
                <p className={`sec-sync-status sec-sync-status--${secSyncJob.status}`}>
                  {secSyncRunning
                    ? `${secSyncJob.status} · ${secSyncJob.discovered_count} discovered`
                    : `${secSyncJob.completed_count} indexed · ${secSyncJob.skipped_count} already current · ${secSyncJob.failed_count} failed`}
                </p>
              )}
              <div className="filing-document-list">
                {filingDocuments.map((document) => (
                  <div className="filing-document" key={document.id}>
                    <FileText aria-hidden="true" size={16} />
                    <div className="filing-document__body">
                      <strong>{document.title}</strong>
                      <span>
                        {document.processing_status === 'completed'
                          ? [
                              document.document_type.replaceAll('_', ' '),
                              document.reporting_period,
                              `${document.chunk_count ?? 0} indexed chunks`,
                            ].filter(Boolean).join(' · ')
                          : document.processing_status}
                      </span>
                      {document.error_message && <small>{document.error_message}</small>}
                    </div>
                    <div className="filing-document__actions">
                      {document.file_name && (
                        <a
                          aria-label={`Download ${document.title}`}
                          href={getFilingDownloadUrl(document.id)}
                          title="Download original file"
                        >
                          <Download aria-hidden="true" size={14} />
                        </a>
                      )}
                      {document.processing_status === 'failed' && (
                        <button onClick={() => retryFiling(document.id)} type="button">
                          Retry
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </section>

            <section className="portfolio-card">
              <header className="section-heading">
                <h2>Portfolio snapshot</h2>
                <span>{selectedProfile?.name ?? 'No profile'}</span>
              </header>
              <div className="portfolio-list">
                {holdings.length ? holdings.map((holding) => (
                  <div className="portfolio-row" key={holding.id}>
                    <div>
                      <strong>{holding.company.symbol}</strong>
                      <span>{holding.company.sector}</span>
                    </div>
                    <div>
                      <strong>{Number(holding.quantity).toLocaleString()} shares</strong>
                      <span>Avg ₹{Number(holding.average_cost).toLocaleString()}</span>
                    </div>
                  </div>
                )) : <p className="empty-state">No holdings recorded for this profile.</p>}
              </div>
              {selectedProfile && (
                <p className="portfolio-limits">
                  Limits: {Number(selectedProfile.max_position_percent)}% per position ·{' '}
                  {Number(selectedProfile.max_sector_percent)}% per sector
                </p>
              )}
            </section>

            <section className="section-block">
              <header className="section-heading">
                <h2>Source evidence</h2>
                <span className="info-text">{evidence.length} sources</span>
              </header>
              <div className="citation-list">
                {evidence.length ? evidence.map((item) => (
                  <CitationCard
                    document={item.title}
                    key={item.id}
                    quote={item.observation}
                    source={`${item.source_name}${item.page_number ? ` · p.${item.page_number}` : ''}`}
                    sourceUrl={item.source_url}
                    stance={
                      supportingEvidenceIds.has(item.id)
                        ? 'supporting'
                        : opposingEvidenceIds.has(item.id)
                          ? 'opposing'
                          : 'context'
                    }
                  />
                )) : <p className="empty-state">Cited evidence will appear here.</p>}
              </div>
            </section>

            <section className="conflict-card">
              <h3>Evidence conflict map</h3>
              <div className="conflict-list">
                {analysis?.conflicts.length ? analysis.conflicts.map((conflict) => (
                  <div className="conflict-item" key={`${conflict.dimension}-${conflict.description}`}>
                    <strong>{conflict.dimension.replaceAll('_', ' ')}</strong>
                    <p>{conflict.description}</p>
                    <span>{conflict.agent_names.map((name) => (
                      agentPresentation[name as keyof typeof agentPresentation]?.name ?? name
                    )).join(' ↔ ')}</span>
                  </div>
                )) : analysis
                  ? <p className="no-conflicts">No material agent conflicts detected.</p>
                  : <p className="empty-state">No evidence has been compared yet.</p>}
              </div>
            </section>

            {analysis && (
              <section className="metrics-card">
                <h3>Session evaluation</h3>
                <span>{analysis.metrics.evidence_count} evidence items</span>
                <span>
                  {analysis.metrics.portfolio_concentration_score === null
                    ? 'Concentration unavailable'
                    : `${Math.round(analysis.metrics.portfolio_concentration_score * 100)}% concentration risk`}
                </span>
                <span>
                  {analysis.metrics.signal_accuracy_30d === null
                    ? 'Accuracy needs 61 sessions'
                    : `${Math.round(analysis.metrics.signal_accuracy_30d * 100)}% 30-session signal accuracy`}
                </span>
                <span>{analysis.conflicts.length} detected conflict</span>
              </section>
            )}

            <p className="disclaimer">
              {analysis?.recommendation.disclaimer ??
                'Decision support only. VibeFinance does not provide financial advice.'}
            </p>
          </aside>
        </div>
      </main>
    </div>
  )
}

export default App
