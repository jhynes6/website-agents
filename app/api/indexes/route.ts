import { NextRequest, NextResponse } from 'next/server'
import { getBackendUrl, buildApiHeaders } from '@/lib/backend'

async function loadIndexesSummaryFromSupabase(): Promise<{ indexes: unknown[] } | null> {
  const supabaseUrl = (process.env.SUPABASE_AGENT_URL || '').replace(/\/$/, '')
  const serviceKey = process.env.SUPABASE_AGENT_SERVICE_ROLE_KEY || process.env.SUPABASE_AGENT_KEY || ''
  if (!supabaseUrl || !serviceKey) return null

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
    if (!response.ok) return null
    const data = await response.json()
    if (!data || !Array.isArray(data.indexes)) return null
    return { indexes: data.indexes }
  } catch {
    return null
  }
}

// Proxy to Python backend's /api/mintagent/indexes
export async function GET(request: NextRequest) {
  try {
    const backendUrl = getBackendUrl('/api/mintagent/indexes') + request.nextUrl.search
    
    const response = await fetch(backendUrl, {
      method: 'GET',
      headers: buildApiHeaders(),
      cache: 'no-store'
    })

    if (!response.ok) {
      // Fallback for environments where backend is temporarily unavailable.
      const fallback = await loadIndexesSummaryFromSupabase()
      if (fallback) return NextResponse.json(fallback)
      return NextResponse.json(
        { error: `Backend error: ${response.statusText}` },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Failed to fetch indexes:', error)
    const fallback = await loadIndexesSummaryFromSupabase()
    if (fallback) return NextResponse.json(fallback)
    return NextResponse.json(
      { error: 'Failed to fetch indexes' },
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
