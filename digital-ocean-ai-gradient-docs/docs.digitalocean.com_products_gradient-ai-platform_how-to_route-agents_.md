---
url: "https://docs.digitalocean.com/products/gradient-ai-platform/how-to/route-agents/"
title: "How to Route to Multiple Agents on DigitalOcean Gradient™ AI Platform | DigitalOcean Documentation"
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
- Route to Multiple Agents

[Give Feedback](https://ideas.digitalocean.com/documentation)

# How to Route to Multiple Agents on DigitalOcean Gradient™ AI Platform

Validated on 26 Jun 2025 • Last edited on 22 Dec 2025

DigitalOcean Gradient™ AI Platform lets you build fully-managed AI agents with knowledge bases for retrieval-augmented generation, multi-agent routing, guardrails, and more, or use serverless inference to make direct requests to popular foundation models.

Agent routing is the ability to reference other agents from the instruction of an agent. Different agents may be trained or optimized for specific tasks or have different domain expertise to handle different types of requests. Agent routing lets you unify multiple agents.

For example, you can have a _parent_ travel agent that comprises of four independent _child_ agents that work in conjunction. The top level general foundation model handles the pleasantries and routes user requests to the more specific trip planner, site help agent, and booking agent models. Suppose these agents are called `Trip Planner`, `Site Help`, `Flight Booking`, and `Hotel Booking`, respectively. The foundation models of each agent can be of different kind, meaning that the chat bot can integrate with other kinds of generative models such as a diffusion model to generate pictures.

We charge for tokens used by parent agents to determine whether the user questions need to be routed to a child agent and agents that answer user questions, which can be a parent agent or a child agent to which the question gets routed.

## Add an Agent Route Using Automation

To add an agent route using the DigitalOcean API, you need the unique identifiers of the parent agent and one or more child agents that the parent agent routes to. To get a list of agents with their unique identifiers, use the [`/v2/gen-ai/agents}` endpoint](https://docs.digitalocean.com/reference/api/digitalocean/#operation/genai_list_agents).

You also need to provide a name of the agent route and rules that to determine how to direct different inputs to the appropriate child agent. To view agent routes for the parent agent, use the [`/v2/gen-ai/agents/{uuid}/child_agents` endpoint](https://docs.digitalocean.com/reference/api/digitalocean/#operation/genai_get_agent_children).

How to Add an Agent Route Using the DigitalOcean API

1. [Create a personal access token](https://docs.digitalocean.com/reference/api/create-personal-access-token/) and save it for use with the API.
2. Send a POST request to [`https://api.digitalocean.com/v2/gen-ai/agents/{parent_agent_uuid}/child_agents/{child_agent_uuid}`](https://docs.digitalocean.com/reference/api/digitalocean//#operation/genai_attach_agent).

### cURL

Using cURL:

```shell
curl -X POST \
  -H "Content-Type: application/json"  \
  -H "Authorization: Bearer $DIGITALOCEAN_TOKEN" \
  "https://api.digitalocean.com/v2/gen-ai/agents/1b418231-b7d6-11ef-bf8f-4e013e2ddde4/child_agents/6a09d603-b68d-11ef-bf8f-4e013e2ddde4" \
  -d '{
    "parent_agent_uuid": "1b418231-b7d6-11ef-bf8f-4e013e2ddde4",
    "child_agent_uuid": "6a09d603-b68d-11ef-bf8f-4e013e2ddde4",
    "route_name": "route-token-stat",
    "if_case": "for any token related statistics, use this route"
  }'

```

## Add an Agent Route Using the Control Panel

To add agent routes to an agent from the [DigitalOcean Control Panel](https://cloud.digitalocean.com/), click **Agent Platform** in the left menu, then in the **Agent Workspaces** tab, select the workspace that contains the agent you want to add agent routing for. From the workspace’s **Agents** tab, click the agent, and then click its **Resources** tab.

In its **Resources** tab, scroll to the **Agent Routes** section and click **Add Agent Route**. In the **Add Agent Route** window, specify the following information:

- **Route name**: Name of the agent route. For example, `travel agent routes`.

- **Route instructions**: These instructions map your input types or attributes to the right agent which has the expertise for that input attribute. Create a set of rules that determine how different inputs are directed to the appropriate agent.
Click to expand an example of route instructions.

For the travel agent example, the following are some route instructions:



- **If**`input is to plan a trip`, select the **Trip Planner** agent from the **Route to** drop-down list.
- **If**`input is a question about the travel website`, select the **Site Help** agent from the **Route to** drop-down list.
- **If**`input is about booking a flight`, select the **Flight Booking** agent from the **Route to** drop-down list.
- **If**`input is about booking a hotel`, select the **Hotel Booking** agent from the **Route to** drop-down list.

Click **Save** to save the agent route. The agent route is displayed in the **AGENT ROUTES** table in the **Resources** tab.

In this article...

- [Add an Agent Route Using Automation](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/route-agents/#add-an-agent-route-using-automation)
- [Add an Agent Route Using the Control Panel](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/route-agents/#add-an-agent-route-using-the-control-panel)

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