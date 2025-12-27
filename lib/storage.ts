import { Redis } from '@upstash/redis'

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
  }
}

interface StorageAdapter {
  getIndexes(): Promise<IndexMetadata[]>
  getIndex(namespace: string): Promise<IndexMetadata | null>
  saveIndex(index: IndexMetadata): Promise<void>
  deleteIndex(namespace: string): Promise<void>
}

class LocalStorageAdapter implements StorageAdapter {
  private readonly STORAGE_KEY = 'firestarter_indexes'

  async getIndexes(): Promise<IndexMetadata[]> {
    if (typeof window === 'undefined') return []
    
    try {
      const stored = localStorage.getItem(this.STORAGE_KEY)
      return stored ? JSON.parse(stored) : []
    } catch {
      console.error('Failed to get stored indexes')
      return []
    }
  }

  async getIndex(namespace: string): Promise<IndexMetadata | null> {
    const indexes = await this.getIndexes()
    return indexes.find(i => i.namespace === namespace) || null
  }

  async saveIndex(index: IndexMetadata): Promise<void> {
    if (typeof window === 'undefined') {
      throw new Error('localStorage is not available on the server')
    }
    
    const indexes = await this.getIndexes()
    const existingIndex = indexes.findIndex(i => i.namespace === index.namespace)
    
    if (existingIndex !== -1) {
      indexes[existingIndex] = index
    } else {
      indexes.unshift(index)
    }
    
    // Keep only the last 50 indexes
    const limitedIndexes = indexes.slice(0, 50)
    
    try {
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(limitedIndexes))
    } catch (error) {
      throw error
    }
  }

  async deleteIndex(namespace: string): Promise<void> {
    if (typeof window === 'undefined') {
      throw new Error('localStorage is not available on the server')
    }
    
    const indexes = await this.getIndexes()
    const filteredIndexes = indexes.filter(i => i.namespace !== namespace)
    
    try {
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(filteredIndexes))
    } catch (error) {
      throw error
    }
  }
}

class RedisStorageAdapter implements StorageAdapter {
  private redis: Redis
  private readonly INDEXES_KEY = 'firestarter:indexes'
  private readonly INDEX_KEY_PREFIX = 'firestarter:index:'
  private readonly TIMEOUT_MS = 3000

  constructor() {
    if (!process.env.UPSTASH_REDIS_REST_URL || !process.env.UPSTASH_REDIS_REST_TOKEN) {
      console.error('[Redis] Configuration MISSING: UPSTASH_REDIS_REST_URL or UPSTASH_REDIS_REST_TOKEN not set')
      throw new Error('Redis configuration missing')
    }
    
    console.log('[Redis] Initializing adapter with URL:', process.env.UPSTASH_REDIS_REST_URL)
    this.redis = new Redis({
      url: process.env.UPSTASH_REDIS_REST_URL,
      token: process.env.UPSTASH_REDIS_REST_TOKEN,
    })
    
    // Test connection
    this.redis.ping().then(res => console.log('[Redis] PING response:', res)).catch(err => console.error('[Redis] PING failed:', err))
  }

  async getIndexes(): Promise<IndexMetadata[]> {
    const timeout = new Promise<IndexMetadata[]>((resolve) => {
      setTimeout(() => {
        console.error('[Redis] getIndexes timeout')
        resolve([])
      }, this.TIMEOUT_MS)
    })

    const work = (async () => {
      try {
        const cached = (await this.redis.get<IndexMetadata[]>(this.INDEXES_KEY)) || []
        const keys = await this.scanKeys(`${this.INDEX_KEY_PREFIX}*`, 100 /*count*/, 5000 /*maxKeys*/)
        const scanned = keys.length > 0 ? await this.fetchIndexesFromKeys(keys) : []

        if (scanned.length > 0) {
          const merged = this.mergeIndexes(cached, scanned)
          // Best-effort write back to keep the cached list in sync
          this.redis.set(this.INDEXES_KEY, merged).catch((err) =>
            console.error('[Redis] Failed to persist reconciled indexes list (non-fatal)', err)
          )
          return merged
        }

        if (cached.length > 0) {
          return this.sortByCreatedAt(cached)
        }

        return []
      } catch (error) {
        console.error('Failed to get indexes from Redis', error)
        return []
      }
    })()

    return Promise.race([work, timeout])
  }

  private sortByCreatedAt(items: IndexMetadata[]): IndexMetadata[] {
    return [...items].sort((a, b) => {
      const da = a?.createdAt ? Date.parse(a.createdAt) : 0
      const db = b?.createdAt ? Date.parse(b.createdAt) : 0
      return db - da
    })
  }

  private async scanKeys(pattern: string, count = 200, maxKeys = 10000): Promise<string[]> {
    let cursor = 0
    const keys: string[] = []

    do {
      const res = await this.redis.scan(cursor, { match: pattern, count })
      const nextCursor = typeof res[0] === 'string' ? parseInt(res[0], 10) : res[0]
      cursor = Number.isNaN(nextCursor) ? 0 : nextCursor
      const batchKeys = res[1] || []
      keys.push(...batchKeys)
      if (keys.length >= maxKeys) break
    } while (cursor !== 0)

    return keys
  }

  private mergeIndexes(existing: IndexMetadata[], fresh: IndexMetadata[]): IndexMetadata[] {
    const map = new Map<string, IndexMetadata>()
    ;[...existing, ...fresh].forEach((item) => {
      if (item?.namespace) {
        map.set(item.namespace, item)
      }
    })
    return this.sortByCreatedAt(Array.from(map.values()))
  }

  private async fetchIndexesFromKeys(keys: string[]): Promise<IndexMetadata[]> {
    const results: IndexMetadata[] = []
    const batchSize = 100
    for (let i = 0; i < keys.length; i += batchSize) {
      const slice = keys.slice(i, i + batchSize)
      const batch = (await this.redis.mget<IndexMetadata[]>(...slice)).filter(Boolean) as IndexMetadata[]
      results.push(...batch)
    }
    return this.sortByCreatedAt(results)
  }

  async getIndex(namespace: string): Promise<IndexMetadata | null> {
    try {
      const index = await this.redis.get<IndexMetadata>(`${this.INDEX_KEY_PREFIX}${namespace}`)
      console.log(`[Redis] Fetched index for namespace "${namespace}" at key "${this.INDEX_KEY_PREFIX}${namespace}":`, index ? 'Found' : 'Not Found')
      if (!index) {
        // Fallback check: check if it's in the main list but not individual key
        const allIndexes = await this.getIndexes()
        const foundInList = allIndexes.find(i => i.namespace === namespace)
        if (foundInList) {
            console.log(`[Redis] Found namespace "${namespace}" in main list but missing individual key. Restoring key.`)
            await this.redis.set(`${this.INDEX_KEY_PREFIX}${namespace}`, foundInList)
            return foundInList
        }
      }
      return index
    } catch (error) {
      console.error(`[Redis] Failed to get index for namespace "${namespace}"`, error)
      return null
    }
  }

  async saveIndex(index: IndexMetadata): Promise<void> {
    try {
      // Save individual index
      console.log(`[Redis] Saving index for namespace "${index.namespace}" to ${this.INDEX_KEY_PREFIX}${index.namespace}`)
      await this.redis.set(`${this.INDEX_KEY_PREFIX}${index.namespace}`, index)
      // Optional: keep a lightweight list for quick access (append without trimming)
      try {
        const list = (await this.redis.get<IndexMetadata[]>(this.INDEXES_KEY)) || []
        const existingIndex = list.findIndex((i) => i.namespace === index.namespace)
        if (existingIndex !== -1) {
          list[existingIndex] = index
        } else {
          list.unshift(index)
        }
        await this.redis.set(this.INDEXES_KEY, list)
      } catch (err) {
        console.error('[Redis] Failed to update cached indexes list (non-fatal)', err)
      }
    } catch (error) {
      console.error(`[Redis] Failed to save index for namespace "${index.namespace}"`, error)
      throw error
    }
  }

  async deleteIndex(namespace: string): Promise<void> {
    try {
      // Delete individual index
      await this.redis.del(`${this.INDEX_KEY_PREFIX}${namespace}`)
      
      // Update indexes list
      const indexes = await this.getIndexes()
      const filteredIndexes = indexes.filter(i => i.namespace !== namespace)
      await this.redis.set(this.INDEXES_KEY, filteredIndexes)
    } catch (error) {
      throw error
    }
  }
}

// Factory function to get the appropriate storage adapter
function getStorageAdapter(): StorageAdapter {
  console.log('[Storage] getStorageAdapter called - checking env vars...')
  console.log('[Storage] UPSTASH_REDIS_REST_URL:', process.env.UPSTASH_REDIS_REST_URL ? 'SET' : 'NOT SET')
  console.log('[Storage] UPSTASH_REDIS_REST_TOKEN:', process.env.UPSTASH_REDIS_REST_TOKEN ? 'SET' : 'NOT SET')
  console.log('[Storage] typeof window:', typeof window)
  
  // Use Redis if both environment variables are set
  if (process.env.UPSTASH_REDIS_REST_URL && process.env.UPSTASH_REDIS_REST_TOKEN) {
    console.log('[Storage] Using RedisStorageAdapter')
    return new RedisStorageAdapter()
  }
  
  // Check if we're on the server
  if (typeof window === 'undefined') {
    console.error('[Storage] On server but no Redis config - throwing error')
    throw new Error('No storage adapter available on the server. Please configure Redis by setting UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN environment variables.')
  }
  
  // Otherwise, use localStorage (only on client)
  console.log('[Storage] Using LocalStorageAdapter (client-side)')
  return new LocalStorageAdapter()
}

// Lazy initialization to avoid errors at module load time
let storage: StorageAdapter | null = null

function getStorage(): StorageAdapter | null {
  if (!storage) {
    try {
      storage = getStorageAdapter()
    } catch {
      // This is expected on the server without Redis configured
      return null
    }
  }
  return storage
}

export const getIndexes = async (): Promise<IndexMetadata[]> => {
  const adapter = getStorage()
  if (!adapter) {
    return []
  }
  
  try {
    return await adapter.getIndexes()
  } catch {
    console.error('Failed to get indexes')
    return []
  }
}

export const getIndex = async (namespace: string): Promise<IndexMetadata | null> => {
  const adapter = getStorage()
  if (!adapter) {
    return null
  }
  
  try {
    return await adapter.getIndex(namespace)
  } catch {
    console.error('Failed to get index')
    return null
  }
}

export const saveIndex = async (index: IndexMetadata): Promise<void> => {
  const adapter = getStorage()
  if (!adapter) {
    console.warn('No storage adapter available - index not saved')
    return
  }
  
  try {
    return await adapter.saveIndex(index)
  } catch {
    // Don't throw - this allows the app to continue functioning
    console.error('Failed to save index')
  }
}

export const deleteIndex = async (namespace: string): Promise<void> => {
  const adapter = getStorage()
  if (!adapter) {
    console.warn('No storage adapter available - index not deleted')
    return
  }
  
  try {
    return await adapter.deleteIndex(namespace)
  } catch {
    // Don't throw - this allows the app to continue functioning
    console.error('Failed to delete index')
  }
}