import { NextResponse } from 'next/server';

export async function GET() {
  const envStatus = {
    UPSTASH_REDIS_REST_URL: !!process.env.UPSTASH_REDIS_REST_URL,
    UPSTASH_REDIS_REST_TOKEN: !!process.env.UPSTASH_REDIS_REST_TOKEN,
    UPSTASH_SEARCH_REST_URL: !!process.env.UPSTASH_SEARCH_REST_URL,
    UPSTASH_SEARCH_REST_TOKEN: !!process.env.UPSTASH_SEARCH_REST_TOKEN,
    FIRECRAWL_API_KEY: !!process.env.FIRECRAWL_API_KEY,
    OPENAI_API_KEY: !!process.env.OPENAI_API_KEY,
  };

  console.log('[DEBUG] Environment variable status:', envStatus);

  return NextResponse.json({ envStatus });
}

