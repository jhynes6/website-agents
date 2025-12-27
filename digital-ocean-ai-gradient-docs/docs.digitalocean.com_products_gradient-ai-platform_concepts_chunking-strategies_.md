---
url: "https://docs.digitalocean.com/products/gradient-ai-platform/concepts/chunking-strategies/"
title: "Chunking Best Practices for Knowledge Base Indexing in DigitalOcean Gradient™ AI Platform | DigitalOcean Documentation"
---

- [DigitalOcean \| Docs](https://docs.digitalocean.com/)

- [Platform](https://docs.digitalocean.com/platform/)
- [Products](https://docs.digitalocean.com/products/)
- [Reference](https://docs.digitalocean.com/reference/)
- [Support](https://docs.digitalocean.com/support/)
- [Sign Up](https://cloud.digitalocean.com/registrations/new)

- [![](https://docs.digitalocean.com/images/icons/gradient-ai-platform.d44093369d163f66a792e27c3d48418be24ba1c7d9e216e99032e5cd6c166096.svg)Gradient AI Platform](https://docs.digitalocean.com/products/gradient-ai-platform/)
- [Getting Started](https://docs.digitalocean.com/products/gradient-ai-platform/getting-started/)
  - [Quickstart](https://docs.digitalocean.com/products/gradient-ai-platform/getting-started/quickstart/)
  - [Test and Compare Models](https://docs.digitalocean.com/products/gradient-ai-platform/getting-started/use-model-playground/)
  - [Use Agent Development Kitpublic](https://docs.digitalocean.com/products/gradient-ai-platform/getting-started/use-adk/)
- [How-Tos](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/)
  - [Use Serverless Inference](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/use-serverless-inference/)
  - [Build Agents Using Agent Development Kitpublic](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/build-agents-using-adk/)
  - [Create Agents](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/create-agents/)
  - [Manage Partner Provider Model Keys](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/manage-model-provider-keys/)
  - [Manage Workspaces](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/manage-workspaces/)
  - [Configure Model Settings](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/configure-models/)
  - [Use Agents](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/use-agents/)
  - [Test Agents](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/test-agents/)
  - [Evaluate Agents](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/evaluate-agents/)
  - [Create Evaluation Dataset](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/create-evaluation-datasets/)
  - [View Agent Insights and Logs](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/view-agent-observability/)
  - [Trace Agent Responses](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/trace-agents/)
  - [Route to Multiple Agents](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/route-agents/)
  - [Route Functions in Agents](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/route-agent-functions/)
  - [Manage Agent Versions](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/manage-agent-versions/)
  - [Create and Manage Knowledge Bases](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/create-manage-agent-knowledge-bases/)
  - [Attach and Detach Agent Knowledge Bases](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/attach-agent-knowledge-bases/)
  - [Manage Agent Guardrails](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/manage-agent-guardrails/)
  - [Destroy Agents](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/destroy-agents/)
- [Reference](https://docs.digitalocean.com/products/gradient-ai-platform/reference/)
  - [API Reference](https://docs.digitalocean.com/reference/api/digitalocean/#tag/GradientAI-Platform)
  - [doctl CLI Reference](https://docs.digitalocean.com/reference/doctl/reference/genai/)
  - [gradient CLI Referencepublic](https://github.com/digitalocean/gradient-adk)
  - [Python SDK Reference](https://gradientai-sdk.digitalocean.com/api/python)
  - [Agent Evaluation Metrics](https://docs.digitalocean.com/products/gradient-ai-platform/reference/agent-evaluation-metrics/)
  - [Agent Tracing Data](https://docs.digitalocean.com/products/gradient-ai-platform/reference/agent-tracing-metrics/)
  - [Chunking Parameterspublic](https://docs.digitalocean.com/products/gradient-ai-platform/reference/chunking-strategies/)
- [Concepts](https://docs.digitalocean.com/products/gradient-ai-platform/concepts/)
  - [Context Management Best Practices](https://docs.digitalocean.com/products/gradient-ai-platform/concepts/context-management/)
  - [Agent Instructions Best Practices](https://docs.digitalocean.com/products/gradient-ai-platform/concepts/agent-instructions/)
  - [Function Instructions Best Practices](https://docs.digitalocean.com/products/gradient-ai-platform/concepts/function-instructions/)
  - [Prompt Writing Best Practices](https://docs.digitalocean.com/products/gradient-ai-platform/concepts/prompts/)
  - [Effectively Use Workspaces](https://docs.digitalocean.com/products/gradient-ai-platform/concepts/workspaces/)
  - [Chunking Best Practicespublic](https://docs.digitalocean.com/products/gradient-ai-platform/concepts/chunking-strategies/)
- [Details](https://docs.digitalocean.com/products/gradient-ai-platform/details/)
  - [Features](https://docs.digitalocean.com/products/gradient-ai-platform/details/features/)
  - [Pricing](https://docs.digitalocean.com/products/gradient-ai-platform/details/pricing/)
  - [Availability](https://docs.digitalocean.com/products/gradient-ai-platform/details/availability/)
  - [Limits](https://docs.digitalocean.com/products/gradient-ai-platform/details/limits/)
  - [Available Models](https://docs.digitalocean.com/products/gradient-ai-platform/details/models/)
  - [Data Privacy](https://docs.digitalocean.com/products/gradient-ai-platform/details/data-privacy/)
- [Support](https://docs.digitalocean.com/products/gradient-ai-platform/support/)

- [Concepts](https://docs.digitalocean.com/products/gradient-ai-platform/concepts/)
- Chunking Best Practices

[Give Feedback](https://ideas.digitalocean.com/documentation)

# Chunking Best Practices for Knowledge Base Indexing in DigitalOcean Gradient™ AI Platformpublic

Validated on 8 Dec 2025 • Last edited on 17 Dec 2025

DigitalOcean Gradient™ AI Platform lets you build fully-managed AI agents with knowledge bases for retrieval-augmented generation, multi-agent routing, guardrails, and more, or use serverless inference to make direct requests to popular foundation models.

Chunking splits your documents into smaller, retrievable units before indexing. The chunking strategy you choose affects retrieval accuracy, indexing cost, and how much context your agent receives during inference. Gradient AI Platform supports several chunking strategies, each configurable per data source.

This guide explains how to choose and tune chunking strategies. For parameter definitions and model-specific ranges and recommendations, see the [chunking strategy parameters reference](https://docs.digitalocean.com/products/gradient-ai-platform/reference/chunking-strategies/#parameters) and the [embedding model catalog](https://docs.digitalocean.com/products/gradient-ai-platform/details/models/#embedding-model). To understand pricing implications, see the [knowledge base pricing page](https://docs.digitalocean.com/products/gradient-ai-platform/details/pricing/#knowledge-bases).

## General Best Practices

We recommend the following:

- Start with the default chunking settings, which work well for most documents.
- Configure chunking per data source and mix strategies within the same knowledge base.
- Consider [indexing and storage costs](https://docs.digitalocean.com/products/gradient-ai-platform/details/pricing/#knowledge-bases) when choosing a strategy, as different chunking methods consume tokens differently.

## Choosing Chunking Strategy

Chunking strategies differ significantly in indexing and retrieval cost. For example, semantic chunking increases indexing cost, while hierarchical chunking increases retrieval cost because parent and child chunks are returned together. For parameter recommendations, see the [parameters reference](https://docs.digitalocean.com/products/gradient-ai-platform/reference/chunking-strategies/#parameters).

The sections below describe when to use each strategy and how they behave during indexing.

### Section-Based Chunking

Uses structural elements such as headings, paragraphs, lists, tables, and callouts as natural boundaries. Adjacent sections are merged or split based on the maximum chunk size (`max_chunk_size`). Section-based chunking produces predictable, readable chunks.

Works best for:

- Product documentation
- Policies and SOPs
- FAQs
- Blogs
- Structured web content
- Markdown files

Choose this strategy if:

- Your document is already structured and has natural boundaries such as headings, paragraphs, lists, or tables.
- You need predictable, readable chunks.
- You want a fast, low-cost option.
- You want a strong baseline for structured content.

For more information, see the [section-based chunking reference](https://docs.digitalocean.com/products/gradient-ai-platform/reference/chunking-strategies/#section) and the [pricing page](https://docs.digitalocean.com/products/gradient-ai-platform/details/pricing/#knowledge-bases).

### Semantic Chunking

Groups text by meaning using the chosen embedding model. It performs two embedding passes:

- Detects semantic boundaries (`semantic_threshold`).
- Embeds the final chunks (`max_chunk_size`).

Semantic chunking produces more semantically aligned chunks, especially for documents without strong formatting.

Use when meaning matters more than formatting.

Works best for:

- Academic writing
- Research notes
- Long-form prose
- Dense or inconsistently structured content

Choose this strategy if:

- Your document groups content based on semantic similarity.
- You need to detect topical shifts even when formatting is poor.
- You need more accurate boundaries that reflect shifts in meaning.
- You can accept higher indexing cost; semantic chunking may increase cost by 1.5 to 3 times compared to other strategies.

For more information, see the [semantic chunking reference](https://docs.digitalocean.com/products/gradient-ai-platform/reference/chunking-strategies/#semantic) and the [pricing page](https://docs.digitalocean.com/products/gradient-ai-platform/details/pricing/#knowledge-bases).

### Hierarchical Chunking

Creates a two-level structure consisting of:

- Parent chunks for broad context (`parent_chunk_size`).
- Child chunks for precise retrieval (`child_chunk_size`).

When a child chunk is retrieved, the system automatically includes its parent chunk to improve grounding.

Use when both broad context and precise retrieval are required.

Works best for:

- API reference documentation
- Legal contracts
- Product manuals
- Highly structured technical content
- Documents requiring long-context reasoning

Choose this strategy if:

- You need both precise retrieval and broader contextual grounding.

Hierarchical chunking has indexing costs similar to section-based strategies, but retrieval costs are higher because parent and child chunks are included together.

For more information, see the [hierarchical chunking reference](https://docs.digitalocean.com/products/gradient-ai-platform/reference/chunking-strategies/#hierarchical) and the [pricing page](https://docs.digitalocean.com/products/gradient-ai-platform/details/pricing/#knowledge-bases).

### Fixed-Length Chunking

Splits text strictly by token count, ignoring formatting or meaning. This produces uniform chunk sizes and predictable indexing behavior.

Use when the document has unreliable formatting or when simplicity is preferred.

Works best for:

- Logs
- IoT telemetry
- OCR text
- Time-series or streaming text
- Machine-generated content
- Code
- Highly structured or repetitive data

Choose this strategy if:

- You want chunking based solely on token count.
- You can ignore document formatting and semantics.
- You need a fast, predictable behavior.
- You are indexing large-scale, unstructured, or repetitive content.

For more information, see the [fixed-length chunking reference](https://docs.digitalocean.com/products/gradient-ai-platform/reference/chunking-strategies/#fixed) and the [pricing page](https://docs.digitalocean.com/products/gradient-ai-platform/details/pricing/#knowledge-bases).

## Improve Chunking Performance

Chunking performance depends heavily on document clarity and formatting. Use the following evaluation loop to optimize your configuration:

1. Index the data source with the default settings.
2. Run an [Agent Evaluation](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/evaluate-agents/) to measure retrieval accuracy.
3. Inspect key retrieval metrics, such as retrieved context relevance, response-context completeness, context adherence, and retrieved chunk usage. For more details, see the [Agent Evaluation metrics reference](https://docs.digitalocean.com/products/gradient-ai-platform/reference/agent-evaluation-metrics/).
4. Modify the chunking strategy or parameters.
5. Re-index the data source and repeat as needed.

Re-indexing consumes tokens, so plan adjustments strategically.

In this article...

- [General Best Practices](https://docs.digitalocean.com/products/gradient-ai-platform/concepts/chunking-strategies/#general-best-practices)
- [Choosing Chunking Strategy](https://docs.digitalocean.com/products/gradient-ai-platform/concepts/chunking-strategies/#choosing-chunking-strategy)
  - [Section-Based Chunking](https://docs.digitalocean.com/products/gradient-ai-platform/concepts/chunking-strategies/#section)
  - [Semantic Chunking](https://docs.digitalocean.com/products/gradient-ai-platform/concepts/chunking-strategies/#semantic)
  - [Hierarchical Chunking](https://docs.digitalocean.com/products/gradient-ai-platform/concepts/chunking-strategies/#hierarchical)
  - [Fixed-Length Chunking](https://docs.digitalocean.com/products/gradient-ai-platform/concepts/chunking-strategies/#fixed)
- [Improve Chunking Performance](https://docs.digitalocean.com/products/gradient-ai-platform/concepts/chunking-strategies/#improve-chunking-performance)

##### Company

- [About](https://www.digitalocean.com/about)
- [Careers](https://www.digitalocean.com/careers)
- [Blog](https://www.digitalocean.com/blog)

##### Docs

- [Docs Home](https://docs.digitalocean.com/)
- [API Reference](https://docs.digitalocean.com/reference/api)
- [CLI Reference](https://docs.digitalocean.com/reference/doctl)
- [Release Notes](https://docs.digitalocean.com/release-notes)
- [Trust Platform](https://www.digitalocean.com/trust)

##### Community

- [Tutorials](https://www.digitalocean.com/community/tutorials)
- [Q&A](https://www.digitalocean.com/community/questions)
- [Write for DOnations](https://www.digitalocean.com/community/pages/write-for-digitalocean)
- [Currents Research](https://www.digitalocean.com/currents)
- [Legal](https://www.digitalocean.com/legal)
- [Code of Conduct](https://www.digitalocean.com/community/pages/code-of-conduct)

##### Support

- [Support Center](https://docs.digitalocean.com/support)
- [Report Abuse](https://www.digitalocean.com/company/contact/abuse)

* * *

Cookie Preferences

© 2025 DigitalOcean, LLC. All rights reserved

### We can't find any results for your search.

Try using different keywords or simplifying your search terms.

Loading...

## Product Docs

### We can't find any results for your search.

Try using different keywords or simplifying your search terms.

## Marketplace

## DigitalOcean Blog

## Community

navigategoexit

GenAI Agent - DigitalOcean

![DigitalOcean Docs Agent](https://product-docs.nyc3.cdn.digitaloceanspaces.com/ai-agent-icon.svg)

This site uses cookies and related technologies, as described in our [privacy policy](https://www.digitalocean.com/legal/privacy-policy/), for purposes that may include site operation, analytics, enhanced user experience, or advertising. You may choose to consent to our use of these technologies, or manage your own preferences. Please visit our [cookie policy](https://www.digitalocean.com/legal/cookie-policy) for more information.

Agree & ProceedDecline AllManage Choices