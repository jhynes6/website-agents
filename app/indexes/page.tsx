'use client'

import { useRouter } from 'next/navigation'
import Image from "next/image"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Globe, FileText, Database, ExternalLink, Trash2, Calendar, FolderOpen, AlertTriangle } from 'lucide-react'
import { toast } from "sonner"
import { useStorage } from "@/hooks/useStorage"
import { useEffect, useState } from 'react'
import { getBackendUrl } from "@/lib/backend"
import type { IndexMetadata } from "@/lib/storage"

interface ResourceLinks {
  client_data: string | null
  client_kb_data: string | null
  agent_directory: string | null
}

interface Warning {
  client_slug: string
  warning: string
}

interface SummaryWarnings {
  warnings: Warning[]
  generated_at: string
}

function getIndexLogoUrl(index: IndexMetadata): string | null {
  const explicit = index.metadata?.favicon
  if (typeof explicit === 'string' && explicit.trim()) {
    return explicit
  }
  const rawUrl = (index.url || '').trim()
  if (!rawUrl) return null
  try {
    const host = new URL(rawUrl).hostname
    if (!host) return null
    // Reliable favicon fallback for sites that don't provide favicon in crawl metadata.
    return `https://www.google.com/s2/favicons?domain=${encodeURIComponent(host)}&sz=128`
  } catch {
    return null
  }
}

export default function IndexesPage() {
  const router = useRouter()
  const { indexes, loading, deleteIndex, isUsingRedis } = useStorage()
  const [resourceLinks, setResourceLinks] = useState<ResourceLinks | null>(null)
  const [summaryWarnings, setSummaryWarnings] = useState<SummaryWarnings | null>(null)

  // Fetch resource links on mount
  useEffect(() => {
    const fetchResourceLinks = async () => {
      try {
        const response = await fetch(getBackendUrl('/api/mintagent/resource-links'))
        if (response.ok) {
          const links = await response.json()
          setResourceLinks(links)
        }
      } catch (error) {
        console.error('Failed to fetch resource links:', error)
      }
    }
    fetchResourceLinks()
  }, [])

  // Fetch summary warnings on mount
  useEffect(() => {
    const fetchWarnings = async () => {
      try {
        const response = await fetch(getBackendUrl('/api/mintagent/summary-warnings'))
        if (response.ok) {
          const data = await response.json()
          setSummaryWarnings(data)
        }
      } catch (error) {
        console.error('Failed to fetch summary warnings:', error)
      }
    }
    fetchWarnings()
  }, [])

  const handleSelectIndex = (index: IndexMetadata) => {
    const slug = index.clientSlug || index.namespace
    // Store the site info in session storage for the dashboard
    const siteInfo = {
      url: index.url,
      clientSlug: slug,
      pagesCrawled: index.pagesCrawled,
      crawlDate: index.createdAt,
      metadata: index.metadata || {},
      crawlComplete: true,
      fromIndex: true // Flag to indicate this is from the index list
    }
    
    sessionStorage.setItem('mintagent_current_data', JSON.stringify(siteInfo))
    
    // Navigate to the dashboard with clientSlug parameter
    router.push(`/dashboard?clientSlug=${slug}`)
  }

  const handleDeleteIndex = async (index: IndexMetadata, e: React.MouseEvent) => {
    e.stopPropagation()
    const slug = index.clientSlug || index.namespace
    
    if (confirm(`Delete chatbot for ${slug}?`)) {
      try {
        await deleteIndex(slug)
        toast.success('Chatbot deleted successfully')
      } catch {
        toast.error('Failed to delete chatbot')
        console.error('Failed to delete index')
      }
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric', 
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-4 max-w-7xl mx-auto font-inter">
      <div className="flex justify-between items-center mb-8">
        <div className="text-xl font-bold text-[#0E3D68]">
          MintAgents
        </div>
        <Button
          asChild
          variant="orange"
          size="sm"
        >
          <Link href="/">
            Create New Chatbot
          </Link>
        </Button>
      </div>

      <div className="mb-8">
        <h1 className="text-3xl font-semibold text-[#36322F] mb-2">Your Chatbots</h1>
        <p className="text-gray-600">
          View and manage all your chatbots
          {isUsingRedis && <span className="text-xs text-gray-500 ml-2">(using Redis storage)</span>}
        </p>
      </div>

      {/* System Warnings */}
      {summaryWarnings && summaryWarnings.warnings.length > 0 && (
        <div className="mb-6 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h3 className="font-semibold text-yellow-900 mb-2">System Warnings</h3>
              <ul className="space-y-1">
                {summaryWarnings.warnings.map((warning, idx) => (
                  <li key={idx} className="text-sm text-yellow-800">
                    <span className="font-mono font-semibold">{warning.client_slug}</span>: {warning.warning}
                  </li>
                ))}
              </ul>
              <p className="text-xs text-yellow-600 mt-2">
                Last checked: {new Date(summaryWarnings.generated_at).toLocaleString()}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Resource Links Buttons */}
      {resourceLinks && (
        <div className="mb-6 flex flex-wrap gap-3">
          {resourceLinks.client_data && (
            <Button
              asChild
              variant="outline"
              size="sm"
              className="gap-2"
            >
              <a href={resourceLinks.client_data} target="_blank" rel="noopener noreferrer">
                <FolderOpen className="w-4 h-4" />
                Client Data
                <ExternalLink className="w-3 h-3" />
              </a>
            </Button>
          )}
          {resourceLinks.client_kb_data && (
            <Button
              asChild
              variant="outline"
              size="sm"
              className="gap-2"
            >
              <a href={resourceLinks.client_kb_data} target="_blank" rel="noopener noreferrer">
                <Database className="w-4 h-4" />
                Client KB Data
                <ExternalLink className="w-3 h-3" />
              </a>
            </Button>
          )}
          {resourceLinks.agent_directory && (
            <Button
              asChild
              variant="outline"
              size="sm"
              className="gap-2"
            >
              <a href={resourceLinks.agent_directory} target="_blank" rel="noopener noreferrer">
                <FileText className="w-4 h-4" />
                Agent Directory
                <ExternalLink className="w-3 h-3" />
              </a>
            </Button>
          )}
        </div>
      )}

      {loading ? (
        <div className="text-center py-10">
          <p className="text-gray-600">Loading indexes...</p>
        </div>
      ) : indexes.length === 0 ? (
        <div className="text-center py-20">
          <Globe className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-gray-700 mb-2">No Chatbots Yet</h3>
          <p className="text-gray-600 mb-6">You haven&apos;t created any chatbots yet.</p>
          <Button asChild variant="orange">
            <Link href="/mintagent">
              Create Your First Chatbot
            </Link>
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
          {indexes.map((index) => {
            const slug = index.clientSlug || index.namespace
            const logoUrl = getIndexLogoUrl(index)
            return (
              <div
                key={slug}
                onClick={() => handleSelectIndex(index)}
                className="bg-white rounded-lg border border-gray-200 hover:shadow-md transition-shadow cursor-pointer group p-4"
              >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3 min-w-0">
                  {logoUrl ? (
                    <div className="w-10 h-10 rounded-lg bg-gray-50 border border-gray-200 overflow-hidden flex-shrink-0">
                      <Image
                        src={logoUrl}
                        alt="favicon"
                        width={40}
                        height={40}
                        className="w-full h-full object-contain"
                        onError={(e) => {
                          e.currentTarget.parentElement!.style.display = 'none';
                        }}
                      />
                    </div>
                  ) : (
                    <div className="w-10 h-10 rounded-lg bg-gray-100 border border-gray-200 flex items-center justify-center flex-shrink-0">
                      <Globe className="w-5 h-5 text-gray-400" />
                    </div>
                  )}
                  <div className="min-w-0">
                    <h3 className="text-base font-semibold text-[#36322F] group-hover:text-orange-600 transition-colors truncate">
                      {slug}
                    </h3>
                    <p className="text-xs text-gray-600 truncate">{index.url}</p>
                    {index.metadata?.description && (
                      <p className="text-xs text-gray-500 mt-2 line-clamp-2">
                        {index.metadata.description}
                      </p>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => handleDeleteIndex(index, e)}
                    className="opacity-0 group-hover:opacity-100 transition-opacity text-red-600 hover:text-red-700 hover:bg-red-50"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                  <ExternalLink className="w-5 h-5 text-gray-400 group-hover:text-gray-600 transition-colors" />
                </div>
              </div>

              <div className="flex items-center gap-4 mt-4 text-xs text-gray-600">
                <div className="flex items-center gap-1">
                  <FileText className="w-4 h-4" />
                  <span>{index.pagesCrawled} pages</span>
                </div>
                <div className="flex items-center gap-1">
                  <Database className="w-4 h-4" />
                  <span className="font-mono text-[11px]">{slug}</span>
                </div>
                <div className="flex items-center gap-1">
                  <Calendar className="w-4 h-4" />
                  <span>{formatDate(index.createdAt)}</span>
                </div>
              </div>
            </div>
            )
          })}
        </div>
      )}
    </div>
  )
}