---
url: "https://docs.digitalocean.com/products/gradient-ai-platform/reference/agent-tracing-metrics/"
title: "Agent Tracing Data | DigitalOcean Documentation"
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
- Agent Tracing Data

[Give Feedback](https://ideas.digitalocean.com/documentation)

# Agent Tracing Data

Validated on 2 Jul 2025 • Last edited on 15 Aug 2025

DigitalOcean Gradient™ AI Platform lets you build fully-managed AI agents with knowledge bases for retrieval-augmented generation, multi-agent routing, guardrails, and more, or use serverless inference to make direct requests to popular foundation models.

[Agent tracing](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/trace-agents/) captures detailed data for every interaction your agent receives. With this data, you can debug errors, monitor latency, track token usage, and understand the choices your agent makes as it builds a response.

This reference explains every field you see when you inspect traces, either in real time from the **Message Info** panel in Agent Playground or later in the **Observability** log stream.

## Agent Playground Metadata

Even without trace storage, you view the current trace in Agent Playground by clicking **Message Info** after you send a prompt. The panel shows token usage, latency, retrieved content, and other key metrics.

Each message shows **Summary Metrics** in **Message Info**. These metrics fall into two groups: **Processing Time** and **Token Usage**.

### Processing Time

- **Time submitted:** when the agent receives the prompt.
- **Time returned:** when the agent finishes generating the response.
- **Time to first token (TTFT):** how long the agent waits before streaming the first token.
- **Processing time:** total time from submission to completion.

Use these values to track performance and isolate latency spikes.

### Token Usage

- **Prompt tokens:** number of tokens in the user input.
- **Response tokens:** number of tokens in the agent’s reply.
- **Total tokens:** combined input-plus-output count.

These counts help you watch token-related costs and efficiency.

### Input

The **input** field shows the exact prompt your user sends. For example:

> “What’s the weather like in Austin tomorrow?”

### Output

The **output** field shows the full response your agent returns. For example:

> “Tomorrow in Austin will be mostly sunny with a high of 95 F.”

### Knowledge-Base Retrieval

If the agent retrieves information from a knowledge base, the trace records:

- **Knowledge base name:** the knowledge base in use.
- **File name:** the data-source file that supplies context.
- **Retrieved context:** the text snippets the agent uses in its reply.

These details confirm what documents the agent is referencing to help generate its response.

### Guardrail Triggers

If a safety guardrail fires, the trace lists:

- **Guardrail name:** the guardrail that triggers (for example, Jailbreak Detection).
- **Reason triggered:** why the guardrail activates, such as an unsafe prompt or instruction override.

You can use these fields to verify that safety policies work as intended.

## Trace Metadata

To view full trace metadata, [open the log stream](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/trace-agents/) from the agent’s **Observability** tab. The log stream opens in a separate window and shows stored sessions and traces in detail.

Each saved trace includes:

- **Timestamp:** when the platform receives and processes the request.
- **Session ID:** the unique ID for the conversation session.
- **Trace ID:** the unique ID for this trace.
- **Status code:** the HTTP status code the request received. `200` indicates success.
- **Tool call ID:** the ID of any tool call the trace makes.
- **Has children:** whether the trace spawns sub-calls (for example, a guardrail action).

In this article...

- [Agent Playground Metadata](https://docs.digitalocean.com/products/gradient-ai-platform/reference/agent-tracing-metrics/#agent-playground-metadata)
  - [Processing Time](https://docs.digitalocean.com/products/gradient-ai-platform/reference/agent-tracing-metrics/#processing-time)
  - [Token Usage](https://docs.digitalocean.com/products/gradient-ai-platform/reference/agent-tracing-metrics/#token-usage)
  - [Input](https://docs.digitalocean.com/products/gradient-ai-platform/reference/agent-tracing-metrics/#input)
  - [Output](https://docs.digitalocean.com/products/gradient-ai-platform/reference/agent-tracing-metrics/#output)
  - [Knowledge-Base Retrieval](https://docs.digitalocean.com/products/gradient-ai-platform/reference/agent-tracing-metrics/#knowledge-base-retrieval)
  - [Guardrail Triggers](https://docs.digitalocean.com/products/gradient-ai-platform/reference/agent-tracing-metrics/#guardrail-triggers)
- [Trace Metadata](https://docs.digitalocean.com/products/gradient-ai-platform/reference/agent-tracing-metrics/#trace-metadata)

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