---
url: "https://docs.digitalocean.com/products/gradient-ai-platform/reference/agent-evaluation-metrics/"
title: "Agent Evaluation Metrics | DigitalOcean Documentation"
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

- [Reference](https://docs.digitalocean.com/products/gradient-ai-platform/reference/)
- Agent Evaluation Metrics

[Give Feedback](https://ideas.digitalocean.com/documentation)

# Agent Evaluation Metrics

Validated on 1 Jul 2025 • Last edited on 17 Dec 2025

DigitalOcean Gradient™ AI Platform lets you build fully-managed AI agents with knowledge bases for retrieval-augmented generation, multi-agent routing, guardrails, and more, or use serverless inference to make direct requests to popular foundation models.

## General Agent Quality

General agent quality metrics measure the overall quality of an agent’s responses, including correctness, instruction following, and safety. These metrics help ensure that agents provide accurate, relevant, and safe responses to user queries.

| Metric | Description | Returns | Recommendations |
| --- | --- | --- | --- |
| **Correctness (General Hallucinations)** | Measures how factually accurate the agent’s response is without using context. High score = likely accurate; low score = possible hallucinations or errors. | Number (0-100); high = likely accurate | Flag low scores, adjust prompt, prevent non-factual answers |
| **Instruction Following** | Measures how well the agent follows instructions. High = followed closely; low = ignored parts. | Number (0-100); Boolean (Yes/No) | Flag ignored instructions, reword or vary instructions, add safeguards |
| **Ground Truth Faithfulness** | Compares response to known correct output. High = semantically equivalent; low = different meaning. | % Yes judgments | Use with other metrics for full picture |
| **Prompt Perplexity** | Measures input prompt complexity and model confidence. Lower perplexity = better performance. | Number (0-100) | Lower perplexity, revise complex prompts |
| **PII Leaks** | Detects if input/output contains personally identifiable info (PII). | Boolean (Yes/No) | No recommendations |
| **Toxicity** | Flags hateful, offensive, or harmful content. | Boolean (Yes/No) | Apply guardrails, retrain agents, change models |
| **Tone** | Identifies emotional tone (Neutral, Joy, Love, Fear, etc.). | String | Align tone via agent instructions |
| **Sexism** | Flags sexist content; identifies harmful gender-based language. | Boolean (Yes/No) | Apply guardrails, retrain agents |
| **Prompt Injection** | Flags input designed to manipulate agent behavior. | Boolean (Yes/No) | Apply guardrails |
| **User Goal Progress (Action Advancement)** | Measures if the agent advanced the user’s task or question (partial/full answer, clarification, confirm action). | Number (0 to 100); 100 = advanced or accomplished at least one goal | No Recommendations |
| **User Goal Completion (Action Completion)** | Measures if the agent fully accomplished the user’s goal; must be accurate, comprehensive, aligned with tool outputs. | Number (0 to 100) | No Recommendations |

## RAG and Tool Correctness

RAG and Tool Correctness metrics evaluate how well agents use Retrieval-Augmented Generation (RAG) pipelines and external tools to provide accurate, relevant, and contextually grounded responses. These metrics help ensure that agents effectively leverage external knowledge and tools to enhance their responses.

| Metric | Description | Returns | Recommendations |
| --- | --- | --- | --- |
| **Context Adherence (Context Hallucinations)** | Measures whether the agent stays within the retrieved context when generating a response. High = relies only on provided facts; low = introduces unsupported information. | Number (0 to 1); score close to 1 means fully adherent; close to 0 means hallucinations likely. | No Recommendations |
| **Response-Context Completeness (Completeness)** | Measures how thoroughly the agent covers key details from the provided context. | Number (0 to 1) | Rewrite the prompt to explicitly ask for full inclusion of relevant info<br>Adjust prompt to encourage thorough coverage of key details |
| **Retrieved Chunk Usage (Chunk Attribution)** | Shows whether each chunk influenced the response. | Boolean (Yes/No) per chunk; also Number (N of K) for count of attributed chunks | Reduce number of retrieved chunks if many unused<br>Tune retrieval to balance recall and performance<br>Use attribution for debugging |
| **Retrieved Context Relevance (Context Relevance)** | Measures how relevant the retrieved context is to the input prompt; checks if the context supports the query. | Number (0 or 100); high = significant similarity or relevance. | No Recommendations |

In this article...

- [General Agent Quality](https://docs.digitalocean.com/products/gradient-ai-platform/reference/agent-evaluation-metrics/#general-agent-quality)
- [RAG and Tool Correctness](https://docs.digitalocean.com/products/gradient-ai-platform/reference/agent-evaluation-metrics/#rag-and-tool-correctness)

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