export type RiskTolerance = 'low' | 'medium' | 'high'

export interface Company {
  id: string
  symbol: string
  name: string
  sector: string
  exchange: string
}

export interface InvestorProfile {
  id: string
  name: string
  risk_tolerance: RiskTolerance
  investment_horizon_years: number
  max_position_percent: number
  max_sector_percent: number
  is_demo: boolean
}

export interface Holding {
  id: string
  profile_id: string
  company: Company
  quantity: number
  average_cost: number
}

export interface WatchlistItem {
  id: string
  profile_id: string
  company: Company
}

const apiUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${apiUrl}${path}`)
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: string } | null
    throw new Error(payload?.detail ?? `Request failed: ${response.status}`)
  }
  return response.json() as Promise<T>
}

async function requestJson<T>(
  path: string,
  method: 'POST' | 'PATCH',
  body: Record<string, unknown>,
): Promise<T> {
  const response = await fetch(`${apiUrl}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: string } | null
    throw new Error(payload?.detail ?? `Request failed: ${response.status}`)
  }
  return response.json() as Promise<T>
}

async function requestDelete(path: string): Promise<void> {
  const response = await fetch(`${apiUrl}${path}`, { method: 'DELETE' })
  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: string } | null
    throw new Error(payload?.detail ?? `Request failed: ${response.status}`)
  }
}

export function getCompanies(query?: string): Promise<Company[]> {
  const suffix = query ? `?q=${encodeURIComponent(query)}` : ''
  return getJson<Company[]>(`/api/companies${suffix}`)
}

export function getProfiles(): Promise<InvestorProfile[]> {
  return getJson<InvestorProfile[]>('/api/profiles')
}

export function createProfile(values: {
  name: string
  risk_tolerance: RiskTolerance
  investment_horizon_years: number
  max_position_percent: number
  max_sector_percent: number
}): Promise<InvestorProfile> {
  return requestJson<InvestorProfile>('/api/profiles', 'POST', values)
}

export function updateProfile(
  profileId: string,
  values: {
    name: string
    risk_tolerance: RiskTolerance
    investment_horizon_years: number
    max_position_percent: number
    max_sector_percent: number
  },
): Promise<InvestorProfile> {
  return requestJson<InvestorProfile>(`/api/profiles/${profileId}`, 'PATCH', values)
}

export function getHoldings(profileId: string): Promise<Holding[]> {
  return getJson<Holding[]>(`/api/profiles/${profileId}/holdings`)
}

export function createHolding(
  profileId: string,
  values: { company_id: string; quantity: number; average_cost: number },
): Promise<Holding> {
  return requestJson<Holding>(`/api/profiles/${profileId}/holdings`, 'POST', values)
}

export function updateHolding(
  profileId: string,
  holdingId: string,
  values: { quantity: number; average_cost: number },
): Promise<Holding> {
  return requestJson<Holding>(
    `/api/profiles/${profileId}/holdings/${holdingId}`,
    'PATCH',
    values,
  )
}

export function deleteHolding(profileId: string, holdingId: string): Promise<void> {
  return requestDelete(`/api/profiles/${profileId}/holdings/${holdingId}`)
}

export function getWatchlist(profileId: string): Promise<WatchlistItem[]> {
  return getJson<WatchlistItem[]>(`/api/profiles/${profileId}/watchlist`)
}

export function createWatchlistItem(
  profileId: string,
  companyId: string,
): Promise<WatchlistItem> {
  return requestJson<WatchlistItem>(`/api/profiles/${profileId}/watchlist`, 'POST', {
    company_id: companyId,
  })
}

export function deleteWatchlistItem(profileId: string, itemId: string): Promise<void> {
  return requestDelete(`/api/profiles/${profileId}/watchlist/${itemId}`)
}
