---
url: "https://docs.digitalocean.com/products/gradient-ai-platform/how-to/trace-agents/"
title: "How to Trace Agent Responses on DigitalOcean Gradient™ AI Platform | DigitalOcean Documentation"
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

- [How-Tos](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/)
- Trace Agent Responses

[Give Feedback](https://ideas.digitalocean.com/documentation)

# How to Trace Agent Responses on DigitalOcean Gradient™ AI Platform

Validated on 30 Jun 2025 • Last edited on 10 Dec 2025

DigitalOcean Gradient™ AI Platform lets you build fully-managed AI agents with knowledge bases for retrieval-augmented generation, multi-agent routing, guardrails, and more, or use serverless inference to make direct requests to popular foundation models.

Agent Tracing shows a step-by-step timeline of how your agent processes each prompt, from receiving the input to generating the final response. Each trace includes: token usage, processing times, session and trace IDs, and accessed resources such as knowledge bases, agent routing, and functions.

## Enable Trace Storage

Before you can view traces, you must enable trace storage for your agent. This allows you to save traces and conversation logs for later review.

To enable trace storage, go to the [DigitalOcean Control Panel](https://cloud.digitalocean.com/), in the left menu, click **Agent Platform**, click the **Agent Workspaces** tab, and then select the workspace that contains the agent you want to enable traces for.

From the workspace’s **Agents** tab, select the agent, click the **Observability** tab, find the **Traces and conversation logs** section, and then click **Enable trace storage** to enable trace storage. You can disable trace storage at any time, but disabling it deletes all stored traces and conversation logs for your agent.

Once you’ve enabled trace storage and your agent has received some requests, you can view the traces.

## View Traces

You can access traces from the [Agent Playground](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/test-agents/#use-agent-playground-in-control-panel) or from the agent’s **Observability** tab.

Click **View log stream** to open the log stream window where you can view traces at three levels of granularity:

- **Sessions** display the complete set of interactions (traces) with your agent, including all prompts and responses within a single session.
- **Traces** display individual actions (spans) taken during an interaction, including the prompt, response, and all processing steps.
- **Spans** display information about the individual action taken by the agent, such as a tool call, knowledge base retrieval, or function execution.

You can list traces by individual sessions, traces, or spans by clicking their respective tabs. The default view is **Sessions**, which shows a list of all sessions for the agent.

To open a session, click on the **Sessions** tab and then click a session from the list. This opens a diagram view of the session’s first trace. The diagram shows the input, document retrievals, tool calls, and the final output. You can click on any of the nodes to see more details about that step in the trace.

![Traces overview page showing a trace flow, with the right panel displaying Document Search details including raw text input and retrieved chunks.](https://docs.digitalocean.com/screenshots/gradient-ai-platform/traces-overview.b34e73db2797df974a4a4d3a14eee3fcb24bd695867e9f186b108f30db7ef09d.png)

You can then page through the session’s traces by clicking the left and right arrows at the top of the diagram.

### Latency and Messages Views

The **Latency** and **Messages** tabs provide additional insights into the agent’s performance.

To view the latency for each step in the session, click the **Latency** tab. This shows a timeline of the session’s processing times. You can click on individual nodes in the timeline to see more details about that step. This can help you identify bottlenecks or delays in the agent’s processing.

![Latency view of a conversation log messages showing timing bars, the agent, and guardrail steps, with the right panel displaying LLM parameters.](https://docs.digitalocean.com/screenshots/gradient-ai-platform/traces-latency.93a502ede2dcf59c56d7c4b28152a2102c9bd87c94fc95e78308c57976b76ebe.png)

The **Messages** tab shows a conversation log and a waterfall chart of all the traces for that session. You can click on any of the traces or spans to see the details about it, including IDs, timestamps, and processing times. This view is useful for quickly scanning through the session’s interactions.

![Conversation log messages screen showing a message tree for an agent session, with a highlighted agent response and a metrics panel on the right.](https://docs.digitalocean.com/screenshots/gradient-ai-platform/traces-messages.dc84a1e3eb2c66a1a442879130ce6f53ba3587eb17421dcf88fdb7bb878e7c2c.png)

## Export Traces

Exporting session and tracing logs lets you download session or trace data as a `.csv` file for offline analysis or archiving.

To begin exporting data, go to the [DigitalOcean Control Panel](https://cloud.digitalocean.com/), in the left menu, click **Agent Platform**, then in **Agent Workspaces**, select the workspace that contains your agent. From the workspace’s **Agents** tab, select the agent, then click the **Observability** tab and scroll to the **Traces and conversation logs** section.

In the log stream window, switch to either the **Sessions** or **Traces** tab, select the interactions you want to export using the checkboxes, then click **Export** to open the **Export Data** window.

In the export window, choose the columns you want to include. You can click **All**, **None**, or **Visible Columns** (the default set), or manually select individual columns using the checkboxes.

After selecting your columns, choose a file name or leave the field blank to use the autogenerated name. Then, click **Export** to download the `.csv` file to your local machine.

In this article...

- [Enable Trace Storage](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/trace-agents/#enable-trace-storage)
- [View Traces](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/trace-agents/#view-traces)
  - [Latency and Messages Views](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/trace-agents/#latency-and-messages-views)
- [Export Traces](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/trace-agents/#export-traces)

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