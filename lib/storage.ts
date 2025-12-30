export interface IndexMetadata {
  url: string
  namespace: string
  index?: string
  clientSlug?: string
  pagesCrawled: number
  createdAt: string
  documentSourceCounts?: {
    website_pages: number
    intake_form: number
    client_materials: number
    unknown: number
  }
  metadata?: {
    title?: string
    description?: string
    favicon?: string
    ogImage?: string
    indexName?: string
  } & Record<string, unknown>
}


