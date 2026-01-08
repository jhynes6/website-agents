import { NextRequest, NextResponse } from 'next/server'
import { getBackendUrl, buildApiHeaders } from '@/lib/backend'

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
      return NextResponse.json(
        { error: `Backend error: ${response.statusText}` }, 
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Failed to fetch indexes:', error)
    return NextResponse.json(
      { error: 'Failed to fetch indexes' },
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
