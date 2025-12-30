import { NextRequest, NextResponse } from 'next/server'
import { getBackendUrl, buildApiHeaders } from '@/lib/backend'

// Proxy to Python backend's /api/mintagent/stats
export async function POST(request: NextRequest) {
  try {
    const backendUrl = getBackendUrl('/api/mintagent/stats')
    const body = await request.json()

    // Ensure clientSlug is set if namespace is present (compat)
    if (!body.clientSlug && body.namespace) {
      body.clientSlug = body.namespace
    }

    const response = await fetch(backendUrl, {
      method: 'POST',
      headers: buildApiHeaders(),
      body: JSON.stringify(body),
      cache: 'no-store'
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: response.statusText }))
      return NextResponse.json(
        errorData, 
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Failed to fetch stats from backend:', error)
    return NextResponse.json(
      { error: 'Failed to fetch stats' },
      { status: 500 }
    )
  }
}

