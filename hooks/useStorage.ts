import { useState, useEffect } from 'react'
import { IndexMetadata } from '@/lib/storage'

export function useStorage() {
  const [indexes, setIndexes] = useState<IndexMetadata[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchIndexes = async () => {
    setLoading(true)
    setError(null)
    
    try {
      // Always try server API first; fallback to localStorage on failure
        const response = await fetch('/api/indexes')
        if (!response.ok) {
          throw new Error('Failed to fetch indexes')
        }
        const data = await response.json()
        setIndexes(data.indexes || [])
      return
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch indexes')
      // Fallback to localStorage
      const stored = typeof window !== 'undefined' ? localStorage.getItem('mintagent_indexes') : null
      setIndexes(stored ? JSON.parse(stored) : [])
    } finally {
      setLoading(false)
    }
  }

  const saveIndex = async (index: IndexMetadata) => {
    try {
      // Save via API endpoint; fallback to localStorage if it fails
        const response = await fetch('/api/indexes', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(index)
        })
        if (!response.ok) {
          throw new Error('Failed to save index')
        }
        // Refresh indexes
        await fetchIndexes()
    } catch (err) {
      // Fallback to localStorage
        const currentIndexes = [...indexes]
        const existingIndex = currentIndexes.findIndex(i => i.namespace === index.namespace)
        
        if (existingIndex !== -1) {
          currentIndexes[existingIndex] = index
        } else {
          currentIndexes.unshift(index)
        }
        
        // Keep only the last 50 indexes
        const limitedIndexes = currentIndexes.slice(0, 50)
      if (typeof window !== 'undefined') {
        localStorage.setItem('mintagent_indexes', JSON.stringify(limitedIndexes))
      }
      setIndexes(limitedIndexes)
    }
  }

  const deleteIndex = async (namespace: string) => {
    try {
      // Delete via API endpoint; fallback to localStorage if it fails
        const response = await fetch(`/api/indexes?namespace=${namespace}`, {
          method: 'DELETE'
        })
        if (!response.ok) {
          throw new Error('Failed to delete index')
        }
        // Refresh indexes
        await fetchIndexes()
    } catch (err) {
        // Delete from localStorage
        const filteredIndexes = indexes.filter(i => i.namespace !== namespace)
      if (typeof window !== 'undefined') {
        localStorage.setItem('mintagent_indexes', JSON.stringify(filteredIndexes))
      }
      setIndexes(filteredIndexes)
    }
  }

  useEffect(() => {
    fetchIndexes()
  }, [])

  return {
    indexes,
    loading,
    error,
    saveIndex,
    deleteIndex,
    refresh: fetchIndexes,
    isUsingRedis: true // We now always attempt server API; flag true to reflect that path
  }
}