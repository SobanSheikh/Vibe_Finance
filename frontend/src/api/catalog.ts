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
  if (!response.ok) throw new Error(`Request failed: ${response.status}`)
  return response.json() as Promise<T>
}

export function getCompanies(query?: string): Promise<Company[]> {
  const suffix = query ? `?q=${encodeURIComponent(query)}` : ''
  return getJson<Company[]>(`/api/companies${suffix}`)
}

export function getProfiles(): Promise<InvestorProfile[]> {
  return getJson<InvestorProfile[]>('/api/profiles')
}

export function getHoldings(profileId: string): Promise<Holding[]> {
  return getJson<Holding[]>(`/api/profiles/${profileId}/holdings`)
}

export function getWatchlist(profileId: string): Promise<WatchlistItem[]> {
  return getJson<WatchlistItem[]>(`/api/profiles/${profileId}/watchlist`)
}
