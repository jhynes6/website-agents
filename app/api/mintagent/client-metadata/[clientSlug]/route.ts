import { NextRequest, NextResponse } from 'next/server'
import { getBackendUrl, buildApiHeaders } from '@/lib/backend'

// Proxy to Python backend's /api/mintagent/client-metadata/{clientSlug}
export async function GET(
  _request: NextRequest,
  { params }: { params: { clientSlug: string } }
) {
  try {
    const clientSlug = params.clientSlug
    const backendUrl = getBackendUrl(`/api/mintagent/client-metadata/${clientSlug}`)

    const response = await fetch(backendUrl, {
      method: 'GET',
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
    console.error('Failed to fetch client metadata:', error)
    return NextResponse.json(
      { error: 'Failed to fetch client metadata' },
      { status: 500 }
    )
  }
}


