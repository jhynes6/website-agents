const backendBase =
  process.env.NEXT_PUBLIC_BACKEND_URL?.replace(/\/$/, '') || ''

if (process.env.NODE_ENV !== 'production') {
  // Log which backend the UI will call in dev
  // eslint-disable-next-line no-console
  console.log(
    `[firestarter] NEXT_PUBLIC_BACKEND_URL: ${
      backendBase || '(unset - using Next.js API routes)'
    }`
  )
}

export const getBackendUrl = (path: string) =>
  backendBase ? `${backendBase}${path}` : path

export const buildApiHeaders = (
  extra?: Record<string, string>
): Record<string, string> => {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...extra,
  }

  // Preserve ability for users to provide Firecrawl key client-side
  if (typeof window !== 'undefined') {
    const firecrawlApiKey = window.localStorage.getItem('firecrawl_api_key')
    if (firecrawlApiKey) {
      headers['X-Firecrawl-API-Key'] = firecrawlApiKey
    }
  }

  return headers
}

