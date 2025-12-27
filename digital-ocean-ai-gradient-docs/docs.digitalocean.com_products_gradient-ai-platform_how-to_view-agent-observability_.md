---
url: "https://docs.digitalocean.com/products/gradient-ai-platform/how-to/view-agent-observability/"
title: "How to View Agent Insights and Logs on DigitalOcean Gradient™ AI Platform | DigitalOcean Documentation"
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
- View Agent Insights and Logs

[Give Feedback](https://ideas.digitalocean.com/documentation)

# How to View Agent Insights and Logs on DigitalOcean Gradient™ AI Platform

Validated on 30 Jun 2025 • Last edited on 10 Dec 2025

DigitalOcean Gradient™ AI Platform lets you build fully-managed AI agents with knowledge bases for retrieval-augmented generation, multi-agent routing, guardrails, and more, or use serverless inference to make direct requests to popular foundation models.

You can view performance insights and runtime logs for your agents to help you troubleshoot issues and understand how your agents are performing.

## View Agent Metrics

The Agent Metrics feature shows your agent’s token usage, traffic, and performance in real time. Use it to monitor efficiency, troubleshoot issues, and [adjust your agent’s configuration](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/test-agents/) as needed. Data may be delayed by up to 15 minutes.

To view metrics for an agent from the [DigitalOcean Control Panel](https://cloud.digitalocean.com/apps), click **Agent Platform** in the left menu. In the **Agent workspaces** tab, select the workspace that contains the agent you want to inspect. In the **Agents** tab, select the agent.

In the agent’s **Overview** page, go to the **Agent Metrics** section. Here, you can:

- View a **line graph of token usage over time**. Use the dropdown menu to choose one of the following:


  - **Tokens In**: Input tokens sent by users.
  - **Tokens Out**: Output tokens generated by the agent.
  - **Total Tokens**: All tokens combined.
  - **Requests In**: The number of user requests received.

You can also select the time range (for example, last 1 hour, last 14 days) to analyze short-term spikes or longer-term trends.

- Review **Token Metrics**, which provide the following performance details:
  - **Average end-to-end throughput**: The average number of tokens processed per second.
  - **Average end-to-end latency**: The average time it takes to deliver a complete response.
  - **Average time to first token**: The average time before the agent begins streaming the first token.

## View Agent Runtime Logs

Viewing agent runtime logs can help you understand how your agent is performing and troubleshoot issues. Runtime logs show the events that occur while your agent processes a prompt, such as which knowledge bases and functions were accessed to generate a response.

To view the runtime logs for an agent, go to the [DigitalOcean Control Panel](https://cloud.digitalocean.com/) and click **Agent Platform** in the left menu. In the **Agent workspaces** tab, select the workspace that contains the agent you want to view logs for and select the agent.

In the agent’s **Observability** tab, under the **Runtime Logs** section, you can view the agent runtime logs in real time.

## View Traces, Conversation Logs, and Insights

Traces, insights, and conversation logs work together to help you monitor agent behavior, troubleshoot issues, and improve performance. They give you visibility into how prompts are processed, how responses are generated, and how users interact with your agent:

- **Traces**: Provide a step-by-step timeline of each prompt with token usage, processing time, and resource access. If you enable trace storage, traces also include full inputs and outputs, giving you a detailed record of the conversation flow.
- **Insights**: Build on trace data by analyzing it with a third-party model to suggest improvements. They highlight ways to reduce latency, optimize token usage, and refine agent behavior for better results.
- **Conversation logs**: Capture every input and output across channels such as playground sessions and API calls. Reviewing these logs helps you see how the agent performs in real interactions and understand the user experience.

To view traces, conversation logs, and insights, go to the [control panel](https://cloud.digitalocean.com/) and click **Agent Platform** in the left menu. In the **Agent workspaces** tab, select the workspace that contains the agent and select the agent. In the agent’s **Observability** tab, go to the **Traces and conversation logs** section.

To view conversation logs, you need to enable trace storage. Click **Enable trace storage** to open the setup window. To also enable insights, check **Enable log stream insights** before finishing.

If you already enabled trace storage but not insights, in the **Traces and Insights** section click **Edit**, then under **Log stream insights**, click **Enable log stream insights** and close the window. By enabling insights, you consent to sending trace data to a third-party model. Insights incur additional costs. For details, see our [pricing page](https://docs.digitalocean.com/products/gradient-ai-platform/details/pricing/#insights).

After enabling trace storage, [send a few requests to your agent](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/test-agents/) to generate traces. Then, go to the **Traces and conversation logs** section of the **Observability** tab. Under **View your traces and conversation log stream**, click **View log stream**. The log stream opens in a new window where you can inspect sessions and prompt traces.

To access insights, on the top right of the **Sessions** page in the log stream window, click **Log stream insights**. If you already have insights, use the **Log Stream Insights** menu on the left to regenerate them. Insights may not generate if no new data is available since the last run.

To view messages, select a session to open the **Messages** screen and see the full conversation.

![Conversation log messages screen showing a message tree for an agent session, with a highlighted agent response and a metrics panel on the right.](https://docs.digitalocean.com/screenshots/gradient-ai-platform/traces-messages.dc84a1e3eb2c66a1a442879130ce6f53ba3587eb17421dcf88fdb7bb878e7c2c.png)

### Disable Traces, Conversation Logs, and Insights

To disable traces, conversation logs, or insights at any time, go to the [control panel](https://cloud.digitalocean.com/), click **Agent Platform** in the left menu, under the **Agent Workspaces** tab, select the workspace that contains the agent you want to disable traces or insights for. Select the agent, and then click the **Settings** tab. In the **Traces and Insights** section, click **Edit**. To stop storing traces and conversation logs, , click _Stop storing trace data_\*. to open the **Disable trace storage** window. Disabling trace storage also disables log stream insights. To confirm, type your agent’s name, and then click **Disable trace storage**.

To stop storing log stream insights, click **Disable log stream insights** to open the **Disable log stream insights** window. To confirm, type your agent’s name, and then click **Disable log stream insights**.

Disabling trace storage deletes all stored trace data, conversation logs, and insights for the agent, and stops collecting new trace and insights data. Disabling insights alone only stops the collection of new insights and does not stop trace storage or delete existing insights. Only disabling trace storage permanently deletes all associated data and cannot be undone.

In this article...

- [View Agent Metrics](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/view-agent-observability/#view-agent-metrics)
- [View Agent Runtime Logs](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/view-agent-observability/#view-agent-runtime-logs)
- [View Traces, Conversation Logs, and Insights](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/view-agent-observability/#conversation)
  - [Disable Traces, Conversation Logs, and Insights](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/view-agent-observability/#disable-traces-insights)

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

This site uses cookies and related technologies, as described in our [privacy policy](https://www.digitalocean.com/legal/privacy-policy/), for purposes that may include site operation, analytics, enhanced user experience, or advertising. You may choose to consent to our use of these technologies, or manage your own preferences. Please visit our [cookie policy](https://www.digitalocean.com/legal/cookie-policy) for more information.

Agree & ProceedDecline AllManage Choices

GenAI Agent - DigitalOcean

![DigitalOcean Docs Agent](https://product-docs.nyc3.cdn.digitaloceanspaces.com/ai-agent-icon.svg)