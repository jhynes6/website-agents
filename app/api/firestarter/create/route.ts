import { NextRequest, NextResponse } from 'next/server'
import { getBackendUrl, buildApiHeaders } from '@/lib/backend'

// Proxy to Python backend's /api/firestarter/create
export async function POST(request: NextRequest) {
  try {
    const backendUrl = getBackendUrl('/api/firestarter/create')
    const body = await request.json()

    // Forward the request to the Python backend
    const response = await fetch(backendUrl, {
      method: 'POST',
      headers: buildApiHeaders(),
      body: JSON.stringify(body),
      cache: 'no-store'
    })

    if (!response.ok) {
      // Forward error response
      const errorData = await response.json().catch(() => ({ error: response.statusText }))
      return NextResponse.json(
        errorData, 
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Failed to create via backend:', error)
    return NextResponse.json(
      { error: 'Failed to initiate crawl' },
      { status: 500 }
    )
  }
}
