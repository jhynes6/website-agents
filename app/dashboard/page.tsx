'use client'

import { useState, useEffect, useRef, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Send, Globe, Copy, Check, FileText, Database, ArrowLeft, ExternalLink, BookOpen, ChevronDown, ChevronUp } from 'lucide-react'
import Image from 'next/image'
// Removed useChat - using custom implementation
import { toast } from "sonner"
import { buildApiHeaders, getBackendUrl } from "@/lib/backend"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

interface Source {
  url: string
  title: string
  snippet: string
}

interface SiteData {
  url: string
  clientSlug: string
  index?: string
  pagesCrawled: number
  pages?: number
  chunks?: number
  metadata: {
    title: string
    description: string
    favicon?: string
    ogImage?: string
    indexName?: string
  }
  agent?: {
    agentUuid: string
    agentName: string
    endpointUrl: string
    hasApiKey: boolean
    region: string
    model: string
    retrievalMethod?: string
  }
  crawlId?: string
  crawlComplete?: boolean
  crawlDate?: string
  createdAt?: string
  namespace?: string // Keep optional for compat if needed, but primary is clientSlug
}

// Simple markdown renderer component
function MarkdownContent({ content, onSourceClick, isStreaming = false }: { content: string; onSourceClick?: (index: number) => void; isStreaming?: boolean }) {
  // Simple markdown parsing
  const parseMarkdown = (text: string) => {
    // First, handle code blocks to prevent other parsing inside them
    const codeBlocks: string[] = [];
    let parsed = text.replace(/```([\s\S]*?)```/g, (_, code) => {
      const placeholder = `__CODE_BLOCK_${codeBlocks.length}__`;
      codeBlocks.push(`<pre class="bg-gray-50 border border-gray-200 p-4 rounded-lg overflow-x-auto my-4 text-sm"><code>${code.trim()}</code></pre>`);
      return placeholder;
    });
    
    // Handle inline code
    parsed = parsed.replace(/`([^`]+)`/g, '<code class="bg-orange-50 text-orange-600 px-1.5 py-0.5 rounded text-sm font-mono">$1</code>');
    
    // Handle links [text](url) - must come before citations
    parsed = parsed.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" class="text-orange-600 hover:text-orange-700 underline">$1</a>');
    
    // Handle citations [1], [2], etc.
    parsed = parsed.replace(/\[(\d+)\]/g, (_, num) => {
      return `<sup class="citation text-orange-600 cursor-pointer hover:text-orange-700 font-medium" data-citation="${num}">[${num}]</sup>`;
    });
    
    // Bold text
    parsed = parsed.replace(/\*\*(.+?)\*\*/g, '<strong class="font-semibold text-gray-900">$1</strong>');
    
    // Italic text  
    parsed = parsed.replace(/\*(.+?)\*/g, '<em>$1</em>');
    
    // Split into lines for processing
    const lines = parsed.split('\n');
    const processedLines = [];
    let inList = false;
    let listType = '';
    let inParagraph = false;
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      const nextLine = i < lines.length - 1 ? lines[i + 1].trim() : '';
      
      // Headers
      if (line.match(/^#{1,3}\s/)) {
        if (inParagraph) {
          processedLines.push('</p>');
          inParagraph = false;
        }
        if (line.match(/^###\s(.+)$/)) {
          processedLines.push(line.replace(/^###\s(.+)$/, '<h3 class="text-base font-semibold mt-4 mb-2 text-gray-900">$1</h3>'));
        } else if (line.match(/^##\s(.+)$/)) {
          processedLines.push(line.replace(/^##\s(.+)$/, '<h2 class="text-lg font-semibold mt-5 mb-3 text-gray-900">$1</h2>'));
        } else if (line.match(/^#\s(.+)$/)) {
          processedLines.push(line.replace(/^#\s(.+)$/, '<h1 class="text-xl font-bold mt-6 mb-3 text-gray-900">$1</h1>'));
        }
        continue;
      }
      
      // Lists
      const bulletMatch = line.match(/^[-*]\s(.+)$/);
      const numberedMatch = line.match(/^(\d+)\.\s(.+)$/);
      
      if (bulletMatch || numberedMatch) {
        if (inParagraph) {
          processedLines.push('</p>');
          inParagraph = false;
        }
        
        const newListType = bulletMatch ? 'ul' : 'ol';
        if (!inList) {
          listType = newListType;
          processedLines.push(`<${listType} class="${listType === 'ul' ? 'list-disc' : 'list-decimal'} ml-6 my-3 space-y-1">`);
          inList = true;
        } else if (listType !== newListType) {
          processedLines.push(`</${listType}>`);
          listType = newListType;
          processedLines.push(`<${listType} class="${listType === 'ul' ? 'list-disc' : 'list-decimal'} ml-6 my-3 space-y-1">`);
        }
        
        const content = bulletMatch ? bulletMatch[1] : numberedMatch![2];
        processedLines.push(`<li class="text-gray-700 leading-relaxed">${content}</li>`);
        continue;
      } else if (inList && line === '') {
        processedLines.push(`</${listType}>`);
        inList = false;
        continue;
      }
      
      // Empty lines
      if (line === '') {
        if (inParagraph) {
          processedLines.push('</p>');
          inParagraph = false;
        }
        if (inList) {
          processedLines.push(`</${listType}>`);
          inList = false;
        }
        continue;
      }
      
      // Regular text - start new paragraph if needed
      if (!inParagraph && !inList && !line.startsWith('<')) {
        processedLines.push('<p class="text-gray-700 leading-relaxed mb-3">');
        inParagraph = true;
      }
      
      // Add line with space if in paragraph
      if (inParagraph) {
        processedLines.push(line + (nextLine && !nextLine.match(/^[-*#]|\d+\./) ? ' ' : ''));
      } else {
        processedLines.push(line);
      }
    }
    
    // Close any open tags
    if (inParagraph) {
      processedLines.push('</p>');
    }
    if (inList) {
      processedLines.push(`</${listType}>`);
    }
    
    parsed = processedLines.join('\n');
    
    // Restore code blocks
    codeBlocks.forEach((block, index) => {
      parsed = parsed.replace(`__CODE_BLOCK_${index}__`, block);
    });
    
    return parsed;
  };

  useEffect(() => {
    // Add click handlers for citations
    const citations = document.querySelectorAll('.citation');
    citations.forEach(citation => {
      citation.addEventListener('click', (e) => {
        const citationNum = parseInt((e.target as HTMLElement).getAttribute('data-citation') || '0');
        if (onSourceClick && citationNum > 0) {
          onSourceClick(citationNum - 1);
        }
      });
    });

    return () => {
      citations.forEach(citation => {
        citation.removeEventListener('click', () => {});
      });
    };
  }, [content, onSourceClick]);

  return (
    <div className="relative">
      <div 
        className="prose prose-sm max-w-none prose-gray prose-headings:text-gray-900 prose-p:text-gray-700 prose-strong:text-gray-900 prose-code:text-orange-600 prose-code:bg-orange-50 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-pre:bg-gray-100 prose-pre:text-gray-800 prose-li:text-gray-700 prose-a:text-orange-600 prose-a:no-underline hover:prose-a:underline"
        dangerouslySetInnerHTML={{ __html: parseMarkdown(content) }}
      />
      {isStreaming && (
        <span className="inline-block w-1 h-4 bg-gray-600 animate-pulse ml-1" />
      )}
    </div>
  );
}

function DashboardContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [siteData, setSiteData] = useState<SiteData | null>(null)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [copiedItem, setCopiedItem] = useState<string | null>(null)
  const [messages, setMessages] = useState<Array<{ role: 'user' | 'assistant'; content: string; sources?: Source[] }>>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [agentEnsuring, setAgentEnsuring] = useState(false)
  const [agentReady, setAgentReady] = useState(false)
  const [showApiModal, setShowApiModal] = useState(false)
  const [activeTab, setActiveTab] = useState<'curl' | 'javascript' | 'python' | 'openai-js' | 'openai-python'>('curl')
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const [autoScroll, setAutoScroll] = useState(true)
  const [stats, setStats] = useState<{
    total: number
    by_content_type: Record<string, number>
    by_document_source: Record<string, number>
  } | null>(null)
  const [clientDetails, setClientDetails] = useState<{
    kb_data: any
    agent_data: any
  } | null>(null)
  const [showKbDetailsModal, setShowKbDetailsModal] = useState(false)
  const [showAgentDetailsModal, setShowAgentDetailsModal] = useState(false)

  useEffect(() => {
    const el = scrollAreaRef.current
    if (!el) return
    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = el
      const atBottom = scrollHeight - scrollTop - clientHeight < 20
      setAutoScroll(atBottom)
    }
    el.addEventListener('scroll', handleScroll)
    return () => {
      el.removeEventListener('scroll', handleScroll)
    }
  }, [])

  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || !siteData) return
    if (!agentReady) {
      toast.message(agentEnsuring ? 'Preparing agent…' : 'Agent not ready yet')
      return
    }

    let processedInput = input.trim()
    
    // Check if the input looks like a URL without protocol
    const urlPattern = /^(?!https?:\/\/)([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(\/.*)?$/
    if (urlPattern.test(processedInput)) {
      processedInput = 'https://' + processedInput
    }

    const userMessage = { role: 'user' as const, content: processedInput }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)
    
    try {
      // Extract index from clientSlug if not provided
      const indexName = siteData.index || siteData.metadata?.indexName || 
        (siteData.clientSlug ? siteData.clientSlug.replace(/-\d+$/, '') : undefined)
      
      const response = await fetch(getBackendUrl('/api/firestarter/query'), {
        method: 'POST',
        headers: buildApiHeaders(),
        body: JSON.stringify({
          messages: [userMessage],
          clientSlug: siteData.clientSlug,
          index: indexName,
          agentType: searchParams.get('agentType') || 'inbox_manager',
          stream: true
        })
      })

      if (!response.ok) {
        throw new Error('Failed to get response')
      }

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      let sources: Source[] = []
      let content = ''
      let hasStartedStreaming = false

      if (!reader) throw new Error('No response body')

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value)
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (line.trim() === '') continue
          
          
          // Handle Vercel AI SDK streaming format
          if (line.startsWith('0:')) {
            // Text content chunk
            const textContent = line.slice(2)
            if (textContent.startsWith('"') && textContent.endsWith('"')) {
              const text = JSON.parse(textContent)
              content += text
              
              // Add assistant message on first content
              if (!hasStartedStreaming) {
                hasStartedStreaming = true
                setMessages(prev => [...prev, { 
                  role: 'assistant' as const, 
                  content: content, 
                  sources: sources 
                }])
              } else {
                // Update the last message with new content
                setMessages(prev => {
                  const newMessages = [...prev]
                  const lastMessage = newMessages[newMessages.length - 1]
                  if (lastMessage && lastMessage.role === 'assistant') {
                    lastMessage.content = content
                    lastMessage.sources = sources
                  }
                  return newMessages
                })
              }
              scrollToBottom()
            }
          } else if (line.startsWith('8:')) {
            // Streaming data chunk (sources, etc)
            try {
              const jsonStr = line.slice(2)
              const data = JSON.parse(jsonStr)
              
              // Check if this is the sources data
              if (data && typeof data === 'object' && 'sources' in data) {
                sources = data.sources
                
                // Update the last message with sources
                setMessages(prev => {
                  const newMessages = [...prev]
                  const lastMessage = newMessages[newMessages.length - 1]
                  if (lastMessage && lastMessage.role === 'assistant') {
                    lastMessage.sources = sources
                  }
                  return newMessages
                })
              } else if (Array.isArray(data)) {
                // Legacy format support
                const sourcesData = data.find(item => item && typeof item === 'object' && 'type' in item && item.type === 'sources')
                if (sourcesData && sourcesData.sources) {
                  sources = sourcesData.sources
                }
              }
            } catch {
              console.error('Failed to parse streaming data')
            }
          } else if (line.startsWith('e:') || line.startsWith('d:')) {
            // End metadata - we can ignore these
          }
        }
      }
    } catch (error) {
      toast.error('Failed to get response')
      console.error('Query failed:', error)
      console.error('Error details:', error instanceof Error ? error.message : String(error))
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    // Get clientSlug from URL params (fallback to namespace for compat)
    const clientSlugParam = searchParams.get('clientSlug') || searchParams.get('namespace')
    const agentTypeParam = searchParams.get('agentType') || 'inbox_manager'
    console.log(`[Dashboard] Init with clientSlug: ${clientSlugParam}`)
    
    if (clientSlugParam) {
      // Try to fetch index data from the database via API first
      console.log(`[Dashboard] Fetching index for: ${clientSlugParam}`)
      fetch(`/api/indexes?clientSlug=${clientSlugParam}`)
        .then(async (res) => {
          if (!res.ok) {
            const text = await res.text()
            console.error(`[Dashboard] Fetch failed: ${res.status} ${res.statusText}`, text)
            throw new Error('Failed to fetch index from API')
          }
          const data = await res.json()
          console.log(`[Dashboard] Fetch success:`, data)
          if (data.index) {
            setSiteData(data.index)
            sessionStorage.setItem('firestarter_current_data', JSON.stringify(data.index))
            setMessages([])
            setAgentReady(false)
            
            // Extract index from clientSlug if not provided
            const indexName = data.index.index || data.index.metadata?.indexName || 
              (data.index.clientSlug ? data.index.clientSlug.replace(/-\d+$/, '') : undefined)
            
            // Fetch stats for this clientSlug
            fetchStats(data.index.clientSlug, indexName)

            // Ensure per-client agent exists so chat is ready immediately
            setAgentEnsuring(true)
            fetch(getBackendUrl('/api/firestarter/ensure-agent'), {
              method: 'POST',
              headers: buildApiHeaders(),
              body: JSON.stringify({ clientSlug: data.index.clientSlug, agentType: agentTypeParam })
            })
              .then(async (res) => {
                if (!res.ok) {
                  const text = await res.text()
                  throw new Error(text || 'ensure-agent failed')
                }
                return res.json()
              })
              .then(() => setAgentReady(true))
              .catch((err) => {
                console.error('[Dashboard] ensure-agent failed:', err)
                const msg = err instanceof Error ? err.message : String(err)
                toast.error(`Failed to prepare agent: ${msg.slice(0, 140)}`)
                setAgentReady(false)
              })
              .finally(() => setAgentEnsuring(false))
            return
          } else {
            throw new Error('Index not found in API response')
          }
        })
        .catch((err) => {
          console.error('[Dashboard] API fetch failed, falling back to localStorage:', err)
          
          // Fallback to localStorage (for when Redis isn't configured)
          const storedIndexes = localStorage.getItem('firestarter_indexes')
          if (storedIndexes) {
            const indexes = JSON.parse(storedIndexes)
            const matchingIndex = indexes.find((idx: { clientSlug: string, namespace?: string }) => 
                idx.clientSlug === clientSlugParam || idx.namespace === clientSlugParam
            )
            if (matchingIndex) {
              console.log('[Dashboard] Found in localStorage:', matchingIndex)
              setSiteData(matchingIndex)
              sessionStorage.setItem('firestarter_current_data', JSON.stringify(matchingIndex))
              setMessages([])
              setAgentReady(false)
              
              const indexName = matchingIndex.index || matchingIndex.metadata?.indexName || 
                (matchingIndex.clientSlug ? matchingIndex.clientSlug.replace(/-\d+$/, '') : undefined)
              
              // Fetch stats for this clientSlug
              fetchStats(matchingIndex.clientSlug || matchingIndex.namespace, indexName)

              // Ensure per-client agent exists so chat is ready immediately
              setAgentEnsuring(true)
              fetch(getBackendUrl('/api/firestarter/ensure-agent'), {
                method: 'POST',
                headers: buildApiHeaders(),
                body: JSON.stringify({ clientSlug: matchingIndex.clientSlug || matchingIndex.namespace, agentType: agentTypeParam })
              })
                .then(async (res) => {
                  if (!res.ok) {
                    const text = await res.text()
                    throw new Error(text || 'ensure-agent failed')
                  }
                  return res.json()
                })
                .then(() => setAgentReady(true))
                .catch((err) => {
                  console.error('[Dashboard] ensure-agent failed:', err)
                  const msg = err instanceof Error ? err.message : String(err)
                  toast.error(`Failed to prepare agent: ${msg.slice(0, 140)}`)
                  setAgentReady(false)
                })
                .finally(() => setAgentEnsuring(false))
              return
            }
          }
          
          // If still not found, redirect to indexes page
          console.error('[Dashboard] Index not found in API or localStorage, redirecting')
          router.push('/indexes')
        })
      } else {
        console.log(`[Dashboard] No clientSlug param, redirecting`)
        router.push('/indexes')
      }
  }, [router, searchParams])

  const fetchStats = async (namespace: string, indexName?: string) => {
    try {
      console.log('[Dashboard] Fetching stats for namespace:', namespace, 'index:', indexName)
      const response = await fetch(getBackendUrl('/api/firestarter/stats'), {
        method: 'POST',
        headers: buildApiHeaders(),
        body: JSON.stringify({ namespace, index: indexName })
      })
      
      if (response.ok) {
        const data = await response.json()
        console.log('[Dashboard] Stats received:', data)
        setStats(data)
    } else {
        const errorText = await response.text()
        console.error('[Dashboard] Stats fetch failed:', response.status, errorText)
      }
    } catch (error) {
      console.error('[Dashboard] Failed to fetch stats:', error)
    }
  }

  const fetchClientDetails = async (clientSlug: string) => {
    try {
      console.log('[Dashboard] Fetching client details for:', clientSlug)
      const response = await fetch(getBackendUrl(`/api/firestarter/client-details/${clientSlug}`))
      
      if (response.ok) {
        const data = await response.json()
        console.log('[Dashboard] Client details received:', data)
        setClientDetails(data)
      } else {
        console.error('[Dashboard] Client details fetch failed:', response.status)
      }
    } catch (error) {
      console.error('[Dashboard] Failed to fetch client details:', error)
    }
  }

  // Fetch client details when siteData is available
  useEffect(() => {
    if (siteData?.clientSlug) {
      fetchClientDetails(siteData.clientSlug)
    }
  }, [siteData?.clientSlug])

  const scrollToBottom = () => {
    if (scrollAreaRef.current && autoScroll) {
      scrollAreaRef.current.scrollTo({
        top: scrollAreaRef.current.scrollHeight,
        behavior: 'smooth'
      })
    }
  }

  const handleDelete = () => {
    // Remove from localStorage
    const storedIndexes = localStorage.getItem('firestarter_indexes')
    if (storedIndexes && siteData) {
      const indexes = JSON.parse(storedIndexes)
      const updatedIndexes = indexes.filter((idx: { clientSlug: string }) => idx.clientSlug !== siteData.clientSlug)
      localStorage.setItem('firestarter_indexes', JSON.stringify(updatedIndexes))
    }
    
    sessionStorage.removeItem('firestarter_current_data')
    router.push('/indexes')
  }

  const copyToClipboard = (text: string, itemId: string) => {
    navigator.clipboard.writeText(text)
    setCopiedItem(itemId)
    setTimeout(() => setCopiedItem(null), 2000)
  }


  if (!siteData) {
    return (
      <div className="min-h-screen bg-[#FBFAF9] flex items-center justify-center">
        <div className="text-gray-600">Loading...</div>
      </div>
    )
  }
  

  const modelName = `firecrawl-${siteData.clientSlug}`
  
  // Get agent endpoint URL if available
  const agentEndpointUrl = siteData.agent?.endpointUrl || null
  const agentApiUrl = agentEndpointUrl 
    ? `${agentEndpointUrl}/api/v1/chat/completions` 
    : `${typeof window !== 'undefined' ? `${window.location.protocol}//${window.location.host}` : 'http://localhost:3001'}/api/v1/chat/completions`
  
  const apiKeyPlaceholder = siteData.agent?.hasApiKey 
    ? 'YOUR_AGENT_API_KEY' 
    : 'YOUR_FIRESTARTER_API_KEY'
  
  const curlCommand = `# Standard request
curl ${agentApiUrl} \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer ${apiKeyPlaceholder}" \\
  -d '{
    "model": "n/a",
    "messages": [
      {"role": "user", "content": "Your question here"}
    ]
  }'

# Streaming request
curl ${agentApiUrl} \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer ${apiKeyPlaceholder}" \\
  -N \\
  -d '{
    "model": "n/a",
    "messages": [
      {"role": "user", "content": "Your question here"}
    ],
    "stream": true
  }'`
  
  const openaiJsCode = `import OpenAI from 'openai';

const openai = new OpenAI({
  apiKey: '${apiKeyPlaceholder}',
  baseURL: '${agentEndpointUrl}/api/v1',
});

const completion = await openai.chat.completions.create({
  model: 'n/a', // Model is defined in the agent
  messages: [
    { role: 'user', content: 'Your question here' }
  ],
});

console.log(completion.choices[0].message.content);

// Streaming example
const stream = await openai.chat.completions.create({
  model: 'n/a',
  messages: [
    { role: 'user', content: 'Your question here' }
  ],
  stream: true,
});

for await (const chunk of stream) {
  process.stdout.write(chunk.choices[0]?.delta?.content || '');
}`
  
  const openaiPythonCode = `from openai import OpenAI

client = OpenAI(
    api_key="${apiKeyPlaceholder}",
    base_url="${agentEndpointUrl}/api/v1"
)

completion = client.chat.completions.create(
    model="n/a",  # Model is defined in the agent
    messages=[
        {"role": "user", "content": "Your question here"}
    ]
)

print(completion.choices[0].message.content)

# Streaming example
stream = client.chat.completions.create(
    model="n/a",
    messages=[
        {"role": "user", "content": "Your question here"}
    ],
    stream=True
)

for chunk in stream:
    if chunk.choices[0].delta.content is not None:
        print(chunk.choices[0].delta.content, end="")`
  
  const jsCode = `// Using fetch API
const response = await fetch('${agentApiUrl}', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer ${apiKeyPlaceholder}'
  },
  body: JSON.stringify({
    model: 'n/a',
    messages: [
      { role: 'user', content: 'Your question here' }
    ]
  })
});

const data = await response.json();
console.log(data.choices[0].message.content);`
  
  const pythonCode = `import requests

response = requests.post(
    '${agentApiUrl}',
    headers={
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ${apiKeyPlaceholder}'
    },
    json={
        'model': 'n/a',
        'messages': [
            {'role': 'user', 'content': 'Your question here'}
        ]
    }
)

data = response.json()
print(data['choices'][0]['message']['content'])`
  

  return (
    <div className="min-h-screen bg-[#FBFAF9]">
      {/* Header */}
      <div className="border-b border-gray-200 bg-white">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => router.push('/indexes')}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <ArrowLeft className="w-5 h-5 text-gray-600" />
              </button>
              <div className="flex items-center gap-3">
                {siteData.metadata.favicon ? (
                  <Image 
                    src={siteData.metadata.favicon} 
                    alt={siteData.metadata.title}
                    width={32}
                    height={32}
                    className="w-8 h-8"
                    onError={(e) => {
                      e.currentTarget.style.display = 'none';
                      e.currentTarget.parentElement?.querySelector('.fallback-icon')?.classList.remove('hidden');
                    }}
                  />
                ) : (
                  <div className="w-8 h-8 bg-gray-100 rounded-lg flex items-center justify-center">
                    <Globe className="w-5 h-5 text-gray-400" />
                  </div>
                )}
                <div>
                  <h1 className="text-xl font-semibold text-[#36322F]">
                    {siteData.metadata.title.length > 50 
                      ? siteData.metadata.title.substring(0, 47) + '...' 
                      : siteData.metadata.title}
                  </h1>
                  <p className="text-sm text-gray-600">{siteData.url}</p>
                </div>
              </div>
            </div>
            
            <Button
              onClick={() => setShowDeleteModal(true)}
              variant="code"
              size="sm"
            >
              Delete
            </Button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="flex flex-col lg:flex-row gap-6 lg:h-[600px]">
          {/* Stats Cards - Show at top on mobile */}
          <div className="lg:w-1/4 flex flex-col gap-4 lg:h-full lg:overflow-y-auto">
            <div className="relative bg-white rounded-xl border border-gray-200 overflow-hidden flex-shrink-0">
              {/* OG Image Background */}
              {siteData.metadata.ogImage && (
                <div className="absolute inset-0 z-0">
                  <Image 
                    src={siteData.metadata.ogImage} 
                    alt=""
                    fill
                    className="object-contain opacity-30"
                    onError={(e) => {
                      e.currentTarget.parentElement!.style.display = 'none';
                    }}
                  />
                  <div className="absolute inset-0 bg-gradient-to-br from-white/70 via-white/60 to-white/70"></div>
                </div>
              )}
              
              <div className="relative z-10 p-6 h-full flex flex-col">
                <div className="mb-4">
                  <h2 className="text-lg font-semibold text-[#36322F]">
                    {siteData.metadata.title.length > 30 
                      ? siteData.metadata.title.substring(0, 27) + '...' 
                      : siteData.metadata.title}
                  </h2>
                  <p className="text-xs text-gray-600">Knowledge Base</p>
                </div>
                
                <div className="space-y-2 flex-1">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-gray-700">
                      <FileText className="w-4 h-4" />
                      <span className="text-sm font-medium">Pages</span>
                    </div>
                    <span className="text-lg font-semibold text-[#36322F]">{siteData.pages || siteData.pagesCrawled || 0}</span>
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-gray-700">
                      <Database className="w-4 h-4" />
                      <span className="text-sm font-medium">Chunks</span>
                    </div>
                    <span className="text-lg font-semibold text-[#36322F]">{siteData.chunks || Math.round((siteData.pages || siteData.pagesCrawled || 0) * 3)}</span>
                  </div>
                  
                    <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-gray-700">
                      <Globe className="w-4 h-4" />
                      <span className="text-sm font-medium">Client</span>
                    </div>
                    <span className="text-xs font-mono text-gray-800 break-all">{siteData.clientSlug}</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl p-6 border border-gray-200 flex flex-col flex-shrink-0">
              <h2 className="text-lg font-semibold text-[#36322F] mb-4">Agent</h2>
              {siteData.agent ? (
                <div className="space-y-3 flex-1">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">Status</span>
                    <span className="text-sm font-medium text-green-600">Active</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">Model</span>
                    <span className="text-xs font-mono text-gray-800">{siteData.agent.model || 'gpt-4o-mini'}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">Region</span>
                    <span className="text-xs font-mono text-gray-800">{siteData.agent.region || 'tor1'}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">Retrieval</span>
                    <span className="text-xs text-gray-800">{siteData.agent.retrievalMethod?.replace('RETRIEVAL_METHOD_', '').toLowerCase() || 'rewrite'}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">API Key</span>
                    <span className={`text-xs font-medium ${siteData.agent.hasApiKey ? 'text-green-600' : 'text-red-600'}`}>
                      {siteData.agent.hasApiKey ? '✓ Configured' : '✗ Missing'}
                    </span>
                  </div>
                </div>
              ) : (
                <div className="flex-1 flex items-center justify-center">
                  <p className="text-sm text-gray-500">No agent configured</p>
                </div>
              )}
            </div>

            {/* Agent Details Button - Left Side */}
            {clientDetails?.agent_data && (
              <div className="bg-[#0E3D68] rounded-xl overflow-hidden flex-shrink-0">
                <button
                  onClick={() => setShowAgentDetailsModal(true)}
                  className="w-full px-6 py-4 flex items-center justify-between hover:bg-[#0a2d4d] transition-colors"
                >
                  <h3 className="text-sm font-semibold text-white">View Agent Details</h3>
                  <ExternalLink className="w-4 h-4 text-white" />
                </button>
              </div>
            )}

            <div className="bg-white rounded-xl p-6 border border-gray-200 flex flex-col flex-shrink-0">
              <h2 className="text-lg font-semibold text-[#36322F] mb-4">Quick Start</h2>
              <div className="space-y-4 flex-1">
                <div>
                  <h3 className="text-sm font-medium text-gray-700 mb-2">1. Test in Dashboard</h3>
                  <p className="text-xs text-gray-600">Use the chat panel to test responses and refine your queries</p>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-gray-700 mb-2">2. Get API Access</h3>
                  <p className="text-xs text-gray-600">Click below to see integration code in multiple languages</p>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-gray-700 mb-2">3. Deploy Anywhere</h3>
                  <p className="text-xs text-gray-600">Deploy chatbot script OR OpenAI-compatible endpoint API</p>
                </div>
              </div>
              <div className="mt-8">
                <Button
                  onClick={() => setShowApiModal(true)}
                  variant="orange"
                  className="w-full"
                >
                  View Integration Code
                </Button>
              </div>
            </div>
          </div>

          {/* Chat Panel and Sources - Show below on mobile */}
          <div className="lg:w-3/4 lg:h-full">
            <div className="flex flex-col lg:flex-row gap-6 lg:h-full">
              {/* Chat Panel */}
              <div className="w-full lg:w-2/3 bg-white rounded-xl border border-gray-200 flex flex-col overflow-hidden h-[500px] lg:h-full">
                {!agentReady && (
                  <div className="px-6 py-3 border-b border-gray-100 text-sm text-gray-600">
                    {agentEnsuring ? 'Preparing agent for this client…' : 'Agent not ready yet.'}
                  </div>
                )}
                <div ref={scrollAreaRef} className="flex-1 overflow-y-auto p-6 pb-0">
                  {messages.length === 0 && (
                    <div className="text-center py-20">
                      <div className="mb-4">
                        {siteData.metadata.favicon && (
                          <Image 
                            src={siteData.metadata.favicon} 
                            alt={siteData.metadata.title}
                            width={64}
                            height={64}
                            className="w-16 h-16 mx-auto mb-4 opacity-50"
                            onError={(e) => {
                              e.currentTarget.style.display = 'none';
                            }}
                          />
                        )}
                      </div>
                      <h3 className="text-lg font-semibold text-[#36322F] mb-2">
                        Chat with {siteData.metadata.title}
                      </h3>
                      <p className="text-gray-600">
                        Ask anything about their {siteData.pagesCrawled} indexed pages
                      </p>
                    </div>
                  )}
                
                  {messages.map((message, index) => (
              <div
                key={index}
                className={`mb-6 ${message.role === 'user' ? 'flex justify-end' : 'flex justify-start'}`}
              >
                <div className={`max-w-[85%] ${message.role === 'user' ? 'ml-12' : 'mr-12'}`}>
                  <div
                    className={`px-5 py-4 rounded-2xl ${
                      message.role === 'user'
                        ? 'bg-[#0E3D68] text-white'
                        : 'bg-white border border-gray-200 text-gray-800 shadow-sm'
                    }`}
                  >
                    {message.role === 'user' ? (
                      <p className="text-[15px] leading-relaxed">{message.content}</p>
                    ) : (
                      <div className="prose prose-sm max-w-none prose-gray">
                        <MarkdownContent 
                          content={message.content} 
                          isStreaming={isLoading && index === messages.length - 1 && message.content !== ''}
                        />
                      </div>
                    )}
                  </div>
                
                </div>
              </div>
              ))}
              
              {isLoading && messages[messages.length - 1]?.role !== 'assistant' && (
                <div className="flex justify-start mb-6">
                  <div className="max-w-[85%] mr-12">
                    <div className="px-5 py-4 rounded-2xl bg-white border border-gray-200 text-gray-800 shadow-sm">
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 bg-orange-500 rounded-full animate-pulse" />
                        <div className="w-2 h-2 bg-orange-500 rounded-full animate-pulse delay-75" />
                        <div className="w-2 h-2 bg-orange-500 rounded-full animate-pulse delay-150" />
                      </div>
                    </div>
                  </div>
                </div>
              )}
                </div>
                
                
                <form onSubmit={handleSubmit} className="p-4 border-t border-gray-200">
                  <div className="relative">
                    <Input
                      type="text"
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      placeholder={`Ask about ${siteData.metadata.title}...`}
                      className="w-full pr-12 placeholder:text-gray-400"
                      disabled={isLoading}
                    />
                    <button
                      type="submit"
                      disabled={isLoading || !input.trim()}
                      className="absolute right-2 top-1/2 -translate-y-1/2 p-2 text-orange-600 hover:text-orange-700 disabled:opacity-50 transition-colors"
                    >
                      <Send className="w-4 h-4" />
                    </button>
                  </div>
                </form>
              </div>
              
              {/* Sources Panel - Shows on right side when available */}
              <div className="hidden lg:block lg:w-1/3">
                <div className="bg-white rounded-xl p-6 border border-gray-200 flex flex-col h-full overflow-hidden">
                  {(() => {
                    const lastAssistantMessage = messages.filter(m => m.role === 'assistant').pop()
                    const hasSources = lastAssistantMessage?.sources && lastAssistantMessage.sources.length > 0
                    
                    if (hasSources) {
                      return (
                        <>
                          <div className="flex items-center justify-between mb-4 animate-fade-in">
                            <h2 className="text-lg font-semibold text-[#36322F] flex items-center gap-2">
                              <BookOpen className="w-5 h-5 text-orange-500" />
                              Sources
                            </h2>
                            <span className="text-xs text-gray-500 bg-orange-50 px-2 py-1 rounded-full">
                              {lastAssistantMessage.sources?.length || 0} references
                            </span>
                          </div>
                          
                          <div className="space-y-3 flex-1 overflow-y-auto">
                            {lastAssistantMessage.sources?.map((source, idx) => (
                              <a
                                key={idx}
                                href={source.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="block p-4 bg-gradient-to-br from-gray-50 to-gray-100 hover:from-orange-50 hover:to-orange-100 rounded-lg border border-gray-200 hover:border-orange-300 transition-all duration-300 group animate-fade-in hover:shadow-md"
                                style={{
                                  animationDelay: `${idx * 100}ms`,
                                  animationDuration: '0.5s',
                                  animationFillMode: 'both'
                                }}
                              >
                                <div className="flex items-start gap-3">
                                  <span className="text-sm font-medium text-orange-500 flex-shrink-0 bg-orange-100 w-8 h-8 rounded-full flex items-center justify-center">
                                    {idx + 1}
                                  </span>
                                  <div className="flex-1 min-w-0">
                                    <h4 className="text-sm font-medium text-gray-800 group-hover:text-orange-600 transition-colors line-clamp-2 mb-1">
                                      {source.title}
                                    </h4>
                                    {source.snippet && (
                                      <p className="text-xs text-gray-600 line-clamp-3 mb-2 leading-relaxed">
                                        {source.snippet}
                                      </p>
                                    )}
                                    <p className="text-xs text-gray-500 truncate flex items-center gap-1 group-hover:text-orange-500 transition-colors">
                                      <ExternalLink className="w-3 h-3" />
                                      {new URL(source.url).hostname}
                                    </p>
                                  </div>
                                </div>
                              </a>
                            ))}
                          </div>
                        </>
                      )
                    }
                    
                    // Default knowledge base view when no sources
                    return (
                      <>
                        <div className="flex items-center justify-between mb-4">
                          <h2 className="text-lg font-semibold text-[#36322F] flex items-center gap-2">
                            <Database className="w-5 h-5 text-gray-400" />
                            Knowledge Base
                          </h2>
                        </div>
                        
                        <div className="space-y-3 p-3 flex-1">
                          <div className="text-center py-8">
                            <div className="relative">
                              <Database className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                              <div className="absolute inset-0 flex items-center justify-center">
                                <div className="w-20 h-20 bg-gray-200 rounded-full animate-ping opacity-20"></div>
                              </div>
                            </div>
                            <p className="text-sm font-medium text-gray-700 mb-1">
                              {siteData.pagesCrawled} pages indexed
                            </p>
                            <p className="text-xs text-gray-500 mb-6">
                              Ready to answer questions about {siteData.metadata.title}
                            </p>
                            <div className="space-y-2 text-left">
                              <div className="flex items-center justify-between p-3 bg-gradient-to-r from-gray-50 to-gray-100 rounded-lg border border-gray-200">
                                <span className="text-xs text-gray-600">Total chunks</span>
                                <span className="text-xs font-medium text-gray-800 bg-white px-2 py-1 rounded">
                                  {Math.round(siteData.pagesCrawled * 3)}
                                </span>
                              </div>
                              <div className="flex items-center justify-between p-3 bg-gradient-to-r from-gray-50 to-gray-100 rounded-lg border border-gray-200">
                                <span className="text-xs text-gray-600">Crawl date</span>
                                <span className="text-xs font-medium text-gray-800 bg-white px-2 py-1 rounded">
                                  {(() => {
                                    const dateString = siteData.crawlDate || siteData.createdAt;
                                    return dateString ? new Date(dateString).toLocaleDateString() : 'N/A';
                                  })()}
                                </span>
                              </div>
                              <div className="flex items-center justify-between p-3 bg-gradient-to-r from-gray-50 to-gray-100 rounded-lg border border-gray-200">
                                <span className="text-xs text-gray-600">Namespace</span>
                                <span className="text-xs font-mono text-gray-800 truncate max-w-[140px] bg-white px-2 py-1 rounded">
                                  {siteData.clientSlug.split('-').slice(0, -1).join('.')}
                                </span>
                              </div>
                              
                              {/* Stats Breakdown */}
                              {stats && stats.total > 0 && (
                                <>
                                  <div className="mt-4 pt-4 border-t border-gray-200">
                                    <h4 className="text-xs font-semibold text-gray-700 mb-2">By Content Type</h4>
                                    <div className="space-y-1">
                                      {Object.entries(stats.by_content_type).map(([type, count]) => (
                                        <div key={type} className="flex items-center justify-between text-xs">
                                          <span className="text-gray-600 capitalize">{type.replace(/_/g, ' ')}</span>
                                          <span className="font-medium text-gray-800">{count}</span>
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                  
                                  <div className="mt-4 pt-4 border-t border-gray-200">
                                    <h4 className="text-xs font-semibold text-gray-700 mb-2">By Source</h4>
                                    <div className="space-y-1">
                                      {Object.entries(stats.by_document_source).map(([source, count]) => (
                                        <div key={source} className="flex items-center justify-between text-xs">
                                          <span className="text-gray-600 capitalize">{source}</span>
                                          <span className="font-medium text-gray-800">{count}</span>
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                </>
                              )}
                            </div>
                          </div>
                        </div>
                      </>
                    )
                  })()}
                </div>

                {/* KB Details Button - Right Side */}
                {clientDetails?.kb_data && (
                  <div className="mt-4 bg-[#0E3D68] rounded-xl overflow-hidden">
                    <button
                      onClick={() => setShowKbDetailsModal(true)}
                      className="w-full px-6 py-4 flex items-center justify-between hover:bg-[#0a2d4d] transition-colors"
                    >
                      <h3 className="text-sm font-semibold text-white">View KB Details</h3>
                      <ExternalLink className="w-4 h-4 text-white" />
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Agent Details Modal */}
      <Dialog open={showAgentDetailsModal} onOpenChange={setShowAgentDetailsModal}>
        <DialogContent className="sm:max-w-4xl max-h-[80vh] bg-white z-50">
          <DialogHeader>
            <DialogTitle>Agent Details</DialogTitle>
            <DialogDescription>
              Complete agent configuration and metadata from mintleads-agents-store
            </DialogDescription>
          </DialogHeader>
          <div className="mt-4 overflow-y-auto max-h-[60vh]">
            <pre className="text-xs bg-gray-900 text-white p-4 rounded overflow-x-auto font-mono">
              {clientDetails?.agent_data ? JSON.stringify(clientDetails.agent_data, null, 2) : 'No data available'}
            </pre>
          </div>
          <DialogFooter>
            <Button
              variant="code"
              onClick={() => setShowAgentDetailsModal(false)}
              className="font-medium"
            >
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* KB Details Modal */}
      <Dialog open={showKbDetailsModal} onOpenChange={setShowKbDetailsModal}>
        <DialogContent className="sm:max-w-4xl max-h-[80vh] bg-white z-50">
          <DialogHeader>
            <DialogTitle>Knowledge Base Details</DialogTitle>
            <DialogDescription>
              Complete client and KB metadata from mintleads-clients-kb
            </DialogDescription>
          </DialogHeader>
          <div className="mt-4 overflow-y-auto max-h-[60vh]">
            <pre className="text-xs bg-gray-900 text-white p-4 rounded overflow-x-auto font-mono">
              {clientDetails?.kb_data ? JSON.stringify(clientDetails.kb_data, null, 2) : 'No data available'}
            </pre>
          </div>
          <DialogFooter>
            <Button
              variant="code"
              onClick={() => setShowKbDetailsModal(false)}
              className="font-medium"
            >
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* Delete Confirmation Modal */}
      <Dialog open={showDeleteModal} onOpenChange={setShowDeleteModal}>
        <DialogContent className="sm:max-w-md bg-white z-50">
          <DialogHeader>
            <DialogTitle>Delete Index</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete the index for {siteData.metadata.title}? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="flex gap-2">
            <Button
              variant="code"
              onClick={() => setShowDeleteModal(false)}
              className="font-medium"
            >
              Cancel
            </Button>
            <Button
              variant="orange"
              onClick={handleDelete}
              className="font-medium"
            >
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* API Modal */}
      <Dialog open={showApiModal} onOpenChange={setShowApiModal}>
        <DialogContent className="sm:max-w-3xl bg-white z-50 max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>API Access</DialogTitle>
            <DialogDescription>
              Use this index with any OpenAI-compatible API client.
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-3 mb-6">
            <div>
              <span className="text-sm text-gray-600">Model Name:</span>
              <code className="ml-2 text-sm text-orange-600">{modelName}</code>
            </div>
            <div>
              <span className="text-sm text-gray-600">Endpoint:</span>
              <code className="ml-2 text-sm text-gray-700">/api/v1/chat/completions</code>
            </div>
          </div>
          
          {/* Language tabs */}
          <div className="mb-6">
            <div className="flex flex-wrap gap-2 mb-6 p-1 bg-gray-100 rounded-lg">
              <button
                onClick={() => setActiveTab('curl')}
                className={`px-4 py-2 text-sm font-medium rounded-md transition-all ${
                  activeTab === 'curl'
                    ? 'bg-white text-orange-600 shadow-sm'
                    : 'text-gray-600 hover:text-gray-800'
                }`}
              >
                cURL
              </button>
              <button
                onClick={() => setActiveTab('openai-js')}
                className={`px-4 py-2 text-sm font-medium rounded-md transition-all ${
                  activeTab === 'openai-js'
                    ? 'bg-white text-orange-600 shadow-sm'
                    : 'text-gray-600 hover:text-gray-800'
                }`}
              >
                OpenAI JS
              </button>
              <button
                onClick={() => setActiveTab('openai-python')}
                className={`px-4 py-2 text-sm font-medium rounded-md transition-all ${
                  activeTab === 'openai-python'
                    ? 'bg-white text-orange-600 shadow-sm'
                    : 'text-gray-600 hover:text-gray-800'
                }`}
              >
                OpenAI Python
              </button>
              <button
                onClick={() => setActiveTab('javascript')}
                className={`px-4 py-2 text-sm font-medium rounded-md transition-all ${
                  activeTab === 'javascript'
                    ? 'bg-white text-orange-600 shadow-sm'
                    : 'text-gray-600 hover:text-gray-800'
                }`}
              >
                JavaScript
              </button>
              <button
                onClick={() => setActiveTab('python')}
                className={`px-4 py-2 text-sm font-medium rounded-md transition-all ${
                  activeTab === 'python'
                    ? 'bg-white text-orange-600 shadow-sm'
                    : 'text-gray-600 hover:text-gray-800'
                }`}
              >
                Python
              </button>
            </div>
            
            {/* Tab content */}
            <div className="bg-gray-900 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-medium text-gray-300">
                  {activeTab === 'curl' && 'cURL Command'}
                  {activeTab === 'javascript' && 'JavaScript (Fetch API)'}
                  {activeTab === 'python' && 'Python (Requests)'}
                  {activeTab === 'openai-js' && 'OpenAI SDK for JavaScript'}
                  {activeTab === 'openai-python' && 'OpenAI SDK for Python'}
                </span>
                <button
                  onClick={() => copyToClipboard(
                    activeTab === 'curl' ? curlCommand : 
                    activeTab === 'javascript' ? jsCode : 
                    activeTab === 'python' ? pythonCode :
                    activeTab === 'openai-js' ? openaiJsCode :
                    openaiPythonCode, 
                    activeTab
                  )}
                  className="text-sm text-orange-400 hover:text-orange-300 flex items-center gap-1 transition-colors"
                >
                  {copiedItem === activeTab ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                  {copiedItem === activeTab ? 'Copied!' : 'Copy'}
                </button>
              </div>
              <pre className="text-sm text-gray-100 overflow-x-auto">
                <code className="language-bash">
                  {activeTab === 'curl' && curlCommand}
                  {activeTab === 'javascript' && jsCode}
                  {activeTab === 'python' && pythonCode}
                  {activeTab === 'openai-js' && openaiJsCode}
                  {activeTab === 'openai-python' && openaiPythonCode}
                </code>
              </pre>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default function DashboardPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gradient-to-br from-orange-50 via-yellow-50 to-red-50 p-6">
        <div className="max-w-7xl mx-auto">
          <div className="flex justify-center items-center min-h-[60vh]">
            <div className="text-center">
              <div className="w-12 h-12 text-orange-600 mx-auto mb-4 animate-spin">
                <Database className="w-full h-full" />
              </div>
              <p className="text-gray-600">Loading dashboard...</p>
            </div>
          </div>
        </div>
      </div>
    }>
      <DashboardContent />
    </Suspense>
  )
}