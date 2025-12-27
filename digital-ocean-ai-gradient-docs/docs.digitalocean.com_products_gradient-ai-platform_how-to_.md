---
url: "https://docs.digitalocean.com/products/gradient-ai-platform/how-to/"
title: "DigitalOcean Gradient™ AI Platform How-Tos | DigitalOcean Documentation"
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

- How-Tos

[Give Feedback](https://ideas.digitalocean.com/documentation)

# DigitalOcean Gradient™ AI Platform How-Tos

Generated on 22 Dec 2025

DigitalOcean Gradient™ AI Platform lets you build fully-managed AI agents with knowledge bases for retrieval-augmented generation, multi-agent routing, guardrails, and more, or use serverless inference to make direct requests to popular foundation models.

## Manage Models

![](https://docs.digitalocean.com/images/icons/gradient-ai-platform.svg)

How to Use Serverless Inference on DigitalOcean Gradient™ AI Platform

Create model access keys that allow you to send requests to foundation models without creating an agent.

![](https://docs.digitalocean.com/images/icons/gradient-ai-platform.svg)

Manage Partner Provider Model Keys

Add, edit, or delete API keys to use their models with your agents.

## Create Agents

![](https://docs.digitalocean.com/images/icons/gradient-ai-platform.svg)

Build Agents Using Agent Development Kit

Use Agent Development Kit to create and manage agents on Gradient™ AI Platform.

![](https://docs.digitalocean.com/images/icons/gradient-ai-platform.svg)

How to Create Agents on DigitalOcean Gradient™ AI Platform

Create an agent with domain-specific knowledge to provide information or take action.

## Manage Agents

![](https://docs.digitalocean.com/images/icons/gradient-ai-platform.svg)

How to Create and Manage Workspaces on DigitalOcean Gradient™ AI Platform

Create workspaces to group agents together and move agents between workspaces as needed.

![](https://docs.digitalocean.com/images/icons/gradient-ai-platform.svg)

Configure Model Settings

Evaluate, compare, and configure model settings in Model Playground.

![](https://docs.digitalocean.com/images/icons/gradient-ai-platform.svg)

Use Agents

Use your agent in an application or through a chat bot interface.

![](https://docs.digitalocean.com/images/icons/gradient-ai-platform.svg)

How to Route to Multiple Agents on DigitalOcean Gradient™ AI Platform

Integrate multiple generative AI agents.

![](https://docs.digitalocean.com/images/icons/gradient-ai-platform.svg)

How to Route Functions in Agents on DigitalOcean Gradient™ AI Platform

Enable the foundation model in your agent to access the external data sources using functions.

![](https://docs.digitalocean.com/images/icons/gradient-ai-platform.svg)

Manage Agent Versions

Rollback to a previous version of an agent to undo changes made to it.

![](https://docs.digitalocean.com/images/icons/gradient-ai-platform.svg)

Destroy Agents

Destroy an agent to permanently and irreversibly destroy the agent and removes all endpoints for the agent.

## Evaluate Agents

![](https://docs.digitalocean.com/images/icons/gradient-ai-platform.svg)

Test Agents

Test the full agent experience with the directions and features you’ve configured using the Agent Playground.

![](https://docs.digitalocean.com/images/icons/gradient-ai-platform.svg)

How to Evaluate Agent Performance on DigitalOcean Gradient™ AI Platform

Create test cases and measure how well your agents perform against for things like tone, factual accuracy, and context relevance.

![](https://docs.digitalocean.com/images/icons/gradient-ai-platform.svg)

How to Create an Evaluation Dataset on DigitalOcean Gradient™ AI Platform

Create effective evaluation datasets in CSV format to test your agent’s performance, improve accuracy, and measure qualities like factual correctness, safety, and instruction following.

![](https://docs.digitalocean.com/images/icons/gradient-ai-platform.svg)

How to View Agent Insights and Logs on DigitalOcean Gradient™ AI Platform

View insights and runtime logs for your agents to troubleshoot issues.

![](https://docs.digitalocean.com/images/icons/gradient-ai-platform.svg)

How to Trace Agent Responses on DigitalOcean Gradient™ AI Platform

Trace how your agent processes prompts to troubleshoot issues, improve performance, and control costs.

## Manage Knowledge Bases

![](https://docs.digitalocean.com/images/icons/gradient-ai-platform.svg)

Create and Manage Knowledge Bases

Create, edit, manage data sources, verify, and permanently destroy knowledge bases.

![](https://docs.digitalocean.com/images/icons/gradient-ai-platform.svg)

Attach and Detach Agent Knowledge Bases

Attach or detach a knowledge base from your agents.

## Manage Guardrails

![](https://docs.digitalocean.com/images/icons/gradient-ai-platform.svg)

Manage Agent Guardrails

Create, manage, edit, duplicate, or delete guardrails to control how your agents respond to sensitive or inappropriate content.

In this article...

[DigitalOcean Gradient™ AI Platform How-Tos](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/)

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