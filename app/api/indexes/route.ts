import { NextRequest, NextResponse } from 'next/server'
import { getBackendUrl, buildApiHeaders } from '@/lib/backend'

type IndexesFallbackResult = {
  indexes?: unknown[]
  debug: {
    source: 'supabase_summary'
    attempted: boolean
    ok: boolean
    reason?: string
    status?: number
    hasSupabaseUrl: boolean
    hasServiceKey: boolean
  }
}

async function loadIndexesSummaryFromSupabase(): Promise<IndexesFallbackResult> {
  const supabaseUrl = (process.env.SUPABASE_AGENT_URL || '').replace(/\/$/, '')
  const serviceKey = process.env.SUPABASE_AGENT_SERVICE_ROLE_KEY || process.env.SUPABASE_AGENT_KEY || ''
  const hasSupabaseUrl = Boolean(supabaseUrl)
  const hasServiceKey = Boolean(serviceKey)
  if (!supabaseUrl || !serviceKey) {
    return {
      debug: {
        source: 'supabase_summary',
        attempted: false,
        ok: false,
        reason: 'missing_supabase_env',
        hasSupabaseUrl,
        hasServiceKey,
      },
    }
  }

  try {
    const response = await fetch(
      `${supabaseUrl}/storage/v1/object/client-data-sources/__reports/indexes.json`,
      {
        method: 'GET',
        headers: {
          apikey: serviceKey,
          Authorization: `Bearer ${serviceKey}`,
        },
        cache: 'no-store',
      }
    )
    if (!response.ok) {
      return {
        debug: {
          source: 'supabase_summary',
          attempted: true,
          ok: false,
          reason: 'non_200',
          status: response.status,
          hasSupabaseUrl,
          hasServiceKey,
        },
      }
    }
    const data = await response.json()
    if (!data || !Array.isArray(data.indexes)) {
      return {
        debug: {
          source: 'supabase_summary',
          attempted: true,
          ok: false,
          reason: 'invalid_payload_shape',
          status: response.status,
          hasSupabaseUrl,
          hasServiceKey,
        },
      }
    }
    return {
      indexes: data.indexes,
      debug: {
        source: 'supabase_summary',
        attempted: true,
        ok: true,
        status: response.status,
        hasSupabaseUrl,
        hasServiceKey,
      },
    }
  } catch {
    return {
      debug: {
        source: 'supabase_summary',
        attempted: true,
        ok: false,
        reason: 'fetch_exception',
        hasSupabaseUrl,
        hasServiceKey,
      },
    }
  }
}

// Proxy to Python backend's /api/mintagent/indexes
export async function GET(request: NextRequest) {
  const hasBackendBaseUrl = Boolean(process.env.NEXT_PUBLIC_BACKEND_URL)
  const backendUrl = getBackendUrl('/api/mintagent/indexes') + request.nextUrl.search

  try {
    const response = await fetch(backendUrl, {
      method: 'GET',
      headers: buildApiHeaders(),
      cache: 'no-store'
    })

    if (!response.ok) {
      // Fallback for environments where backend is temporarily unavailable.
      const fallback = await loadIndexesSummaryFromSupabase()
      if (Array.isArray(fallback.indexes)) {
        return NextResponse.json({ indexes: fallback.indexes })
      }
      return NextResponse.json(
        {
          error: `Backend error: ${response.statusText}`,
          debug: {
            backend: {
              attempted: true,
              status: response.status,
              reason: 'non_200',
              hasBackendBaseUrl,
            },
            fallback: fallback.debug,
          },
        },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Failed to fetch indexes:', error)
    const fallback = await loadIndexesSummaryFromSupabase()
    if (Array.isArray(fallback.indexes)) {
      return NextResponse.json({ indexes: fallback.indexes })
    }
    return NextResponse.json(
      {
        error: 'Failed to fetch indexes',
        debug: {
          backend: {
            attempted: true,
            reason: 'fetch_exception',
            hasBackendBaseUrl,
          },
          fallback: fallback.debug,
        },
      },
      { status: 500 }
    )
  }
}

export async function POST(request: NextRequest) {
  try {
    const backendUrl = getBackendUrl('/api/mintagent/indexes')
    const body = await request.json()
    const response = await fetch(backendUrl, {
      method: 'POST',
      headers: buildApiHeaders(),
      body: JSON.stringify(body),
      cache: 'no-store',
    })
    if (!response.ok) {
      return NextResponse.json(
        { error: `Backend error: ${response.statusText}` },
        { status: response.status }
      )
    }
    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Failed to upsert index:', error)
    return NextResponse.json(
      { error: 'Failed to save index' },
      { status: 500 }
    )
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const backendUrl = getBackendUrl('/api/mintagent/indexes') + request.nextUrl.search

    const response = await fetch(backendUrl, {
      method: 'DELETE',
      headers: buildApiHeaders(),
      cache: 'no-store',
    })

    if (!response.ok) {
      return NextResponse.json(
        { error: `Backend error: ${response.statusText}` },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Failed to delete index:', error)
    return NextResponse.json(
      { error: 'Failed to delete index' },
      { status: 500 }
    )
  }
}
