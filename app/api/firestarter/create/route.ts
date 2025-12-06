import { NextRequest, NextResponse } from 'next/server'
import FirecrawlApp from '@mendable/firecrawl-js'
import { searchIndex } from '@/lib/upstash-search'
import { saveIndex } from '@/lib/storage'
import { serverConfig as config } from '@/firestarter.config'

// Lightweight structured logger for crawl flow
const log = (message: string, data?: Record<string, unknown>) => {
  const base = `[firestarter:create] ${message}`
  if (data && Object.keys(data).length > 0) {
    console.log(base, JSON.stringify(data))
  } else {
    console.log(base)
  }
}


export async function POST(request: NextRequest) {
  try {
    // Check if creation is disabled
    if (!config.features.enableCreation) {
      return NextResponse.json({ 
        error: 'Chatbot creation is currently disabled. You can only view existing chatbots.' 
      }, { status: 403 })
    }

    let body;
    try {
      body = await request.json()
    } catch {
      return NextResponse.json({ error: 'Invalid request body' }, { status: 400 })
    }
    
    const { url, limit = config.crawling.defaultLimit, includePaths, excludePaths } = body
    log('request.received', { url, limit, includePathsLength: includePaths?.length, excludePathsLength: excludePaths?.length })
    
    if (!url) {
      return NextResponse.json({ error: 'URL is required' }, { status: 400 })
    }

    // Generate unique namespace with timestamp to avoid collisions
    const baseNamespace = new URL(url).hostname.replace(/\./g, '-')
    const timestamp = Date.now()
    const namespace = `${baseNamespace}-${timestamp}`
    
    // Initialize Firecrawl with API key from environment or headers
    const apiKey = process.env.FIRECRAWL_API_KEY || request.headers.get('X-Firecrawl-API-Key')
    if (!apiKey) {
      return NextResponse.json({ 
        error: 'Firecrawl API key is not configured. Please provide your API key.' 
      }, { status: 500 })
    }
    
    const firecrawl = new FirecrawlApp({
      apiKey: apiKey
    })

    // Start crawling the website with specified limit
    
    const crawlOptions = {
      limit: limit,
      scrapeOptions: {
        formats: ['markdown', 'html'] as ('markdown' | 'html')[],
        maxAge: config.crawling.cacheMaxAge, // Use config value
      },
      includePaths: undefined as string[] | undefined,
      excludePaths: undefined as string[] | undefined
    }
    
    // Add include/exclude paths if provided
    if (includePaths && Array.isArray(includePaths) && includePaths.length > 0) {
      crawlOptions.includePaths = includePaths
    }
    if (excludePaths && Array.isArray(excludePaths) && excludePaths.length > 0) {
      crawlOptions.excludePaths = excludePaths
    }
    
    log('crawl.start', { url, limit, cacheMaxAge: crawlOptions.scrapeOptions.maxAge, includePaths, excludePaths })
    const crawlResponse = await firecrawl.crawlUrl(url, crawlOptions) as {
      success: boolean
      data: Array<{
        url?: string
        markdown?: string
        content?: string
        metadata?: {
          title?: string
          description?: string
          ogDescription?: string
          sourceURL?: string
          favicon?: string
          ogImage?: string
          'og:image'?: string
        }
      }>
    }
    log('crawl.complete', { success: crawlResponse.success, pages: crawlResponse.data?.length })
    if (!crawlResponse.success) {
      log('crawl.error', { message: 'Firecrawl returned success=false' })
      return NextResponse.json({ error: 'Crawl failed to start' }, { status: 502 })
    }
    if (!crawlResponse.data || crawlResponse.data.length === 0) {
      log('crawl.empty', { message: 'No pages returned from crawl' })
      return NextResponse.json({ error: 'Crawl completed but returned no pages' }, { status: 502 })
    }
    const pages = crawlResponse.data
    const pagesPreview = pages.slice(0, 5).map((page) => ({
      title: page.metadata?.title || 'Untitled',
      url: page.metadata?.sourceURL || page.url,
      hasContent: Boolean(page.markdown || page.content)
    }))
    const missingContent = pages.filter((p) => !(p.markdown || p.content)).length
    const missingUrl = pages.filter((p) => !(p.metadata?.sourceURL || p.url)).length
    log('crawl.pages.preview', { sample: pagesPreview })
    log('crawl.pages.summary', { total: pages.length, missingContent, missingUrl })
    
    
    // Store the crawl data for immediate use
    const crawlId = 'immediate-' + Date.now()
    
    // Log first page content preview for debugging
    if (crawlResponse.data && crawlResponse.data.length > 0) {
      // Find the homepage in the crawled data
      const homepage = crawlResponse.data.find((page) => {
        const pageUrl = page.metadata?.sourceURL || page.url || ''
        // Check if it's the homepage (ends with domain or domain/)
        return pageUrl === url || pageUrl === url + '/' || pageUrl === url.replace(/\/$/, '')
      }) || crawlResponse.data[0] // Fallback to first page
      
      // Log homepage info for debugging
      log('crawl.homepage', {
        title: homepage?.metadata?.title,
        url: homepage?.metadata?.sourceURL || homepage?.url
      })
    }
    
    // Store documents in Upstash Search
    const documents = pages.map((page, index) => {
      // Get the content and metadata
      const fullContent = page.markdown || page.content || ''
      const title = page.metadata?.title || 'Untitled'
      const url = page.metadata?.sourceURL || page.url || ''
      const description = page.metadata?.description || page.metadata?.ogDescription || ''
      
      // Create a searchable text - include namespace for better search filtering
      // The limit is 1500 chars for the whole content object when stringified
      const searchableText = `namespace:${namespace} ${title} ${description} ${fullContent}`.substring(0, 1000)
      
      return {
        id: `${namespace}-${index}`,
        content: {
          text: searchableText,  // Searchable text
          url: url,  // Required by FirestarterContent
          title: title  // Required by FirestarterContent
        },
        metadata: {
          namespace: namespace,
          title: title,
          url: url,
          sourceURL: page.metadata?.sourceURL || page.url || '',
          crawlDate: new Date().toISOString(),
          pageTitle: page.metadata?.title,
          description: page.metadata?.description || page.metadata?.ogDescription,
          favicon: page.metadata?.favicon,
          ogImage: page.metadata?.ogImage || page.metadata?.['og:image'],
          // Store the full content in metadata for retrieval (not searchable but accessible)
          fullContent: fullContent.substring(0, 5000) // Store more content here
        }
      }
    })
    
    // Store documents in batches
    const batchSize = 10
    log('upsert.start', { totalDocuments: documents.length, batchSize })
    
    try {
      for (let i = 0; i < documents.length; i += batchSize) {
        const batch = documents.slice(i, i + batchSize)
        await searchIndex.upsert(batch)
        log('upsert.batch', { batchIndex: i / batchSize, batchSize: batch.length })
      }
      
      
      // Verify documents were stored - try multiple approaches
      
      // First try with filter
      interface SearchResult {
        metadata?: {
          namespace?: string
        }
      }
      let verifyResult: SearchResult[] = []
      try {
        verifyResult = await searchIndex.search({
          query: documents[0]?.content?.title || 'test',
          filter: `metadata.namespace = "${namespace}"`,
          limit: 1
        })
      } catch (filterSearchError) {
        log('verify.search.filter.error', { error: filterSearchError instanceof Error ? filterSearchError.message : 'unknown' })
        
        // Try without filter
        try {
          const allResults = await searchIndex.search({
            query: namespace, // Search for the namespace itself
            limit: 10
          })
          
          // Log the structure of the first result for debugging
          if (allResults.length > 0) {
          }
          
          // Manual filter check
          verifyResult = allResults.filter((doc: SearchResult) => {
            const docNamespace = doc.metadata?.namespace
            return docNamespace === namespace
          })
        } catch (searchError) {
          log('verify.search.error', { error: searchError instanceof Error ? searchError.message : 'unknown' })
        }
      }
      
      log('verify.result', { matches: verifyResult.length })
    } catch (upsertError) {
      throw new Error(`Failed to store documents: ${upsertError instanceof Error ? upsertError.message : 'Unknown error'}`)
    }
    
    // Save index metadata to storage
    const homepage = crawlResponse.data.find((page) => {
      const pageUrl = page.metadata?.sourceURL || page.url || ''
      return pageUrl === url || pageUrl === url + '/' || pageUrl === url.replace(/\/$/, '')
    }) || crawlResponse.data[0]
    
    try {
      await saveIndex({
        url,
        namespace,
        pagesCrawled: crawlResponse.data?.length || 0,
        createdAt: new Date().toISOString(),
        metadata: {
          title: homepage?.metadata?.title,
          description: homepage?.metadata?.description || homepage?.metadata?.ogDescription,
          favicon: homepage?.metadata?.favicon,
          ogImage: homepage?.metadata?.ogImage || homepage?.metadata?.['og:image']
        }
      })
      log('index.saved', { namespace, pagesCrawled: crawlResponse.data?.length || 0 })
    } catch {
      // Continue execution - storage error shouldn't fail the entire operation
      console.error('Failed to save index metadata')
    }
    
    return NextResponse.json({
      success: true,
      namespace,
      crawlId,
      message: `Crawl completed successfully (limited to ${limit} pages)`,
      details: {
        url,
        pagesLimit: limit,
        pagesCrawled: crawlResponse.data?.length || 0,
        formats: ['markdown', 'html']
      },
      data: crawlResponse.data // Include the actual crawl data
    })
  } catch (error) {
    log('crawl.failed', { error: error instanceof Error ? error.message : 'unknown' })
    
    const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred'
    const statusCode = error && typeof error === 'object' && 'statusCode' in error ? error.statusCode : undefined
    
    
    // Provide more specific error messages
    if (statusCode === 401) {
      return NextResponse.json(
        { error: 'Firecrawl authentication failed. Please check your API key.' },
        { status: 401 }
      )
    }
    
    return NextResponse.json(
      { 
        error: 'Failed to start crawl',
        details: errorMessage
      },
      { status: 500 }
    )
  }
}

