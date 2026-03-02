import { NextRequest, NextResponse } from 'next/server'
import { getBackendUrl, buildApiHeaders } from '@/lib/backend'

// Proxy to Python backend's /api/mintagent/query
export async function POST(request: NextRequest) {
  try {
    const backendUrl = getBackendUrl('/api/mintagent/query')
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
      return NextResponse.json(
        { error: `Backend error: ${response.statusText}` }, 
        { status: response.status }
      )
    }

    // Handle streaming response
    if (body.stream) {
      return new Response(response.body, {
        headers: {
          'Content-Type': 'text/plain; charset=utf-8',
          'Transfer-Encoding': 'chunked'
        }
      })
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Failed to query backend:', error)
    return NextResponse.json(
      { error: 'Failed to process query' },
      { status: 500 }
    )
  }
}
