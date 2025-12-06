import os

from upstash_search import Search


def main():
    # Configure from env for safety; fallback to sample host/token/index if desired
    url = os.environ.get("UPSTASH_SEARCH_REST_URL", "https://assuring-stingray-92074-gcp-usc1-search.upstash.io")
    token = os.environ.get("UPSTASH_SEARCH_REST_TOKEN", "ACAFMGFzc3VyaW5nLXN0aW5ncmF5LTkyMDc0LWdjcC11c2MxYWRtaW5ZVGt5WXpCbU5qY3RNamRtT0MwME1XTTBMV0k1T1RrdFpUY3pNR05pTWpjM01qZzM=")
    index_name = os.environ.get("UPSTASH_SEARCH_INDEX", "test")

    client = Search(url=url, token=token)
    index = client.index(index_name)

    # Sample scrape-like payload for mintleads.io
    documents = [
  {
    "id": "mintleads-home",
    "content": {
      "text": "We’ll change the way you grow your business. Done-for-you B2B lead generation. No More Cold Outreach: we vet prospects and connect you only to qualified leads. Your Ideal Prospects: campaigns built from scratch for your audience. Calls on Your Calendar: phone/video booked directly. Money-Back Guarantee. Process: List Building; Email Copy That Converts (50–80% open rates); Discovery Call; Outreach Campaign; Calls on Calendar. Pricing tiers: BOOST (single vertical, 2.5k targets/mo); GROW (two+ verticals, 5k targets/mo, CRM); SCALE (unlimited, 10k targets/mo, custom qualification). Testimonials highlight results and quality. CTA: Book Your Discovery Call.",
      "url": "https://mintleads.io/",
      "title": "MintLeads | Done-for-you Lead Generation"
    },
    "metadata": {
      "namespace": "mintleads",
      "title": "MintLeads | Done-for-you Lead Generation",
      "url": "https://mintleads.io/",
      "sourceURL": "https://mintleads.io/",
      "description": "Mint Leads provides lead generation for digital marketing agencies connecting with e-commerce brands, SaaS, and SMB.",
      "fullContent": "<scraped markdown>",
      "index": "mintleads"
    }
  },
  {
    "id": "mintleads-pricing",
    "content": {
      "text": "Pricing tiers: BOOST (add $250k ARR, single vertical, 2.5k targets/mo, campaign mgmt, monthly updates). GROW (add $500k ARR, two+ verticals, multiple products, 5k targets/mo, bi-weekly updates, CRM integration). SCALE (add $1.5M ARR, unlimited verticals, sales asset consult, 10k targets/mo, weekly updates, custom lead qualification). Each tier includes list building, high-open email copy, and money-back guarantee.",
      "url": "https://mintleads.io/",
      "title": "MintLeads Pricing"
    },
    "metadata": {
      "namespace": "mintleads",
      "title": "MintLeads Pricing",
      "url": "https://mintleads.io/",
      "sourceURL": "https://mintleads.io/",
      "description": "Boost, Grow, Scale plans with volume and qualification options.",
      "fullContent": "<scraped markdown>",
      "index": "mintleads"
    }
  }
]

    index.upsert(documents=documents)

    search_results = index.search(
        query="outreach automation",
        limit=2,
        filter="metadata.namespace = 'mintleads'",
    )

    print("Search results:", search_results)


if __name__ == "__main__":
    main()

