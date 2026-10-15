import type { Company } from './catalog'

export type FilingProcessingStatus = 'pending' | 'processing' | 'completed' | 'failed'

export interface FilingDocument {
  id: string
  company_id: string
  title: string
  document_type: string
  reporting_period: string | null
  source_url: string | null
  source_name: string
  published_at: string | null
  file_name: string | null
  file_size_bytes: number | null
  processing_status: FilingProcessingStatus
  error_message: string | null
  page_count: number | null
  chunk_count: number | null
}

export interface FilingUploadMetadata {
  title: string
  documentType: string
  reportingPeriod: string
  publishedAt: string
  sourceName: string
  sourceUrl: string
}

export type SecSyncStatus =
  | 'pending'
  | 'discovering'
  | 'processing'
  | 'completed'
  | 'partial'
  | 'failed'

export interface SecSyncJob {
  job_id: string
  status: SecSyncStatus
  discovered_count: number
  completed_count: number
  skipped_count: number
  failed_count: number
  document_ids: string[]
  error: string | null
}

interface SecSyncAccepted {
  job_id: string
  status: SecSyncStatus
}

const apiUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: string } | null
    throw new Error(payload?.detail ?? `Request failed: ${response.status}`)
  }
  return response.json() as Promise<T>
}

export function getFilingDocuments(companyId: string): Promise<FilingDocument[]> {
  return fetch(
    `${apiUrl}/api/filings/documents?company_id=${encodeURIComponent(companyId)}`,
  ).then((response) => parseResponse<FilingDocument[]>(response))
}

export function getFilingDownloadUrl(documentId: string): string {
  return `${apiUrl}/api/filings/documents/${encodeURIComponent(documentId)}/download`
}

export function retryFilingDocument(documentId: string): Promise<FilingDocument> {
  return fetch(`${apiUrl}/api/filings/documents/${documentId}/retry`, {
    method: 'POST',
  }).then((response) => parseResponse<FilingDocument>(response))
}

export async function syncSecFilings(
  companyId: string,
  onProgress: (job: SecSyncJob) => void,
): Promise<SecSyncJob> {
  const accepted = await fetch(`${apiUrl}/api/filings/sec/sync`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      company_id: companyId,
      forms: ['10-K', '10-Q', '8-K'],
      per_form_limit: 1,
    }),
  }).then((response) => parseResponse<SecSyncAccepted>(response))

  let delay = 1000
  while (true) {
    await new Promise((resolve) => window.setTimeout(resolve, delay))
    const job = await fetch(
      `${apiUrl}/api/filings/sec/sync/${accepted.job_id}`,
    ).then((response) => parseResponse<SecSyncJob>(response))
    onProgress(job)
    if (['completed', 'partial', 'failed'].includes(job.status)) return job
    delay = Math.min(delay * 2, 4000)
  }
}

export function uploadFiling(
  company: Company,
  file: File,
  metadata: FilingUploadMetadata,
  onProgress: (percent: number) => void,
): Promise<FilingDocument> {
  const form = new FormData()
  form.append('file', file)
  form.append('company_id', company.id)
  form.append('title', metadata.title.trim())
  form.append('document_type', metadata.documentType)
  form.append('source_name', metadata.sourceName.trim())
  form.append('source_url', metadata.sourceUrl.trim())
  if (metadata.reportingPeriod.trim()) {
    form.append('reporting_period', metadata.reportingPeriod.trim())
  }
  if (metadata.publishedAt) form.append('published_at', metadata.publishedAt)

  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest()
    request.open('POST', `${apiUrl}/api/filings/upload`)
    request.upload.addEventListener('progress', (event) => {
      if (event.lengthComputable) {
        onProgress(Math.round((event.loaded / event.total) * 100))
      }
    })
    request.addEventListener('load', () => {
      let payload: FilingDocument | { detail?: string } | null = null
      try {
        payload = JSON.parse(request.responseText) as FilingDocument | { detail?: string }
      } catch {
        payload = null
      }
      if (request.status >= 200 && request.status < 300 && payload && 'id' in payload) {
        resolve(payload)
      } else {
        reject(new Error(payload && 'detail' in payload ? payload.detail : 'Upload failed'))
      }
    })
    request.addEventListener('error', () => reject(new Error('Upload connection failed')))
    request.send(form)
  })
}
