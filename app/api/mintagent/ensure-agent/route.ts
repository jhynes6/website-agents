import { NextRequest, NextResponse } from 'next/server'
import { getBackendUrl, buildApiHeaders } from '@/lib/backend'

// Proxy to Python backend's /api/mintagent/ensure-agent
export async function POST(request: NextRequest) {
  try {
    const backendUrl = getBackendUrl('/api/mintagent/ensure-agent')
    const body = await request.json()

    // Ensure clientSlug is set if namespace is present (compat)
    if (!body.clientSlug && body.namespace) {
      body.clientSlug = body.namespace
    }

    const response = await fetch(backendUrl, {
      method: 'POST',
      headers: buildApiHeaders(),
      body: JSON.stringify(body),
      cache: 'no-store',
    })

    if (!response.ok) {
      const text = await response.text()
      return NextResponse.json(
        { error: `Backend error: ${response.status} ${text}` },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Failed to ensure agent:', error)
    return NextResponse.json({ error: 'Failed to ensure agent' }, { status: 500 })
  }
}


