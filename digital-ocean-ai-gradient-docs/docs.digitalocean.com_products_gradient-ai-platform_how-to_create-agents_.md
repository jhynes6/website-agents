---
url: "https://docs.digitalocean.com/products/gradient-ai-platform/how-to/create-agents/"
title: "How to Create Agents on DigitalOcean Gradient™ AI Platform | DigitalOcean Documentation"
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
- Create Agents

[Give Feedback](https://ideas.digitalocean.com/documentation)

# How to Create Agents on DigitalOcean Gradient™ AI Platform

Validated on 28 Aug 2025 • Last edited on 22 Dec 2025

DigitalOcean Gradient™ AI Platform lets you build fully-managed AI agents with knowledge bases for retrieval-augmented generation, multi-agent routing, guardrails, and more, or use serverless inference to make direct requests to popular foundation models.

You can create agents using the DigitalOcean [API or CLI](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/create-agents/#create-an-agent-using-automation), [control panel](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/create-agents/#create-an-agent-using-the-control-panel), or [Agent Development Kit](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/build-agents-using-adk/).

## Create an Agent Using Automation

To create an agent with the DigitalOcean API or CLI, provide a name, a [foundation model](https://docs.digitalocean.com/products/gradient-ai-platform/details/models/#foundation-models), [instructions](https://docs.digitalocean.com/products/gradient-ai-platform/concepts/agent-instructions/), the project identifier, and the datacenter region. We strongly recommend adding a [knowledge base](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/create-manage-agent-knowledge-bases/) so your agent can ground its responses in your own domain data, reducing hallucinations and improving accuracy.

You can use the API or CLI to get available options for these parameters:

- To list available models and their identifiers, use the [`/v2/gen-ai/models` endpoint](https://docs.digitalocean.com/reference/api/digitalocean/#operation/genai_list_models) or the [`doctl genai list-models`](https://docs.digitalocean.com/reference/doctl/reference/genai/list-models/) command.

The first time you use a model from a provider, you must accept the provider’s terms in the [DigitalOcean Control Panel](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/create-agents/#create-an-agent-using-the-control-panel).

- To view available datacenters, use the [`/v2/gen-ai/regions` endpoint](https://docs.digitalocean.com/reference/api/digitalocean/#operation/genai_list_regions) or the [`doctl genai list-regions`](https://docs.digitalocean.com/reference/doctl/reference/genai/list-regions/) command.

- To list (or create) knowledge bases, use the [`/v2/gen-ai/knowledge_bases` endpoint](https://docs.digitalocean.com/reference/api/digitalocean/#operation/genai_list_knowledge_base) or the [`doctl genai knowledge-base create`](https://docs.digitalocean.com/reference/doctl/reference/genai/knowledge-base/create/) command.


How to Create an Agent Using the DigitalOcean CLI

1. [Install `doctl`](https://docs.digitalocean.com/reference/doctl/how-to/install/), the official DigitalOcean CLI.
2. [Create a personal access token](https://docs.digitalocean.com/reference/api/create-personal-access-token/) and save it for use with `doctl`.
3. Use the token to grant `doctl` access to your DigitalOcean account.




```shell
doctl auth init
```

4. Finally, run `doctl genai agent create`. Basic usage looks like this, but you can [read the usage docs](https://docs.digitalocean.com/reference/doctl/reference/genai/agent/create/) for more details:




```shell
doctl genai agent create <agent-name>... [flags]
```



The following example creates an agent:




```shell
doctl genai agent create --name "My Agent" --project-id "12345678-1234-1234-1234-123456789012" --model-id "12345678-1234-1234-1234-123456789013" --region "tor1" --instruction "You are an agent who thinks deeply about the world"
```


How to Create an Agent Using the DigitalOcean API

1. [Create a personal access token](https://docs.digitalocean.com/reference/api/create-personal-access-token/) and save it for use with the API.
2. Send a POST request to [`https://api.digitalocean.com/v2/gen-ai/agents`](https://docs.digitalocean.com/reference/api/digitalocean//#operation/genai_create_agent).

### cURL

Using cURL:

```shell
curl -X POST \
    -H "Content-Type: application/json"  \
    -H "Authorization: Bearer $DIGITALOCEAN_TOKEN" \
    "https://api.digitalocean.com/v2/gen-ai/agents" \
    -d '{
      "name": "api-create",
      "model_uuid": "95ea6652-75ed-11ef-bf8f-4e013e2ddde4",
      "instruction": "be a weather reporter",
      "description": "weather-agent",
      "project_id": "37455431-84bd-4fa2-94cf-e8486f8f8c5e",
      "tags": [\
        "tag1"\
      ],
      "region": "tor1",
      "knowledge_base_uuid": [\
        "9758a232-b351-11ef-bf8f-4e013e2ddde4"\
      ]
    }'
```

## Create an Agent Using the Control Panel

To create an agent from the [DigitalOcean Control Panel](https://cloud.digitalocean.com/), in the left menu, click **Agent Platform** to go to the **Agent Workspaces** tab. Click the workspace where you want to create an agent to go to that workspace’s **Agents** tab. Finally, click **Create Agent** to open the **Create an agent** page, where you can choose a custom configuration or a template.

### Give Your Agent a Name

Choose a descriptive name in the **Agent name** field that reflects the agent’s role or expertise.

### Choose a Configuration

Choose a custom configuration to define the agent’s objective, model, and settings, or choose a template with predefined instructions and a default model. You can add a knowledge base with either option.

Custom Configuration

### Define Agent Instructions

Provide clear instructions that define your agent’s identity, objectives, expertise, and boundaries. These instructions help the agent understand what role it plays, what tasks it should prioritize, and which resources it can use.

> You are a travel agent. You help find airline tickets and car rentals, compare prices, schedules, and find the best deals.
>
> You also suggest hotel, resort, or vacation rentals that cost less than $5000 for a week.
>
> Make sure that the recommendations you make are clear, actionable, and customized to the financial situation.

See [Write Effective Agent Instructions](https://docs.digitalocean.com/products/gradient-ai-platform/concepts/agent-instructions/) for best practices. You can also use the [agent instruction templates](https://docs.digitalocean.com/products/gradient-ai-platform/concepts/agent-instructions/#copyable-templates) as-is or adapt them to your needs.

### Select a Model

Agent use foundation models to interpret prompts and generate responses.

Select a [foundation model](https://docs.digitalocean.com/products/gradient-ai-platform/details/models/#foundation-models) from the **Select a model** drop-down list. To test models before choosing, use the [Model Playground](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/configure-models/) by clicking **Model Playground**.

If you use a commercial model like [Anthropic Claude](https://www.anthropic.com/claude), you must bring your own API key. We bill usage [directly to your model account](https://docs.digitalocean.com/products/gradient-ai-platform/details/pricing/#model). If your team already has keys, choose one from the **Select or add an API key** drop-down list, or [add a new key](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/create-agents/#add-api-key).

You can change the foundation model at any time after creating the agent.

### Add API Key

From your Anthropic account, [copy your API key](https://docs.anthropic.com/en/api/admin-api/apikeys/get-api-key). In the **Add Anthropic API Key** window, under the **Anthropic API Key** section, paste the key.

Under **Key Name**, type a unique name without using the key itself. Names can include lowercase letters, numbers, hyphens, and periods.

Check **I agree to the Anthropic Terms** to confirm agreement, and then click **Verify and Save** to validate the API key.

After verification, under the **Select or add an API key** section, in the drop-down list, we automatically select the API key.

In the **Model Keys** page, you [can view, add, edit, or delete model keys](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/manage-model-provider-keys/). For more details on foundation models, see our [models page](https://docs.digitalocean.com/products/gradient-ai-platform/details/models/).

Agent Template

### Select a Template

From the **Agent templates** tab, select one of the following templates:

- **Customer Support Agent**: This template creates an agent configured to answer product questions and help users troubleshoot issues.
- **Business Analytics Agent**: This template creates an agent configured to analyze data and generate insights.

The template automatically sets the model and guardrails.

### Choose a Workspace

Workspaces group related agents together under a single space to help you organize your AI agents, share them across your team, and run evaluations to test and compare their performance in a structured way. Every agent you create exists in a workspace. By default, you have one workspace called **My Agent Workspace (Created by Default)**.

In the **Where should your agent live?** section, choose a [workspace](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/manage-workspaces/) for your agent. You can select an existing workspace by clicking **Use Existing** and choosing one from the drop-down list, or create a new workspace by clicking **Create New** and providing the new workspace a name and description.

### Add Knowledge Bases

A knowledge base is a mixture of unstructured text files in Spaces buckets and web pages. Knowledge bases provide context to the prompt for your agent’s foundation model. Your agent uses knowledge bases to augment prompts to the foundation model, answer questions, and analyze documents. Examples of knowledge bases include product documentation, pricing, and product catalogs.

We strongly recommend adding one or more [knowledge bases](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/create-manage-agent-knowledge-bases/) when creating your agent to ground its responses in your data and improve accuracy, either by selecting an existing one from the **Knowledge Bases** drop-down list or creating a new one.

To keep your knowledge base up to date automatically, you can also [enable auto-indexing](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/create-manage-agent-knowledge-bases/#auto-index-data-source-control-panel).

### Finalize and Create

By default, the new agent belongs to your default project. You can choose a different project from the **Select a project** drop-down list.

Optionally, you can tags your agents. Tags organize related resources. Tags must be single words with letters, numbers, colons, dashes, or underscores.

At the bottom of this section, review the chosen agent resources and [model token rate](https://docs.digitalocean.com/products/gradient-ai-platform/details/pricing/#open-source-models-agent-usage).

Click **Create Agent** to complete creating the agent. Your agent appears in the **Projects** section of the control panel’s main menu.

## Next Steps

After creating your agent, you can:

- [Route tasks across multiple agents](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/route-agents/).
- [Call functions in your agent](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/route-agent-functions/).
- [Test the agent in the Agent Playground](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/test-agents/).
- [Use the agent](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/use-agents/) in a chatbot or application.

In this article...

- [Create an Agent Using Automation](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/create-agents/#create-an-agent-using-automation)
- [Create an Agent Using the Control Panel](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/create-agents/#create-an-agent-using-the-control-panel)
  - [Give Your Agent a Name](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/create-agents/#give-your-agent-a-name)
  - [Choose a Configuration](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/create-agents/#choose-a-configuration)
  - [Choose a Workspace](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/create-agents/#choose-a-workspace)
  - [Add Knowledge Bases](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/create-agents/#add-knowledge-bases)
  - [Finalize and Create](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/create-agents/#finalize-and-create)
- [Next Steps](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/create-agents/#next-steps)

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