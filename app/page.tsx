"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useStorage } from "@/hooks/useStorage";
import { buildApiHeaders, getBackendUrl } from "@/lib/backend";
import { clientConfig as config } from "@/mintagent.config";
import { 
  Globe, 
  ArrowRight, 
  Settings, 
  Loader2, 
  CheckCircle2, 
  FileText, 
  AlertCircle,
  Database,
  Zap,
  Search,
  Sparkles,
  Lock,
  ExternalLink
} from "lucide-react";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

export default function MintagentPage() {
  const router = useRouter();
  const searchParams = new URLSearchParams(typeof window !== 'undefined' ? window.location.search : '');
  const urlParam = searchParams.get('url');
  const { saveIndex } = useStorage();
  
  const [url, setUrl] = useState(urlParam || 'https://mintleads.io/');
  const [clientDriveFolder, setClientDriveFolder] = useState('');
  const [indexName, setIndexName] = useState<string>('');
  const [hasInteracted, setHasInteracted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [pageLimit, setPageLimit] = useState(config.crawling.defaultLimit);
  const [isCreationDisabled, setIsCreationDisabled] = useState<boolean | undefined>(undefined);
  const [crawlProgress, setCrawlProgress] = useState<{
    status: string;
    pagesFound: number;
    pagesScraped: number;
    currentPage?: string;
  } | null>(null);
  const [showApiKeyModal, setShowApiKeyModal] = useState(false);
  const [firecrawlApiKey, setFirecrawlApiKey] = useState<string>('');
  const [isValidatingApiKey, setIsValidatingApiKey] = useState(false);
  const [hasFirecrawlKey, setHasFirecrawlKey] = useState(false);
  const [mapLinks, setMapLinks] = useState<Array<{ url: string; title?: string; description?: string }>>([]);
  const [selectedLinks, setSelectedLinks] = useState<Record<string, boolean>>({});
  const [useMapFlow, setUseMapFlow] = useState(false);
  const [isScrapingSelected, setIsScrapingSelected] = useState(false);
  const allMappedSelected =
    mapLinks.length > 0 && mapLinks.every((link) => selectedLinks[link.url]);

  useEffect(() => {
    // Check environment and API keys
    fetch('/api/check-env')
      .then(res => res.json())
      .then(data => {
        setIsCreationDisabled(data.environmentStatus.DISABLE_CHATBOT_CREATION || false);
        
        // Check for Firecrawl API key
        const hasEnvFirecrawl = data.environmentStatus.FIRECRAWL_API_KEY;
        setHasFirecrawlKey(hasEnvFirecrawl);
        
        if (!hasEnvFirecrawl) {
          // Check localStorage for saved API key
          const savedKey = localStorage.getItem('firecrawl_api_key');
          if (savedKey) {
            setFirecrawlApiKey(savedKey);
            setHasFirecrawlKey(true);
          }
        }
      })
      .catch(() => {
        setIsCreationDisabled(false);
      });
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    console.log('[Homepage] handleSubmit called', { url, loading, hasFirecrawlKey });

    const slug = indexName.trim();
    if (!slug) {
      toast.error('Client slug is required');
      return;
    }

    const rawUrl = url?.trim() || '';
    const driveFolder = clientDriveFolder?.trim() || '';
    const hasUrl = !!rawUrl;

    if (!hasUrl && !driveFolder) {
      toast.error('Provide a website URL or a Client Drive Folder');
      return;
    }
    
    // Check if we have Firecrawl API key
    if (hasUrl && !hasFirecrawlKey && !localStorage.getItem('firecrawl_api_key')) {
      console.log('[Homepage] No Firecrawl API key, showing modal');
      setShowApiKeyModal(true);
      return;
    }

    let normalizedUrl: string | undefined = undefined;
    if (hasUrl) {
      normalizedUrl = rawUrl;
      if (!normalizedUrl.startsWith('http://') && !normalizedUrl.startsWith('https://')) {
        normalizedUrl = 'https://' + normalizedUrl;
      }
      
      // Validate URL
      try {
        new URL(normalizedUrl);
      } catch {
        toast.error('Please enter a valid URL');
        return;
      }
    }

    setLoading(true);
    setCrawlProgress({
      status: 'Starting crawl...',
      pagesFound: 0,
      pagesScraped: 0
    });
    
    interface CrawlResponse {
      success: boolean
      namespace: string
    index?: string
      crawlId?: string
      details?: {
        url?: string
        pagesCrawled?: number
        pagesScraped?: number
      }
      data: Array<{
        url?: string
        metadata?: {
          sourceURL?: string
          title?: string
          ogTitle?: string
          description?: string
          ogDescription?: string
          favicon?: string
          ogImage?: string
          'og:image'?: string
          'twitter:image'?: string
          indexName?: string
        }
      }>
    }
    
    let data: CrawlResponse | null = null;
    
    try {
      // Map/scrape fallback flow
      if (useMapFlow) {
        if (!hasUrl || !normalizedUrl) {
          toast.error('Website URL is required for Map + Scrape');
          setLoading(false);
          setCrawlProgress(null);
          return;
        }
        setCrawlProgress({
          status: 'Discovering all pages...',
          pagesFound: 0,
          pagesScraped: 0
        });
        
        const mapResp = await fetch(getBackendUrl('/api/mintagent/map'), {
          method: 'POST',
          headers: buildApiHeaders(),
          body: JSON.stringify({ url: normalizedUrl, limit: 5000, index: slug || undefined, clientSlug: slug })
        });
        const mapData = await mapResp.json();
        if (!mapResp.ok || !mapData?.success) {
          throw new Error(mapData?.error || 'Failed to map site');
        }
        const links = mapData.links || [];
        
        if (links.length === 0) {
          toast.error('No pages discovered');
        setLoading(false);
        setCrawlProgress(null);
        return;
      }

        // Auto-scrape all discovered URLs (up to the page limit)
        const urlsToScrape = links.slice(0, pageLimit).map((l: any) => l.url || l);
        
        toast.success(`Discovered ${links.length} URLs. Scraping ${urlsToScrape.length} pages...`);
        
        setCrawlProgress({
          status: `Scraping ${urlsToScrape.length} discovered pages...`,
          pagesFound: urlsToScrape.length,
          pagesScraped: 0
        });
        
        const scrapeResp = await fetch(getBackendUrl('/api/mintagent/scrape'), {
          method: 'POST',
          headers: buildApiHeaders(),
          body: JSON.stringify({ urls: urlsToScrape, index: slug || undefined, clientSlug: slug })
        });
        
        data = await scrapeResp.json();
        
        if (!scrapeResp.ok || !data?.success) {
          const errorMsg = (data as any)?.error || 'Failed to scrape URLs'
          throw new Error(errorMsg)
        }
        
        setCrawlProgress({
          status: 'Scraping complete!',
          pagesFound: data.details?.pagesScraped || urlsToScrape.length,
          pagesScraped: data.details?.pagesScraped || urlsToScrape.length
        });
        
        // Handle map+scrape success - extract metadata and redirect
        let homepageMetadata: {
          title?: string
          ogTitle?: string
          description?: string
          ogDescription?: string
          favicon?: string
          ogImage?: string
          'og:image'?: string
          'twitter:image'?: string
        } = {};
        if (data.data && data.data.length > 0) {
          const homepage = data.data.find((page: any) => {
            const pageUrl = page.metadata?.sourceURL || page.url || '';
            return pageUrl === normalizedUrl || pageUrl === normalizedUrl + '/' || pageUrl === normalizedUrl.replace(/\/$/, '');
          }) || data.data[0];
          
          homepageMetadata = homepage.metadata || {};
        }
        
        const siteInfo = {
          url: normalizedUrl,
          namespace: data.namespace,
          index: data.index,
          pagesCrawled: data.details?.pagesScraped || data.details?.pagesCrawled || urlsToScrape.length,
          crawlComplete: true,
          crawlDate: new Date().toISOString(),
          metadata: {
            title: homepageMetadata.ogTitle || homepageMetadata.title || new URL(normalizedUrl).hostname,
            description: homepageMetadata.ogDescription || homepageMetadata.description || 'Your custom website',
            favicon: homepageMetadata.favicon,
            ogImage: homepageMetadata.ogImage || homepageMetadata['og:image'] || homepageMetadata['twitter:image'],
            indexName: data.index,
          }
        };
        
        sessionStorage.setItem('mintagent_current_data', JSON.stringify(siteInfo));
        
        await saveIndex({
          url: normalizedUrl,
          namespace: data.namespace,
          pagesCrawled: data.details?.pagesScraped || data.details?.pagesCrawled || urlsToScrape.length,
          createdAt: new Date().toISOString(),
          metadata: {
            title: homepageMetadata.ogTitle || homepageMetadata.title || new URL(normalizedUrl).hostname,
            description: homepageMetadata.ogDescription || homepageMetadata.description || 'Your custom website',
            favicon: homepageMetadata.favicon,
            ogImage: homepageMetadata.ogImage || homepageMetadata['og:image'] || homepageMetadata['twitter:image'],
            indexName: data.index,
          } as any
        });
        
        setTimeout(() => {
          router.push(`/dashboard?namespace=${siteInfo.namespace}`);
        }, 1000);
        return; // Exit early - don't run regular crawl
      } else {
        // Regular crawl flow
      // Simulate progressive updates (crawl flow)
      let currentProgress = 0;
        let progressInterval: NodeJS.Timeout | null = null;
        
        try {
          progressInterval = setInterval(() => {
        currentProgress += Math.random() * 3;
        if (currentProgress > pageLimit * 0.8) {
              if (progressInterval) {
          clearInterval(progressInterval);
                progressInterval = null;
              }
        }
        
        setCrawlProgress(prev => {
          if (!prev) return null;
          const scraped = Math.min(Math.floor(currentProgress), pageLimit);
          return {
            ...prev,
            status: scraped < pageLimit * 0.3 ? 'Discovering pages...' : 
                   scraped < pageLimit * 0.7 ? 'Scraping content...' : 
                   'Finalizing...',
            pagesFound: pageLimit,
            pagesScraped: scraped,
            currentPage: scraped > 0 ? `Processing page ${scraped} of ${pageLimit}` : undefined
          };
        });
      }, 300);
      
      const response = await fetch(getBackendUrl('/api/mintagent/create'), {
        method: 'POST',
        headers: buildApiHeaders(),
        body: JSON.stringify({ 
          url: hasUrl ? normalizedUrl : undefined, 
          limit: pageLimit, 
          index: slug || undefined,
          clientSlug: slug,
          clientDriveFolder: driveFolder || undefined 
        })
      });

      data = await response.json();
        } finally {
          if (progressInterval) {
            clearInterval(progressInterval);
          }
        }
      }
      
      if (data && data.success) {
        setCrawlProgress({
          status: hasUrl ? 'Crawl complete!' : 'Ingestion complete!',
          pagesFound: data.details?.pagesCrawled || 0,
          pagesScraped: data.details?.pagesCrawled || 0
        });
        
        let homepageMetadata: {
          title?: string
          ogTitle?: string
          description?: string
          ogDescription?: string
          favicon?: string
          ogImage?: string
          'og:image'?: string
          'twitter:image'?: string
        } = {};
        if (hasUrl && normalizedUrl && data.data && data.data.length > 0) {
          const homepage = data.data.find((page) => {
            const pageUrl = page.metadata?.sourceURL || page.url || '';
            return pageUrl === normalizedUrl || pageUrl === normalizedUrl + '/' || pageUrl === normalizedUrl.replace(/\/$/, '');
          }) || data.data[0];
          
          homepageMetadata = homepage.metadata || {};
        } else if (data.homepage) {
          homepageMetadata = data.homepage;
        }
        
        const effectiveUrl = normalizedUrl || driveFolder || '';
        const fallbackHost = normalizedUrl ? new URL(normalizedUrl).hostname : slug || 'drive-only';

        const siteInfo = {
          url: effectiveUrl,
          namespace: data.namespace,
          index: data.index,
          crawlId: data.crawlId,
          pagesCrawled: data.details?.pagesCrawled || 0,
          crawlComplete: true,
          crawlDate: new Date().toISOString(),
          metadata: {
            title: homepageMetadata.ogTitle || homepageMetadata.title || fallbackHost,
            description: homepageMetadata.ogDescription || homepageMetadata.description || 'Your custom website',
            favicon: homepageMetadata.favicon,
            ogImage: homepageMetadata.ogImage || homepageMetadata['og:image'] || homepageMetadata['twitter:image'],
            indexName: data.index,
          }
        };
        
        sessionStorage.setItem('mintagent_current_data', JSON.stringify(siteInfo));
        
        await saveIndex({
          url: effectiveUrl,
          namespace: data.namespace,
          pagesCrawled: data.details?.pagesCrawled || 0,
          createdAt: new Date().toISOString(),
          metadata: {
            title: homepageMetadata.ogTitle || homepageMetadata.title || fallbackHost,
            description: homepageMetadata.ogDescription || homepageMetadata.description || 'Your custom website',
            favicon: homepageMetadata.favicon,
            ogImage: homepageMetadata.ogImage || homepageMetadata['og:image'] || homepageMetadata['twitter:image'],
            indexName: data.index,
          } as any
        });
        
        setTimeout(() => {
          router.push(`/dashboard?namespace=${siteInfo.namespace}`);
        }, 1000);
      } else if (data && 'error' in data) {
        setCrawlProgress({
          status: 'Error: ' + (data as { error: string }).error,
          pagesFound: 0,
          pagesScraped: 0
        });
        toast.error((data as { error: string }).error);
      }
    } catch (error) {
      console.error('[Homepage] handleSubmit error:', error);
      toast.error('Failed to start crawling. Please try again.');
      setLoading(false);
      setCrawlProgress(null);
    } finally {
      if (!data?.success) {
        setLoading(false);
        setCrawlProgress(null);
      }
    }
  };

  const handleScrapeSelected = async () => {
    const chosen = Object.keys(selectedLinks).filter((url) => selectedLinks[url]);
    if (chosen.length === 0) {
      toast.error('Select at least one URL to scrape');
      return;
    }
    setIsScrapingSelected(true);
    try {
      const resp = await fetch(getBackendUrl('/api/mintagent/scrape'), {
        method: 'POST',
        headers: buildApiHeaders(),
        body: JSON.stringify({ urls: chosen, index: indexName || undefined }),
      });
      let result: any = null;
      try {
        result = await resp.json();
      } catch {
        // ignore JSON parse errors, handle below
      }
      if (!resp.ok || !result?.success) {
        const message =
          result?.error ||
          `Failed to scrape selected URLs (status ${resp.status})`;
        throw new Error(message);
      }

      const homepageMetadata = result.homepage || {};
      const siteInfo = {
        url: url,
        namespace: result.namespace,
        index: result.index,
        pagesCrawled: result.details?.pagesScraped || 0,
        crawlComplete: true,
        crawlDate: new Date().toISOString(),
        metadata: {
          title: homepageMetadata.title || new URL(url).hostname,
          description: homepageMetadata.description || 'Your custom website',
          favicon: homepageMetadata.favicon,
          ogImage: homepageMetadata.ogImage,
          indexName: result.index,
        },
      };

      sessionStorage.setItem('mintagent_current_data', JSON.stringify(siteInfo));
      await saveIndex({
        url: url,
        namespace: result.namespace,
        pagesCrawled: result.details?.pagesScraped || 0,
        createdAt: new Date().toISOString(),
        metadata: siteInfo.metadata as any,
      });

      toast.success(`Scraped ${result.details?.pagesScraped || chosen.length} pages`);
      router.push(`/dashboard?namespace=${result.namespace}`);
    } catch (err) {
      console.error(err);
      toast.error(err instanceof Error ? err.message : 'Failed to scrape selected URLs');
    } finally {
      setIsScrapingSelected(false);
    }
  };

  const handleApiKeySubmit = async () => {
    if (!firecrawlApiKey.trim()) {
      toast.error('Please enter a valid Firecrawl API key');
      return;
    }

    setIsValidatingApiKey(true);

    try {
      // Test the Firecrawl API key
      const response = await fetch('/api/scrape', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Firecrawl-API-Key': firecrawlApiKey,
        },
        body: JSON.stringify({ url: 'https://example.com' }),
      });

      if (!response.ok) {
        throw new Error('Invalid Firecrawl API key');
      }
      
      // Save the API key to localStorage
      localStorage.setItem('firecrawl_api_key', firecrawlApiKey);
      setHasFirecrawlKey(true);

      toast.success('API key saved successfully!');
      setShowApiKeyModal(false);

      // Trigger form submission after API key is saved
      if (url) {
        const form = document.querySelector('form');
        if (form) {
          form.requestSubmit();
        }
      }
    } catch {
      toast.error('Invalid API key. Please check and try again.');
    } finally {
      setIsValidatingApiKey(false);
    }
  };

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-4 max-w-7xl mx-auto font-inter">
      <div className="flex justify-between items-center mb-8">
        <div className="text-xl font-bold text-mint-primary">
          MintAgents
        </div>
        <div className="flex items-center gap-2">
          <Button
            asChild
            variant="orange"
            className="font-medium"
          >
            <Link href="/indexes">
              View All
            </Link>
          </Button>
          <Button
            asChild
            variant="orange"
            className="font-medium flex items-center gap-2"
          >
            <a
              href="https://cloud.digitalocean.com/gen-ai/workspaces/11f0df43-69be-eb71-b074-4e013e2ddde4/agents"
              target="_blank"
              rel="noopener noreferrer"
            >
              Link to DB
            </a>
          </Button>
        </div>
      </div>

      {isCreationDisabled === undefined ? (
        // Show loading state while checking environment
        <div className="max-w-2xl mx-auto">
          <div className="text-center pt-8 pb-6">
            <h1 className="text-[2.5rem] lg:text-[3.8rem] text-center text-[#0E3D68] dark:text-zinc-100 font-semibold tracking-tight leading-[1.1] opacity-0 animate-fade-up [animation-duration:500ms] [animation-delay:200ms] [animation-fill-mode:forwards]">
              MintAgents<br />
              <span className="text-[2.5rem] lg:text-[3.8rem] block mt-2 opacity-0 animate-fade-up [animation-duration:500ms] [animation-delay:400ms] [animation-fill-mode:forwards] text-transparent bg-clip-text bg-gradient-to-tr from-[#00B388] to-[#0E3D68]">
                Loading...
              </span>
            </h1>
          </div>
        </div>
      ) : isCreationDisabled === true ? (
        <div className="max-w-2xl mx-auto">
          <div className="text-center pt-8 pb-6">
            <h1 className="text-[2.5rem] lg:text-[3.8rem] text-center text-[#0E3D68] dark:text-zinc-100 font-semibold tracking-tight leading-[1.1] opacity-0 animate-fade-up [animation-duration:500ms] [animation-delay:200ms] [animation-fill-mode:forwards]">
              MintAgents<br />
              <span className="text-[2.5rem] lg:text-[3.8rem] block mt-2 opacity-0 animate-fade-up [animation-duration:500ms] [animation-delay:400ms] [animation-fill-mode:forwards] text-transparent bg-clip-text bg-gradient-to-tr from-gray-400 to-gray-600">
                Read-Only Mode
              </span>
            </h1>
          </div>
          
          <div className="bg-orange-50 border border-orange-200 rounded-xl p-8 text-center">
            <Lock className="h-12 w-12 text-orange-600 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-[#36322F] mb-2">
              Chatbot Creation Disabled
            </h2>
            <p className="text-gray-600 mb-6">
              Chatbot creation has been disabled by the administrator. You can only view and interact with existing chatbots.
            </p>
            <div className="flex gap-4 justify-center">
              <Button
                asChild
                variant="orange"
                className="font-medium"
              >
                <Link href="/indexes">
                  View Existing Chatbots
                </Link>
              </Button>
              <Button
                asChild
                variant="orange"
                className="font-medium"
              >
                <Link href="/">
                  Back to Home
                </Link>
              </Button>
            </div>
          </div>
        </div>
      ) : (
        <>
          <div className="text-center pt-8 pb-6">
            <h1 className="text-[2.5rem] lg:text-[3.8rem] text-center text-[#0E3D68] dark:text-zinc-100 font-semibold tracking-tight leading-[1.1] opacity-0 animate-fade-up [animation-duration:500ms] [animation-delay:200ms] [animation-fill-mode:forwards]">
              MintAgents<br />
              <span className="text-[2.5rem] lg:text-[3.8rem] block mt-2 opacity-0 animate-fade-up [animation-duration:500ms] [animation-delay:400ms] [animation-fill-mode:forwards] text-[#00B388]">
                Custom AI Chatbots
              </span>
            </h1>
          </div>

          <div className="max-w-2xl mx-auto">
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="relative">
                <Input
                  type="text"
                  value={url}
                  onChange={(e) => {
                    setUrl(e.target.value);
                    setHasInteracted(true);
                  }}
                  onFocus={() => {
                    if (!hasInteracted && url === 'https://mintleads.io/') {
                      setUrl('');
                      setHasInteracted(true);
                    }
                  }}
                  placeholder="https://example.com"
                  className="w-full h-14 px-6 text-lg border-mint-primary/20 focus:border-mint-accent focus:ring-mint-accent/20"
                  required
                  disabled={loading}
                />
                <Button
                  type="submit"
                  disabled={loading}
                  variant="orange"
                  className="absolute right-2 top-2 h-10"
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin mr-2" />
                      Crawling...
                    </>
                  ) : (
                    <>
                      Start
                      <ArrowRight className="w-4 h-4 ml-2" />
                    </>
                  )}
                </Button>
              </div>
              <div className="flex flex-col sm:flex-row sm:items-center gap-3">
                <div className="flex-1">
                  <label className="block text-sm font-medium text-[#0E3D68] dark:text-gray-300 mb-1">
                    Index Name (client-slug)
                  </label>
                  <Input
                    type="text"
                    value={indexName}
                    onChange={(e) => setIndexName(e.target.value)}
                    placeholder="e.g. mintleads"
                    disabled={loading}
                    required
                    className="border-[#0E3D68]/20 focus:border-[#00B388] focus:ring-[#00B388]/20"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Optional.
                  </p>
                </div>
              </div>
              <div className="flex flex-col sm:flex-row sm:items-center gap-3">
                <div className="flex-1">
                  <label className="block text-sm font-medium text-[#0E3D68] dark:text-gray-300 mb-1">
                    Client Drive Folder
                  </label>
                  <Input
                    type="text"
                    value={clientDriveFolder}
                    onChange={(e) => setClientDriveFolder(e.target.value)}
                    placeholder="Google Drive folder link or ID (optional)"
                    disabled={loading}
                    className="border-[#0E3D68]/20 focus:border-[#00B388] focus:ring-[#00B388]/20"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Optional. Provide a shared folder URL or ID to ingest Drive files.
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3 text-sm text-muted-foreground">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    className="h-4 w-4 rounded border-gray-300 text-[#00B388] focus:ring-[#00B388]"
                    checked={useMapFlow}
                    onChange={() => setUseMapFlow(!useMapFlow)}
                    disabled={loading}
                  />
                  <span>Use Map + Scrape for comprehensive coverage (slower but finds all pages)</span>
                </label>
              </div>
              <p className="text-xs text-gray-500 mt-1 ml-6">
                💡 Recommended: Enable this to discover and scrape ALL pages. Regular crawl may miss some pages.
              </p>
            </form>

            {/* Map results and selection */}
            {mapLinks.length > 0 && (
              <div className="mt-6 p-4 border rounded-xl bg-[#FBFAF9] space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-[#36322F]">Mapped URLs</h3>
                    <p className="text-sm text-gray-600">Select which pages to scrape.</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <label className="flex items-center gap-2 text-sm text-gray-700">
                      <input
                        type="checkbox"
                        className="h-4 w-4 rounded border-gray-300 text-orange-600 focus:ring-orange-500"
                        checked={allMappedSelected}
                        onChange={(e) => {
                          if (e.target.checked) {
                            // select all
                            const next: Record<string, boolean> = {};
                            mapLinks.forEach((link) => {
                              next[link.url] = true;
                            });
                            setSelectedLinks(next);
                          } else {
                            setSelectedLinks({});
                          }
                        }}
                      />
                      <span>Select all</span>
                    </label>
                    <Button
                      type="button"
                      size="sm"
                      variant="orange"
                      onClick={handleScrapeSelected}
                      disabled={isScrapingSelected}
                    >
                      {isScrapingSelected ? 'Scraping...' : 'Scrape Selected'}
                    </Button>
                  </div>
                </div>
                <div className="max-h-60 overflow-auto space-y-2">
                  {mapLinks.map((link, idx) => (
                    <label key={link.url + idx} className="flex items-start gap-2 text-sm text-gray-800">
                      <input
                        type="checkbox"
                        className="mt-1 h-4 w-4 rounded border-gray-300 text-orange-600 focus:ring-orange-500"
                        checked={!!selectedLinks[link.url]}
                        onChange={(e) =>
                          setSelectedLinks((prev) => ({
                            ...prev,
                            [link.url]: e.target.checked,
                          }))
                        }
                      />
                      <div className="flex-1">
                        <p className="font-medium text-[#36322F]">{link.title || link.url}</p>
                        <p className="text-xs text-gray-600 break-all">{link.url}</p>
                        {link.description && (
                          <p className="text-xs text-gray-500">{link.description}</p>
                        )}
                      </div>
                    </label>
                  ))}
                </div>
              </div>
            )}

            {/* Loading Progress */}
            {loading && crawlProgress && (
              <div className="mt-8 p-6 bg-[#FBFAF9] rounded-xl border border-gray-200 animate-in fade-in slide-in-from-bottom-4 duration-500">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-[#36322F] flex items-center gap-2">
                    {crawlProgress.status === 'Crawl complete!' ? (
                      <CheckCircle2 className="w-5 h-5 text-[#00B388] animate-in zoom-in duration-300" />
                    ) : crawlProgress.status.includes('Error') ? (
                      <AlertCircle className="w-5 h-5 text-red-600 animate-in zoom-in duration-300" />
                    ) : (
                      <Loader2 className="w-5 h-5 text-[#00B388] animate-spin" />
                    )}
                    <span className="animate-in fade-in duration-300">{crawlProgress.status}</span>
                  </h3>
                </div>
                
                <div className="space-y-3">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">Pages discovered</span>
                    <span className="text-[#36322F] font-medium transition-all duration-300">
                      {crawlProgress.pagesFound}
                    </span>
                  </div>
                  
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">Pages scraped</span>
                    <span className="text-[#36322F] font-medium transition-all duration-300">
                      {crawlProgress.pagesScraped}
                    </span>
                  </div>
                  
                  {crawlProgress.pagesFound > 0 && (
                    <div className="mt-4">
                      <div className="flex justify-between text-xs text-gray-600 mb-1">
                        <span>Progress</span>
                        <span>{Math.round((crawlProgress.pagesScraped / crawlProgress.pagesFound) * 100)}% ({crawlProgress.pagesScraped} / {crawlProgress.pagesFound} pages)</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div 
                          className="bg-[#00B388] h-2 rounded-full transition-all duration-500"
                          style={{ width: `${(crawlProgress.pagesScraped / crawlProgress.pagesFound) * 100}%` }}
                        />
                      </div>
                    </div>
                  )}
                  
                  {crawlProgress.currentPage && (
                    <div className="mt-4 p-3 bg-gray-50 rounded-lg">
                      <p className="text-xs text-gray-600 mb-1">Currently scraping:</p>
                      <p className="text-sm text-gray-800 truncate flex items-center gap-2">
                        <FileText className="w-4 h-4 text-gray-500" />
                        {crawlProgress.currentPage}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Settings Button */}
            <div className="mt-6 flex justify-center">
              <Button
                type="button"
                onClick={() => setShowSettings(!showSettings)}
                variant="orange"
                size="sm"
                className="font-medium"
              >
                <Settings className="w-4 h-4 mr-2" />
                Advanced Settings
              </Button>
            </div>

            {/* Settings Panel */}
            {showSettings && (
              <div className="mt-4 p-6 bg-[#FBFAF9] rounded-xl border border-gray-200">
                <h3 className="text-lg font-semibold text-[#36322F] mb-4">Crawl Settings</h3>
                
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Maximum pages to crawl
                    </label>
                    <div className="flex items-center gap-4">
                      <input
                        type="range"
                        min={config.crawling.minLimit}
                        max={config.crawling.maxLimit}
                        step="5"
                        value={pageLimit}
                        onChange={(e) => setPageLimit(parseInt(e.target.value))}
                        className="flex-1 accent-[#00B388]"
                        disabled={loading}
                      />
                      <span className="text-[#36322F] font-medium w-12 text-right">{pageLimit === 5000 ? 'All' : pageLimit}</span>
                    </div>
                    <p className="mt-2 text-xs text-gray-600">
                      More pages = better coverage but longer crawl time
                    </p>
                    <p className="mt-1 text-xs text-gray-500">
                      * To set limit higher - feel free to pull the GitHub repo and deploy your own version (with a better copy)
                    </p>
                  </div>
                  
                  <div className="grid grid-cols-5 gap-2 mt-4">
                    {config.crawling.limitOptions.map(limit => (
                      <Button
                        key={limit}
                        type="button"
                        onClick={() => setPageLimit(limit)}
                        disabled={loading}
                        variant={pageLimit === limit ? "orange" : "outline"}
                        size="sm"
                      >
                        {limit === 5000 ? 'All' : limit}
                      </Button>
                    ))}
                  </div>
                </div>
              </div>
            )}

            <div className="mt-12">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-[#FBFAF9] rounded-xl border border-gray-200 px-6 py-4 flex items-center gap-3 hover:shadow-sm transition-shadow">
                  <div className="w-8 h-8 bg-[#00B388]/10 rounded-lg flex items-center justify-center flex-shrink-0">
                    <Globe className="w-4 h-4 text-[#00B388]" />
                  </div>
                  <div className="flex items-center">
                    <h3 className="text-base font-semibold text-[#0E3D68]">Smart Crawling</h3>
                  </div>
                </div>
                
                <div className="bg-[#FBFAF9] rounded-xl border border-gray-200 px-6 py-4 flex items-center gap-3 hover:shadow-sm transition-shadow">
                  <div className="w-8 h-8 bg-[#00B388]/10 rounded-lg flex items-center justify-center flex-shrink-0">
                    <FileText className="w-4 h-4 text-[#00B388]" />
                  </div>
                  <div className="flex items-center">
                    <h3 className="text-base font-semibold text-[#0E3D68]">Content Extraction</h3>
                  </div>
                </div>
                
                <div className="bg-[#FBFAF9] rounded-xl border border-gray-200 px-6 py-4 flex items-center gap-3 hover:shadow-sm transition-shadow">
                  <div className="w-8 h-8 bg-[#00B388]/10 rounded-lg flex items-center justify-center flex-shrink-0">
                    <Database className="w-4 h-4 text-[#00B388]" />
                  </div>
                  <div className="flex items-center">
                    <h3 className="text-base font-semibold text-[#0E3D68]">Intelligent Chunking</h3>
                  </div>
                </div>
                
                <div className="bg-[#FBFAF9] rounded-xl border border-gray-200 px-6 py-4 flex items-center gap-3 hover:shadow-sm transition-shadow">
                  <div className="w-8 h-8 bg-[#00B388]/10 rounded-lg flex items-center justify-center flex-shrink-0">
                    <Search className="w-4 h-4 text-[#00B388]" />
                  </div>
                  <div className="flex items-center">
                    <h3 className="text-base font-semibold text-[#0E3D68]">Semantic Search</h3>
                  </div>
                </div>
                
                <div className="bg-[#FBFAF9] rounded-xl border border-gray-200 px-6 py-4 flex items-center gap-3 hover:shadow-sm transition-shadow">
                  <div className="w-8 h-8 bg-[#00B388]/10 rounded-lg flex items-center justify-center flex-shrink-0">
                    <Zap className="w-4 h-4 text-[#00B388]" />
                  </div>
                  <div className="flex items-center">
                    <h3 className="text-base font-semibold text-[#0E3D68]">RAG Pipeline</h3>
                  </div>
                </div>
                
                <div className="bg-[#FBFAF9] rounded-xl border border-gray-200 px-6 py-4 flex items-center gap-3 hover:shadow-sm transition-shadow">
                  <div className="w-8 h-8 bg-[#00B388]/10 rounded-lg flex items-center justify-center flex-shrink-0">
                    <Sparkles className="w-4 h-4 text-[#00B388]" />
                  </div>
                  <div className="flex items-center">
                    <h3 className="text-base font-semibold text-[#0E3D68]">Instant API</h3>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </>
      )}

      {/* API Key Modal */}
      <Dialog open={showApiKeyModal} onOpenChange={setShowApiKeyModal}>
        <DialogContent className="sm:max-w-md bg-white dark:bg-zinc-900">
          <DialogHeader>
            <DialogTitle>Firecrawl API Key Required</DialogTitle>
            <DialogDescription>
              This tool requires a Firecrawl API key to crawl and index websites.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-4 py-4">
            <Button
              onClick={() => window.open('https://www.firecrawl.dev', '_blank')}
              variant="orange"
              size="sm"
              className="flex items-center justify-center gap-2 cursor-pointer"
            >
              <ExternalLink className="h-4 w-4" />
              Get Firecrawl API Key
            </Button>
            <div className="flex flex-col gap-2">
              <label htmlFor="firecrawl-key" className="text-sm font-medium">
                Firecrawl API Key
              </label>
              <Input
                id="firecrawl-key"
                type="password"
                placeholder="fc-..."
                value={firecrawlApiKey}
                onChange={(e) => setFirecrawlApiKey(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !isValidatingApiKey) {
                    handleApiKeySubmit();
                  }
                }}
                disabled={isValidatingApiKey}
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="orange"
              onClick={() => setShowApiKeyModal(false)}
              disabled={isValidatingApiKey}
              className="font-medium"
            >
              Cancel
            </Button>
            <Button
              onClick={handleApiKeySubmit}
              disabled={isValidatingApiKey || !firecrawlApiKey.trim()}
              variant="orange"
              className="font-medium"
            >
              {isValidatingApiKey ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Validating...
                </>
              ) : (
                'Submit'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
