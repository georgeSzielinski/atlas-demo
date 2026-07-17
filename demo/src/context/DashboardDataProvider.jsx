/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useMemo } from 'react'
import { getDashboardV2 } from '../services/api'
import { useAsyncResource } from '../services/useAsyncResource'

// Single source of the homepage payload. Every Dashboard v2 widget reads from
// this context, so the homepage issues exactly ONE GET /dashboard/v2 request.
// Data lives here; UI/selection state is kept out of this provider so selection
// changes never re-trigger the fetch.

const DashboardDataContext = createContext(null)

const DASHBOARD_V2_KEY = 'dashboard/v2'


export function DashboardDataProvider({ children }) {
  const { data, isLoading, error, refetch } = useAsyncResource(
    DASHBOARD_V2_KEY,
    getDashboardV2,
  )


  const value = useMemo(
    () => ({ data: data ?? null, isLoading, error, refetch }),
    [data, isLoading, error, refetch],
  )

  return (
    <DashboardDataContext.Provider value={value}>
      {children}
    </DashboardDataContext.Provider>
  )
}

export function useDashboardData() {
  const context = useContext(DashboardDataContext)
  if (context === null) {
    throw new Error('useDashboardData must be used within a DashboardDataProvider')
  }
  return context
}

// Convenience selector: read one top-level section from the payload.
export function useDashboardSection(name) {
  const { data } = useDashboardData()
  return data ? data[name] : undefined
}
