import { Search } from '@upstash/search'

// Initialize Upstash Search client
const searchClient = new Search({
  url: process.env.UPSTASH_SEARCH_REST_URL!,
  token: process.env.UPSTASH_SEARCH_REST_TOKEN!,
})

// Create a search index for mintagent documents
export const searchIndex = searchClient.index<MintagentContent>('mintagent')

export interface MintagentContent {
  text: string
  url: string
  title: string
  [key: string]: unknown // Add index signature for Upstash type compatibility
}

export interface MintagentIndex {
  namespace: string
  url: string
  pagesCrawled: number
  crawlDate: string
  metadata: {
    title: string
    description?: string
    favicon?: string
    ogImage?: string
  }
}