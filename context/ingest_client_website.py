#!/usr/bin/env python3
"""
Client Website Content Scraper with Bright Data + LLM Content Extraction

This script crawls a client's website using their sitemap and saves each page
as a markdown file in a "website" folder with rich metadata. It uses Bright Data
for professional web scraping and GPT-4o mini LLM for intelligent content cleaning
that removes navigation, headers, footers, and boilerplate while preserving
the core informational content.

Features:
    - Professional web scraping with Bright Data (bot detection bypass)
    - GPT-4o mini LLM for intelligent content cleaning and structuring
    - Automatic filtering of navigation, headers, footers, social media, contact info
    - Content restructuring for optimal RAG retrieval
    - LLM-based URL categorization for better content organization
    - Parallel processing for faster scraping

Usage:
    # Full website crawl (default)
    python ingest_client_website.py --url https://example.com --client-name "Client Corp"

    # Single URL scrape
    python ingest_client_website.py --url https://example.com/page --single-url --client-name "Client Corp"

Required:
    --url: The website URL (base URL for sitemap discovery, or specific URL when using --single-url)
    -- BRIGHTDATA_API_TOKEN environment variable
    -- OPENAI_API_KEY environment variable (for LLM content cleaning)

Optional:
    --workers: Number of parallel workers for faster processing (default: 4)
    --output-dir: Output directory for website folder and logs (default: ingestion/client_ingestion_outputs)
    --no-llm-categories: Disable LLM categorization (LLM is enabled by default)
    --single-url: Scrape only the specified URL instead of crawling the entire sitemap
    --client-name: Client name to add to metadata
    --project-name: Project name to add to metadata
"""

import os
import sys
import argparse
import logging
import re
import time
import json
import psutil
import requests
import asyncio
from pathlib import Path
from urllib.parse import urlparse, urljoin
from dotenv import load_dotenv
from xml.etree import ElementTree
from typing import List, Set, Optional, Dict, Any
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from openai import AsyncOpenAI
from openai import OpenAI

# Content cleaning and extraction utilities are built-in

load_dotenv()

# Bright Data Configuration
BRIGHTDATA_API_TOKEN = os.getenv("BRIGHTDATA_API_TOKEN")

# Scraper utilities are built-in

print(f"BrightData API Token available: {bool(BRIGHTDATA_API_TOKEN)}")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_urls_from_sitemap(sitemap_url: str, processed_sitemaps: Optional[Set[str]] = None) -> List[str]:
    """
    Recursively fetches URLs from sitemap, handling both sitemap indexes and regular sitemaps.
    """
    if processed_sitemaps is None:
        processed_sitemaps = set()

    if sitemap_url in processed_sitemaps:
        return []

    processed_sitemaps.add(sitemap_url)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }

    try:
        response = requests.get(sitemap_url, headers=headers, timeout=30)
        response.raise_for_status()

        # Parse the XML
        root = ElementTree.fromstring(response.content)

        # Try different possible namespaces
        namespaces = [
            {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'},
            {},  # No namespace
        ]

        urls = []
        for ns in namespaces:
            # Try to find sitemap locations
            locations = root.findall('.//ns:loc', ns) if ns else root.findall('.//loc')

            for loc in locations:
                if loc.text is None:
                    continue
                url = loc.text.strip()
                if any(url.endswith(ext) for ext in ['.xml', 'sitemap.xml', 'sitemap_index.xml']):
                    # This is a sitemap index
                    logger.info(f"📋 Found nested sitemap: {url}")
                    child_urls = get_urls_from_sitemap(url, processed_sitemaps)
                    urls.extend(child_urls)
                else:
                    urls.append(url)

            if urls:  # If we found URLs with this namespace, stop trying others
                break

        return list(set(urls))  # Remove duplicates

    except Exception as e:
        logger.warning(f"Error processing sitemap {sitemap_url}: {str(e)}")
        return []

def discover_sitemaps(base_url: str) -> List[str]:
    """Discover sitemap URLs from common locations"""
    sitemap_candidates = [
        urljoin(base_url, '/sitemap.xml'),
        urljoin(base_url, '/sitemap_index.xml'),
        urljoin(base_url, '/wp-sitemap.xml'),
        urljoin(base_url, '/sitemap.xml.gz'),
    ]
    
    # Also check robots.txt
    try:
        robots_url = urljoin(base_url, '/robots.txt')
        response = requests.get(robots_url, timeout=15)
        if response.status_code == 200:
            for line in response.text.split('\n'):
                if line.strip().lower().startswith('sitemap:'):
                    sitemap_url = line.split(':', 1)[1].strip()
                    sitemap_candidates.append(sitemap_url)
    except:
        pass
    
    return sitemap_candidates

def extract_clean_content_from_markdown(markdown_content: str) -> tuple[str, str]:
    """
    Use LLM-based content cleaning to process Bright Data markdown content.
    Uses GPT-4o mini to remove navigation, headers, footers, and boilerplate.
    Returns (cleaned_markdown_content, title)
    """
    try:
        # Prefer true LLM cleaning when OPENAI_API_KEY is available
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            cleaned_md, title = llm_clean_markdown_content(markdown_content)
            if cleaned_md:
                logger.info("✅ LLM content cleaning applied")
                return cleaned_md, title
            logger.warning("⚠️ LLM cleaning returned empty content, using fallback")
        else:
            logger.info("OPENAI_API_KEY not found; using fallback cleaner")
    except Exception as e:
        logger.error(f"❌ Error in LLM content cleaning: {e}")

    # Fallback cleaner
    logger.info("Using built-in content cleaning fallback")
    return clean_markdown_content_fallback(markdown_content)

def clean_markdown_content_fallback(markdown_content: str) -> tuple[str, str]:
    """
    Fallback content cleaning for markdown when the main extractor fails
    """
    lines = markdown_content.split('\n')
    
    # Extract title from first # heading
    title = ""
    for line in lines[:20]:  # Check first 20 lines for title
        line_stripped = line.strip()
        if line_stripped.startswith('# ') and len(line_stripped) > 3:
            title = line_stripped[2:].strip()
            break
    
    # Simple navigation filtering
    cleaned_lines = []
    skip_next_empty = False
    
    for line in lines:
        line = line.strip()
        
        # Skip obvious navigation
        if (line.startswith('[') and '](' in line and len(line) < 50) or \
           'website-files.com' in line or \
           'Asset%20' in line:
            skip_next_empty = True
            continue
            
        # Skip empty lines after removed navigation
        if not line and skip_next_empty:
            skip_next_empty = False
            continue
            
        skip_next_empty = False
        cleaned_lines.append(line)
    
    # Join and clean up excessive whitespace
    cleaned_content = '\n'.join(cleaned_lines)
    cleaned_content = re.sub(r'\n{3,}', '\n\n', cleaned_content).strip()
    
    return cleaned_content, title

def llm_clean_markdown_content(markdown_content: str) -> tuple[str, str]:
    """
    Clean raw markdown using GPT-4o mini to remove navigation, headers, footers, and boilerplate
    while preserving core informational content and structure. Returns (cleaned_markdown, title).
    """
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")

    # Truncate overly large inputs to stay safely within context limits
    content = markdown_content
    max_chars = int(os.getenv('CONTENT_CLEAN_MAX_CHARS', '120000'))
    if len(content) > max_chars:
        logger.info(f"Truncating content from {len(content)} to {max_chars} chars for LLM cleaning")
        content = content[:max_chars]

    client = OpenAI(api_key=api_key)

    system_instructions = (
        "You are an expert content extraction assistant. Given a single web page in Markdown, "
        "return only the substantive article/page content. Remove navigation menus, headers, footers, "
        "sidebars, cookie notices, forms, repeated link lists, social links, and boilerplate. Preserve "
        "semantic structure (headings, paragraphs, lists, code blocks). Do not invent content. "
        "If multiple sections exist (e.g., hero + body), keep the meaningful text and headings only. "
        "Do not include site-wide menus or footers."
    )

    user_prompt = (
        "Clean the following Markdown. Return ONLY a valid JSON object with keys 'title' and 'content_md'. "
        "- 'title' should be a concise page title inferred from the H1 or the main content. "
        "- 'content_md' should be the cleaned Markdown content only, no extra commentary or JSON wrapper. "
        "Do not include any text outside the JSON object. Example format:\n"
        '{"title": "Page Title", "content_md": "# Clean Markdown Content Here"}\n\n'
        "```markdown\n" + content + "\n```"
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_instructions},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=4096,
        )
        text = response.choices[0].message.content or ""

        # Attempt JSON parse
        title = ""
        cleaned = ""
        try:
            data = json.loads(text)
            title = (data.get("title") or "").strip()
            cleaned = (data.get("content_md") or "").strip()
        except Exception as e:
            # If not JSON, try to heuristically split out a first-level heading as title
            logger.warning(f"⚠️  LLM returned non-JSON response, falling back to simple extraction. Error: {e}")
            logger.debug(f"LLM response was: {text[:200]}...")
            lines = [ln.strip() for ln in text.splitlines()]
            for ln in lines:
                if ln.startswith('# '):
                    title = ln[2:].strip()
                    break
            # If JSON parsing failed, don't use the raw text - it might be malformed JSON
            # Instead, return empty content to trigger fallback
            cleaned = ""

        # Final sanitation
        if not cleaned:
            return "", ""
        if not title:
            # Derive title from first H1 in cleaned content
            for ln in cleaned.splitlines():
                ln = ln.strip()
                if ln.startswith('# '):
                    title = ln[2:].strip()
                    break
        return cleaned, title
    except Exception as e:
        raise RuntimeError(f"OpenAI cleaning failed: {e}")

def crawl_single_url(url: str) -> dict:
    """
    Crawl a single URL using Bright Data API for scraping and GPT-4o mini LLM for content cleaning.
    This provides professional web scraping with intelligent content extraction that removes
    navigation, headers, footers, and boilerplate while preserving core informational content.
    """
    if not BRIGHTDATA_API_TOKEN:
        logger.error("❌ BRIGHTDATA_API_TOKEN not found in environment variables. Cannot scrape.")
        return {
            'url': url, 'title': '', 'content': "Error: BRIGHTDATA_API_TOKEN not set.",
            'success': False, 'word_count': 0, 'extraction_method': 'brightdata_error'
        }

    api_url = "https://api.brightdata.com/request?async=true"
    payload = json.dumps({
      "zone": "web_unlocker1",
      "url": url,
      "format": "raw",
      "method": "GET",
      "country": "US",
      "data_format": "markdown"  # Using markdown format for better content extraction
    })
    
    headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'Authorization': f'Bearer {BRIGHTDATA_API_TOKEN}'
    }

    try:
        response = requests.request("POST", api_url, headers=headers, data=payload, timeout=120)
        response.raise_for_status()
        
        # Check for Bright Data response headers that might indicate a scraping failure
        if 'x-response-code' in response.headers and response.headers['x-response-code'] != '200':
             logger.error(f"❌ Bright Data failed to load {url}. Status: {response.headers.get('x-response-code')}, Body: {response.text[:200]}")
             return {
                'url': url, 'title': '', 'content': f"Error from Bright Data. Status: {response.headers.get('x-response-code')}",
                'success': False, 'word_count': 0, 'extraction_method': 'brightdata_failed_load'
            }
        
        markdown_content = response.text

        # Use our sophisticated content extractor to clean the markdown and extract content
        cleaned_content, extracted_title = extract_clean_content_from_markdown(markdown_content)

        # Use extracted title or fallback to URL path
        title = extracted_title if extracted_title else urlparse(url).path

        return {
            'url': url,
            'title': title,
            'content': cleaned_content,
            'success': True,
            'word_count': len(cleaned_content.split()),
            'extraction_method': 'brightdata_markdown_llm_cleanup'
        }

    except requests.RequestException as e:
        logger.error(f"❌ Error during Bright Data API call for {url}: {e}")
        return {
            'url': url, 'title': '', 'content': f"Error calling Bright Data API: {str(e)}",
            'success': False, 'word_count': 0, 'extraction_method': 'brightdata_request_error'
        }

def scrape_single_url(url: str, custom_metadata: Dict[str, str], output_dir: str, use_llm_categories: bool = True) -> dict:
    """
    Scrape a single URL and save it to the appropriate location with proper metadata.
    Returns summary statistics similar to the full crawl.
    """
    logger.info(f"🎯 Scraping single URL: {url}")

    try:
        start_time = time.time()

        # Create output directories
        website_dir = os.path.join(output_dir, 'website')
        os.makedirs(website_dir, exist_ok=True)

        # Scrape the URL
        scrape_result = crawl_single_url(url)

        if not scrape_result['success']:
            logger.error(f"❌ Failed to scrape {url}: {scrape_result['content']}")
            return {
                'successful': 0,
                'failed': 1,
                'total_words': 0,
                'categories': {},
                'urls': [url]
            }

        # Create filename and save content
        filename = safe_filename(url)
        filepath = os.path.join(website_dir, filename)

        # Prepare metadata for the markdown file
        metadata = {
            'url': url,
            'scraped_at': datetime.now().isoformat(),
            'extraction_method': scrape_result['extraction_method'],
            'word_count': scrape_result['word_count'],
            **custom_metadata
        }

        # Categorize the URL if LLM categorization is enabled
        if use_llm_categories:
            try:
                # Use the synchronous categorization from the main async function
                # We'll set this to a simple fallback for now in single URL mode
                # TODO: Properly handle async categorization in single URL mode
                metadata['category'] = categorize_url_simple(url)
                logger.info(f"🏷️  Categorized as: {metadata['category']} (simple categorization)")

            except Exception as e:
                logger.warning(f"⚠️  Categorization failed: {e}")
                metadata['category'] = 'other'

        # Create YAML frontmatter
        yaml_frontmatter = "---\n"
        for key, value in metadata.items():
            yaml_frontmatter += f"{key}: {value}\n"
        yaml_frontmatter += "---\n\n"

        # Write the markdown file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(yaml_frontmatter)
            f.write(f"# {scrape_result['title']}\n\n")
            f.write(scrape_result['content'])

        logger.info(f"✅ Saved: {filepath}")
        logger.info(f"📊 Words: {scrape_result['word_count']}")

        # Save URL reference
        urls_file = os.path.join(output_dir, 'urls_discovered.txt')
        with open(urls_file, 'w', encoding='utf-8') as f:
            f.write(url + '\n')

        # Save categorization results
        categories_file = os.path.join(output_dir, 'url_categories.json')
        with open(categories_file, 'w', encoding='utf-8') as f:
            json.dump({url: metadata.get('category', 'other')}, f, indent=2, ensure_ascii=False)

        # Save scraping summary
        summary = {
            'total_urls_discovered': 1,
            'successful': 1,
            'failed': 0,
            'total_words': scrape_result['word_count'],
            'categories': {metadata.get('category', 'other'): 1},
            'extraction_methods': {scrape_result['extraction_method']: 1},
            'scraped_at': datetime.now().isoformat(),
            'custom_metadata': custom_metadata
        }

        summary_file = os.path.join(output_dir, 'scraping_summary.json')
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        end_time = time.time()
        duration = end_time - start_time

        logger.info(f"\n🎉 SINGLE URL SCRAPING COMPLETE!")
        logger.info(f"⏱️  Total time: {duration:.2f} seconds")
        logger.info(f"✅ Successfully scraped: 1/1")
        logger.info(f"📝 Words scraped: {scrape_result['word_count']:,}")
        logger.info(f"📂 Content saved to: {filepath}")

        return {
            'successful': 1,
            'failed': 0,
            'total_words': scrape_result['word_count'],
            'categories': {metadata.get('category', 'other'): 1},
            'urls': [url]
        }

    except Exception as e:
        logger.error(f"❌ Error scraping single URL {url}: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            'successful': 0,
            'failed': 1,
            'total_words': 0,
            'categories': {},
            'urls': [url]
        }

def safe_filename(url: str) -> str:
    """
    Convert a URL into a filesystem-safe markdown filename.
    """
    try:
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        if not path:
            name = 'index'
        else:
            name = path.replace('/', '_')
        # Remove query and fragment markers
        name = name.replace('?', '_').replace('&', '_').replace('=', '_').replace('#', '_')
        # Trim overly long names
        if len(name) > 180:
            name = name[:180]
        return f"{name}.md"
    except Exception:
        return "page.md"

# LLM-based URL categorization system
CATEGORIZATION_SYSTEM_PROMPT = """
Your task is to categorize website URLs based on the type of content likely found on each page.

Begin with a concise checklist (3-7 bullets) of what you will do; keep items conceptual, not implementation-level.

## Category Definitions
- **homepage**: The company's main or landing page.
- **services_products**: Pages describing specific services or products the company offers for sale.
- **industry_markets**: Pages detailing the industries or markets served by the company.
- **pricing**: Pages providing information about the cost or pricing of products or services.
- **case_studies**: Pages containing case studies or detailed success stories.
- **testimonials**: Pages devoted exclusively to customer testimonials.
- **blogs_resources**: Pages featuring blogs, resources, guides, or other thought leadership materials.
- **about**: Pages with background or general information about the company.
- **careers**: Pages related to employment, job openings, or hiring.
- **other**: Use this for URLs that cannot be confidently categorized using the options above.

## Categorization Rules
- Assign each URL to only one category from the list above.
- If a URL could fit into multiple categories, select the most specific and relevant category.
- If the input is invalid, empty, or not a well-formed URL, categorize it as "other".
- Set reasoning_effort = minimal; ensure decisions are efficient and only escalate if ambiguous cases arise.

## Input Handling
- Input is a list of URLs. If a single URL is provided, respond with a list containing one item.
- Maintain the original order of URLs in your output.
- Each category value must exactly match one of the defined category names listed above (spelling and case sensitive).

## Output Format
Return ONLY the category name as a single word from the list above. Do not return JSON, explanations, or any other text.
Example outputs: "homepage", "services_products", "blogs_resources", "other"
"""

VALID_CATEGORIES = [
    'homepage', 'services_products', 'industry_markets', 'pricing', 
    'case_studies', 'testimonials', 'blogs_resources', 'about', 'careers', 'other'
]

async def categorize_single_url_with_llm(url: str, client: AsyncOpenAI) -> tuple[str, str]:
    """Categorize a single URL using LLM"""
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": CATEGORIZATION_SYSTEM_PROMPT},
                {"role": "user", "content": f"categorize the url: {url}"}
            ],
            temperature=0.1,  # Lower temperature for more consistent categorization
            max_tokens=50,
            top_p=1
        )
        
        category = response.choices[0].message.content.strip()
        
        # Try to parse as JSON first (in case LLM returns JSON despite instructions)
        try:
            import json
            parsed = json.loads(category)
            if isinstance(parsed, dict):
                # Handle {"categories": ["blogs_resources"]} format
                if 'categories' in parsed and isinstance(parsed['categories'], list) and len(parsed['categories']) > 0:
                    category = parsed['categories'][0]
                # Handle {"category": "blogs_resources"} format
                elif 'category' in parsed:
                    category = parsed['category']
        except (json.JSONDecodeError, KeyError, IndexError):
            # Not JSON, use as-is
            pass
        
        category = category.strip().lower()
        
        if category not in VALID_CATEGORIES:
            logger.warning(f"⚠️  Invalid category '{category}' for {url}, defaulting to 'other'")
            category = 'other'
            
        return url, category
        
    except Exception as e:
        logger.error(f"❌ Error categorizing {url}: {e}")
        return url, 'other'

async def categorize_urls_with_llm(urls: List[str]) -> Dict[str, str]:
    """Categorize multiple URLs using LLM in parallel"""
    try:
        # Load OpenAI API key
        load_dotenv()
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.error("❌ OPENAI_API_KEY not found in environment")
            logger.warning("⚠️  Falling back to simple regex-based categorization")
            return {url: categorize_url_simple(url) for url in urls}
        
        client = AsyncOpenAI(api_key=api_key)
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize OpenAI client: {e}")
        logger.warning("⚠️  Falling back to simple regex-based categorization")
        return {url: categorize_url_simple(url) for url in urls}
    
    logger.info(f"🤖 Categorizing {len(urls)} URLs using LLM...")
    
    # Process in batches to avoid rate limits
    batch_size = 10
    results = {}
    
    for i in range(0, len(urls), batch_size):
        batch = urls[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(urls) + batch_size - 1) // batch_size
        
        logger.info(f"🔄 Processing batch {batch_num}/{total_batches} ({len(batch)} URLs)")
        
        tasks = [categorize_single_url_with_llm(url, client) for url in batch]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in batch_results:
            if isinstance(result, Exception):
                logger.error(f"❌ Batch error: {result}")
            else:
                url, category = result
                results[url] = category
        
        # Rate limiting between batches
        if i + batch_size < len(urls):
            await asyncio.sleep(1)
    
    logger.info(f"✅ LLM categorization complete")
    return results

def categorize_url_simple(url: str) -> str:
    """Simple regex-based categorization as fallback"""
    path = urlparse(url).path.lower()
    
    # Check for homepage
    if path in ['', '/']:
        return 'homepage'
    
    # Simple pattern matching
    if any(keyword in path for keyword in ['/blog', '/news', '/article', '/post', '/resource', '/guide']):
        return 'blogs_resources'
    elif any(keyword in path for keyword in ['/case-study', '/case-studies', '/portfolio']):
        return 'case_studies'
    elif any(keyword in path for keyword in ['/product', '/service', '/solution']):
        return 'services_products'
    elif any(keyword in path for keyword in ['/about', '/company', '/team']):
        return 'about'
    elif any(keyword in path for keyword in ['/pricing', '/plans', '/price']):
        return 'pricing'
    elif any(keyword in path for keyword in ['/career', '/job', '/hiring', '/recruit']):
        return 'careers'
    elif any(keyword in path for keyword in ['/testimonial', '/review', '/client']):
        return 'testimonials'
    elif any(keyword in path for keyword in ['/industry', '/market', '/sector']):
        return 'industry_markets'
    else:
        return 'other'

def crawl_parallel(urls: List[str], custom_metadata: dict, output_dir: str, max_workers: int = 4, url_categories: Dict[str, str] = None) -> dict:
    """Crawl URLs in parallel and save as markdown files with LLM-based categorization"""
    
    logger.info(f"🚀 Processing {len(urls)} URLs with {max_workers} workers")
    
    results = {
        'successful': 0,
        'failed': 0,
        'urls_processed': [],
        'total_words': 0,
        'categories': {}
    }
    
    website_dir = os.path.join(output_dir, 'website')
    os.makedirs(website_dir, exist_ok=True)
    
    def process_single_url(url_data):
        """Process a single URL and save as markdown"""
        url, idx = url_data
        if idx % 10 == 0:
            logger.info(f"📊 Processing URL {idx+1}/{len(urls)}: {urlparse(url).path}")
        
        # Scrape content
        scrape_result = crawl_single_url(url)
        
        if scrape_result['success']:
            # Get LLM-based category or fallback to simple categorization
            content_type = url_categories.get(url, categorize_url_simple(url)) if url_categories else categorize_url_simple(url)
            
            # Create comprehensive metadata
            parsed_url = urlparse(url)
            metadata = {
                'source': 'website',  # Always 'website' for scraped pages
                'content_type': content_type,  # LLM-categorized content type
                'url': url,
                'title': scrape_result['title'],
                'domain': parsed_url.netloc,
                'path': parsed_url.path,
                'scraped_time': datetime.now().isoformat(),
                'url_depth': len([p for p in parsed_url.path.split('/') if p]),
                'word_count': scrape_result['word_count'],
                **custom_metadata
            }
            
            # Save as markdown with frontmatter
            filename = safe_filename(url)
            filepath = os.path.join(website_dir, filename)
            
            # Create markdown content with frontmatter
            frontmatter = "---\n"
            for key, value in metadata.items():
                if isinstance(value, str):
                    # Escape quotes and clean value for YAML frontmatter
                    clean_value = value.replace('"', '\\"').replace('\n', ' ').replace('\r', ' ')
                    frontmatter += f"{key}: \"{clean_value}\"\n"
                else:
                    frontmatter += f"{key}: {value}\n"
            frontmatter += "---\n\n"
            
            # Don't add title manually - our content extractor already preserves document structure
            markdown_content = frontmatter + scrape_result['content']
            
            # Save file
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)
                
                return {
                    'url': url,
                    'success': True,
                    'words': scrape_result['word_count'],
                    'category': content_type,
                    'filename': filename
                }
            except Exception as e:
                logger.error(f"❌ Failed to save {filename}: {e}")
        
        return {'url': url, 'success': False, 'words': 0, 'category': 'failed'}
    
    # Process with thread pool
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        url_data = [(url, idx) for idx, url in enumerate(urls)]
        futures = [executor.submit(process_single_url, data) for data in url_data]
        
        completed = 0
        for future in as_completed(futures):
            try:
                result = future.result()
                completed += 1
                
                if result['success']:
                    results['successful'] += 1
                    results['urls_processed'].append(result['url'])
                    results['total_words'] += result['words']
                    
                    # Track categories
                    category = result['category']
                    results['categories'][category] = results['categories'].get(category, 0) + 1
                    
                    logger.info(f"💾 Saved: {result['filename']} ({result['words']} words) [{category}]")
                else:
                    results['failed'] += 1
                
                if completed % 10 == 0:
                    progress = completed / len(urls) * 100
                    logger.info(f"📈 Progress: {progress:.1f}% ({completed}/{len(urls)})")
                    
            except Exception as e:
                logger.error(f"❌ Thread error: {e}")
                results['failed'] += 1
                completed += 1
    
    return results

def save_scraping_summary(urls: List[str], results: dict, output_dir: str, custom_metadata: dict):
    """Save comprehensive scraping summary"""
    os.makedirs(output_dir, exist_ok=True)
    
    # Save all discovered URLs
    urls_file = os.path.join(output_dir, 'urls_discovered.txt')
    with open(urls_file, 'w', encoding='utf-8') as f:
        for url in sorted(urls):
            f.write(url + '\n')
    
    # Save successful URLs
    success_file = os.path.join(output_dir, 'urls_successful.txt')
    with open(success_file, 'w', encoding='utf-8') as f:
        for url in sorted(results['urls_processed']):
            f.write(url + '\n')
    
    # Save comprehensive summary
    summary = {
        'scraping_summary': {
            'total_urls_discovered': len(urls),
            'successful_scrapes': results['successful'],
            'failed_scrapes': results['failed'],
            'success_rate': f"{(results['successful'] / len(urls) * 100):.1f}%" if urls else "0%",
            'total_words_scraped': results['total_words'],
            'categories': results['categories'],
            'custom_metadata_applied': custom_metadata,
            'scrape_time': datetime.now().isoformat()
        }
    }
    
    summary_file = os.path.join(output_dir, 'scraping_summary.json')
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    logger.info(f"💾 Summary saved to {summary_file}")

async def main_async():
    """Async main function to handle LLM categorization"""
    parser = argparse.ArgumentParser(
        description='Scrape client website content and save as markdown files with LLM categorization',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Required arguments
    parser.add_argument('--url', '-u', required=True,
                       help='Website URL (base URL for sitemap discovery, or specific URL when using --single-url)')
    
    # Optional arguments
    parser.add_argument('--workers', '-w', type=int, default=8,
                       help='Number of parallel workers for faster processing (default: 4)')
    parser.add_argument('--output-dir', '-o', default='ingestion/client_ingestion_outputs',
                       help='Output directory for website folder and logs (default: ingestion/client_ingestion_outputs)')
    parser.add_argument('--no-llm-categories', action='store_true',
                       help='Disable LLM categorization and use simple keyword-based categorization instead (LLM categories enabled by default)')
    parser.add_argument('--single-url', action='store_true',
                       help='Scrape only the specified URL instead of crawling the entire sitemap (default: False)')
    parser.add_argument('--max-per-category', type=int, default=100,
                       help='Maximum number of URLs to scrape per category (default: 100)')
    parser.add_argument('--max-total-urls', type=int, default=500,
                       help='Maximum total URLs to process (default: 500)')
    
    # Metadata arguments
    parser.add_argument('--client-name', default='',
                       help='Client name to add to metadata')
    parser.add_argument('--project-name', default='',
                       help='Project name to add to metadata')
    parser.add_argument('--metadata', action='append',
                       help='Custom metadata in key=value format (can be used multiple times)')
    
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Validate URL
    if not args.url.startswith(('http://', 'https://')):
        args.url = 'https://' + args.url
    
    # Parse custom metadata
    custom_metadata = {}
    
    if args.client_name:
        custom_metadata['client_name'] = args.client_name
    if args.project_name:
        custom_metadata['project_name'] = args.project_name
        
    if args.metadata:
        for meta_arg in args.metadata:
            if '=' in meta_arg:
                key, value = meta_arg.split('=', 1)
                custom_metadata[key.strip()] = value.strip()
            else:
                logger.warning(f"Invalid metadata format: {meta_arg}. Use key=value format.")
    
    logger.info(f"🌐 Starting website scraping: {args.url}")
    logger.info(f"⚡ Workers: {args.workers}")
    logger.info(f"📁 Output: {args.output_dir}/website/")
    use_llm_categories = not args.no_llm_categories
    logger.info(f"🤖 LLM Categorization: {'Enabled' if use_llm_categories else 'Disabled (--no-llm-categories flag used)'}")
    logger.info(f"🧠 Content Extraction: Bright Data + LLM cleanup")
    logger.info(f"🎯 Mode: {'Single URL' if args.single_url else 'Full Sitemap Crawl'}")

    if custom_metadata:
        logger.info(f"🏷️  Custom metadata: {custom_metadata}")

    try:
        start_time = time.time()

        # Handle single URL vs. full sitemap crawl
        if args.single_url:
            logger.info("🎯 SINGLE URL MODE: Scraping only the specified URL")

            # Scrape single URL
            results = scrape_single_url(args.url, custom_metadata, args.output_dir, use_llm_categories)

            # Final summary
            end_time = time.time()
            duration = end_time - start_time

            logger.info(f"\n🎉 SINGLE URL SCRAPING COMPLETE!")
            logger.info(f"⏱️  Total time: {duration:.2f} seconds")
            logger.info(f"✅ Successfully scraped: {results['successful']}")
            logger.info(f"❌ Failed: {results['failed']}")
            logger.info(f"📝 Total words scraped: {results['total_words']:,}")
            logger.info(f"📂 Content saved to: {args.output_dir}/website/")

            if duration > 0:
                logger.info(f"🚀 Scraping speed: {results['successful']/duration:.1f} URLs/second")

            return 0

        # Default behavior: Full sitemap crawl
        logger.info("🔍 Discovering URLs from sitemap...")
        
        sitemap_candidates = discover_sitemaps(args.url)
        all_urls = []
        
        for sitemap_url in sitemap_candidates:
            logger.info(f"📋 Checking sitemap: {sitemap_url}")
            urls = get_urls_from_sitemap(sitemap_url)
            if urls:
                all_urls.extend(urls)
                logger.info(f"✅ Found {len(urls)} URLs in {sitemap_url}")
        
        # Remove duplicates and fallback if no URLs found
        all_urls = list(set(all_urls))
        if not all_urls:
            all_urls = [args.url]
            logger.info(f"⚠️  No sitemap URLs found, using base URL only")
        
        # Apply total URL cap to prevent runaway scraping
        original_count = len(all_urls)
        max_total_urls = args.max_total_urls
        if len(all_urls) > max_total_urls:
            logger.warning(f"⚠️  Found {len(all_urls)} URLs, capping at {max_total_urls} to prevent runaway scraping")
            # Prioritize URLs: homepage first, then by URL length (shorter = more important)
            all_urls.sort(key=lambda x: (x != args.url, len(x)))
            all_urls = all_urls[:max_total_urls]
            logger.info(f"📊 Limited from {original_count} to {len(all_urls)} URLs")

        logger.info(f"📊 Total unique URLs to process: {len(all_urls)}")
        
        # Save discovered URLs for reference
        os.makedirs(args.output_dir, exist_ok=True)
        urls_file = os.path.join(args.output_dir, 'urls_discovered.txt')
        with open(urls_file, 'w', encoding='utf-8') as f:
            for url in sorted(all_urls):
                f.write(url + '\n')
        
        # Step 2: Categorize URLs with LLM by default
        url_categories = {}
        if use_llm_categories:
            url_categories = await categorize_urls_with_llm(all_urls)
            
            # Save categorization results
            categories_file = os.path.join(args.output_dir, 'url_categories.json')
            with open(categories_file, 'w', encoding='utf-8') as f:
                json.dump(url_categories, f, indent=2, ensure_ascii=False)
            logger.info(f"🏷️  URL categories saved to: {categories_file}")
        else:
            # If LLM categorization disabled, do simple categorization
            url_categories = {u: categorize_url_simple(u) for u in all_urls}
        
        # Apply per-category cap
        max_per = max(1, args.max_per_category)
        by_cat = {}
        for u, c in url_categories.items():
            by_cat.setdefault(c, []).append(u)
        limited_urls = []
        for c, urls in by_cat.items():
            if len(urls) > max_per:
                logger.info(f"🔎 Limiting category '{c}' from {len(urls)} to {max_per} URLs")
                limited_urls.extend(urls[:max_per])
            else:
                limited_urls.extend(urls)
        
        logger.info(f"📊 URLs after per-category cap ({max_per}): {len(limited_urls)} (from {len(all_urls)})")
        
        # Step 3: Crawl URLs in parallel
        results = crawl_parallel(limited_urls, custom_metadata, args.output_dir, args.workers, url_categories)
        
        # Step 4: Save summary
        save_scraping_summary(all_urls, results, args.output_dir, custom_metadata)
        
        # Final summary
        end_time = time.time()
        duration = end_time - start_time
        
        logger.info(f"\n🎉 WEBSITE SCRAPING COMPLETE!")
        logger.info(f"⏱️  Total time: {duration:.2f} seconds")
        logger.info(f"📊 URLs discovered: {len(all_urls)}")
        logger.info(f"✅ Successfully scraped: {results['successful']}")
        logger.info(f"❌ Failed: {results['failed']}")
        logger.info(f"📝 Total words scraped: {results['total_words']:,}")
        
        if duration > 0:
            logger.info(f"🚀 Scraping speed: {results['successful']/duration:.1f} URLs/second")
        
        logger.info(f"📂 Content saved to: {args.output_dir}/website/")
        logger.info(f"📂 Content categories:")
        for category, count in results['categories'].items():
            logger.info(f"   {category}: {count} pages")
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("🛑 Scraping interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"❌ Error during website scraping: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return 1

async def run_website_ingestion_async(
    url: str,
    output_dir: str,
    client_name: str,
    workers: int = 4,
    use_llm_categories: bool = True,
    single_url: bool = False,
    max_per_category: int = 100,
    max_total_urls: int = 500,  # Cap total URLs to prevent runaway scraping
    project_name: str = "",
    extra_metadata: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Programmatic async entrypoint for website ingestion.
    Returns a dict with summary information.
    """
    load_dotenv()

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    custom_metadata: Dict[str, str] = {}
    if client_name:
        custom_metadata["client_name"] = client_name
    if project_name:
        custom_metadata["project_name"] = project_name
    if extra_metadata:
        custom_metadata.update(extra_metadata)

    os.makedirs(output_dir, exist_ok=True)

    try:
        start_time = time.time()

        if single_url:
            # Single URL path
            results = scrape_single_url(url, custom_metadata, output_dir, use_llm_categories)
            duration = time.time() - start_time
            return {
                "status": "success",
                "mode": "single_url",
                "url": url,
                "successful": results.get("successful", 0),
                "failed": results.get("failed", 0),
                "total_words": results.get("total_words", 0),
                "output_dir": output_dir,
                "duration_sec": duration,
            }

        # Full crawl path
        sitemap_candidates = discover_sitemaps(url)
        all_urls: List[str] = []
        for sitemap_url in sitemap_candidates:
            urls = get_urls_from_sitemap(sitemap_url)
            if urls:
                all_urls.extend(urls)
        all_urls = list(set(all_urls))
        if not all_urls:
            all_urls = [url]

        # Apply total URL cap BEFORE categorization to save on API costs
        original_count = len(all_urls)
        if len(all_urls) > max_total_urls:
            logger.warning(f"⚠️  Found {len(all_urls)} URLs, capping at {max_total_urls} to prevent runaway scraping")
            # Prioritize URLs: homepage first, then by URL length (shorter = more important)
            all_urls.sort(key=lambda x: (x != url, len(x)))
            all_urls = all_urls[:max_total_urls]
            logger.info(f"📊 Limited from {original_count} to {len(all_urls)} URLs")

        # Save discovered URLs
        urls_file = os.path.join(output_dir, "urls_discovered.txt")
        with open(urls_file, 'w', encoding='utf-8') as f:
            for u in sorted(all_urls):
                f.write(u + "\n")

        url_categories: Dict[str, str] = {}
        if use_llm_categories:
            url_categories = await categorize_urls_with_llm(all_urls)
            categories_file = os.path.join(output_dir, 'url_categories.json')
            with open(categories_file, 'w', encoding='utf-8') as f:
                json.dump(url_categories, f, indent=2, ensure_ascii=False)
        else:
            url_categories = {u: categorize_url_simple(u) for u in all_urls}

        # Enforce per-category cap
        max_per = max(1, int(max_per_category))
        by_cat: Dict[str, List[str]] = {}
        for u, c in url_categories.items():
            by_cat.setdefault(c, []).append(u)
        limited_urls: List[str] = []
        for c, urls in by_cat.items():
            limited_urls.extend(urls[:max_per])

        results = crawl_parallel(limited_urls, custom_metadata, output_dir, workers, url_categories)
        save_scraping_summary(all_urls, results, output_dir, custom_metadata)

        duration = time.time() - start_time
        return {
            "status": "success",
            "mode": "full",
            "total_urls": len(all_urls),
            "processed_urls": len(limited_urls),
            "successful": results.get("successful", 0),
            "failed": results.get("failed", 0),
            "total_words": results.get("total_words", 0),
            "output_dir": output_dir,
            "duration_sec": duration,
        }
    except Exception as e:
        logger.error(f"❌ Error in programmatic website ingestion: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"status": "error", "error": str(e)}

def main():
    """Wrapper to run async main function"""
    return asyncio.run(main_async())

if __name__ == "__main__":
    sys.exit(main())
