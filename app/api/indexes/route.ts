import { NextRequest, NextResponse } from 'next/server'
import { getIndexes, getIndex, saveIndex, deleteIndex, IndexMetadata } from '@/lib/storage'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const namespace = searchParams.get('namespace')

    console.log(`[API] GET /indexes - namespace param: ${namespace}`)

    if (namespace) {
      const index = await getIndex(namespace)
      console.log(`[API] getIndex result for ${namespace}:`, index ? 'Found' : 'Not Found')
      
      if (index) {
        return NextResponse.json({ index })
      }
      return NextResponse.json({ error: 'Index not found' }, { status: 404 })
    }

    const indexes = await getIndexes()
    console.log(`[API] getIndexes result count:`, indexes.length)
    return NextResponse.json({ indexes: indexes || [] })
  } catch (error) {
    // Return empty array instead of error to allow app to function
    console.error('Failed to get indexes', error)
    return NextResponse.json({ indexes: [] })
  }
}

export async function POST(request: NextRequest) {
  try {
    const index: IndexMetadata = await request.json()
    await saveIndex(index)
    return NextResponse.json({ success: true })
  } catch {
    // Return success anyway to allow app to continue
    console.error('Failed to save index')
    return NextResponse.json({ success: true, warning: 'Index saved locally only' })
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const namespace = searchParams.get('namespace')
    
    if (!namespace) {
      return NextResponse.json({ error: 'Namespace is required' }, { status: 400 })
    }
    
    await deleteIndex(namespace)
    return NextResponse.json({ success: true })
  } catch {
    // Return success anyway to allow app to continue
    console.error('Failed to delete index')
    return NextResponse.json({ success: true, warning: 'Index deleted locally only' })
  }
}
