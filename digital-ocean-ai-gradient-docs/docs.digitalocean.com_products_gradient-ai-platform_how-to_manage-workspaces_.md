---
url: "https://docs.digitalocean.com/products/gradient-ai-platform/how-to/manage-workspaces/"
title: "How to Create and Manage Workspaces on DigitalOcean Gradient™ AI Platform | DigitalOcean Documentation"
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
- Manage Workspaces

[Give Feedback](https://ideas.digitalocean.com/documentation)

# How to Create and Manage Workspaces on DigitalOcean Gradient™ AI Platform

Validated on 1 Jul 2025 • Last edited on 9 Dec 2025

DigitalOcean Gradient™ AI Platform lets you build fully-managed AI agents with knowledge bases for retrieval-augmented generation, multi-agent routing, guardrails, and more, or use serverless inference to make direct requests to popular foundation models.

Workspaces help you group related agents together under a single space. This makes it easier to manage agents, share them across your team, and run evaluations to test and compare their performance in a structured way.

All agents must reside in a workspace. You can add agents to an existing workspace upon creation, and move them between workspaces as needed. If you do not assign an agent to workspace upon creation, it is added to the default workspace.

Note
All agents created before the launch of the workspaces feature on 1 July 2025 have been automatically moved into a default workspace named `My Agent Workspace (Created by Default)`. You can [create additional workspaces](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/manage-workspaces/#create-a-workspace) at any time to reorganize or move your agents as needed.

Agents built and deployed using Agent Development Kit are also organized into workspaces labeled `Managed by ADK`. These workspaces group agent deployments by development environments, such as production, staging, or test. However, you cannot move agent deployments from one workspace to another. To use the agent in another workspace, you must redeploy it to that workspace with the environment defined.

## Create a Workspace

There are multiple ways to create a workspaces. You can create one:

- During the [agent creation workflow](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/create-agents/).
- From the **Agent Workspaces** tab in the [DigitalOcean Control Panel](https://cloud.digitalocean.com/).
- From the **Actions** menu button in the [DigitalOcean Control Panel](https://cloud.digitalocean.com/).

To create a workspace from the **Agent workspaces** tab, click the **Create workspace** button.

On the **Create a workspace** page, give the workspace a name and an optional description.

The **Move agents to workspace** section provides a list of existing agents associated with your [DigitalOcean team](https://docs.digitalocean.com/platform/teams/). To move agents into the new workspace, click the checkbox beside the agents you want to add. You can use the search bar to filter the list for specific agents.

Once you’ve selected the agents you want to add to the workspace, click **Create Workspace**. This creates the workspace and adds it to your **Workspaces** tab.

## Move Agents Between Workspaces

You can move agents between workspaces at anytime.

To move agents between workspaces in the [DigitalOcean Control Panel](https://cloud.digitalocean.com/), click **Agent Platform** in the left menu, then in the **Agent Workspaces** tab, select the workspace you want to move agents either to or from. From the workspace’s **Agents** tab, click the **Action** button, and then select **Manage agents** from the drop-down menu.

From the **Move agents** page, select **Move to another workspace** to move agents from the selected workspace to another workspace on your team, or select **Move to this workspace** to move agents from other workspaces to the selected workspace.

If you selected the **Move to another workspace** option, select the workspace you want to move agents to from the **Select a workspace** drop-down menu.

Next, select the agents you want to move by clicking the checkboxes beside them. You can use the search bar to filter the list for specific agents.

Once you’ve selected the agent you want to move, click **Move agents**. The agents are moved to the desired workspace.

## Destroy a Workspace

Destroying a workspace permanently and irreversibly destroys the workspace. Before you can destroy a workspace, you must either move or [destroy](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/destroy-agents/) any remaining agents in the workspace.

To destroy a workspace from the [DigitalOcean Control Panel](https://cloud.digitalocean.com/), click **Agent Platform** in the left menu, then in the **Agent Workspaces** tab, select the workspace that you want to destroy. From the workspace’s overview page, select the **Settings** tab.

From the **Settings** tab, click **Destroy**. A prompt asks you to confirm the deletion by entering the name of the workspace. After entering the name of the workspace, click **Destroy**. The workspace is remove from your team.

In this article...

- [Create a Workspace](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/manage-workspaces/#create-a-workspace)
- [Move Agents Between Workspaces](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/manage-workspaces/#move-agents-between-workspaces)
- [Destroy a Workspace](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/manage-workspaces/#destroy-a-workspace)

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