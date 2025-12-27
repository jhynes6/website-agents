---
url: "https://docs.digitalocean.com/products/gradient-ai-platform/how-to/test-agents/"
title: "How to Test Agents Using the Agent Playground on DigitalOcean Gradient™ AI Platform | DigitalOcean Documentation"
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
- Test Agents

[Give Feedback](https://ideas.digitalocean.com/documentation)

# How to Test Agents Using the Agent Playground on DigitalOcean Gradient™ AI Platform

Validated on 7 Nov 2025 • Last edited on 14 Nov 2025

DigitalOcean Gradient™ AI Platform lets you build fully-managed AI agents with knowledge bases for retrieval-augmented generation, multi-agent routing, guardrails, and more, or use serverless inference to make direct requests to popular foundation models.

The [Agent Playground](https://docs.digitalocean.com/products/gradient-ai-platform/details/features/) lets you test your agent’s performance, including how it uses [knowledge bases](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/attach-agent-knowledge-bases/) and [agent routing](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/route-agents/).

After [setting up your agent](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/create-agents/), you can adjust its agent instructions, foundation model settings, or RAG pipelines, to see how they affect agent responses. You can safely experiment with different settings and features, and then apply the new settings to the agent to optimize its performance.

If you want to trace your agent’s responses in the Agent Playground, see [Tracing Agent Responses](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/trace-agents/). All tokens used in the Agent Playground are charged at the same rate as tokens used in live agent interactions.

## Use Agent Playground in Control Panel

To open the Agent Playground, go to the [DigitalOcean Control Panel](https://cloud.digitalocean.com/), click **Agent Platform** in the left menu, then in the **Agent Workspaces** tab, select the workspace that contains the agent you want to test. From the workspace’s **Agents** tab, click the agent you want to test, and then click the **Playground** tab.

### Adjust Agent Instructions

In the **Agent Instructions** field, you can update the agent’s instructions. The agent’s instructions informs the agent about its purpose and the types of information it should and shouldn’t retrieve. You define an agent’s instructions during creation, but you can change them at any time. See our [instruction-writing best practices](https://docs.digitalocean.com/products/gradient-ai-platform/concepts/agent-instructions/) to learn how to write effective instructions.

### Configure Model Settings

In the **Settings** tab, you can configure the following model settings:

- **Max Tokens**: Defines the maximum output tokens a model processes. For model-specific details, see the [models](https://docs.digitalocean.com/products/gradient-ai-platform/details/models/) page.
Click to see example responses with different max token values.

For the prompt “What is the UN?”, here are responses with different max token values:




| Max tokens | Example response |
| --- | --- |
| 200 | The United Nations (UN) is an international organization that aims to promote peace, security, and cooperation among its member states. |
| 512 | The United Nations (UN) is an international organization that was established in 1945 to promote peace, security, and cooperation among its member states. The UN has 193 member states and is headquartered in New York City. Its goals include maintaining international peace and security, promoting sustainable development, protecting human rights, delivering humanitarian aid, and upholding international law. The UN is composed of several key bodies, including the General Assembly, the Security Council, the Economic and Social Council, the Secretariat, and the International Court of Justice. |

- **Temperature**: Controls the model’s creativity, specified as a number between 0 and 1. Lower values produce more predictable and conservative responses, while higher values encourage creativity and variation. Values are rounded to the nearest hundredth. For example, if you enter a value of `0.255`, the value is rounded to `0.26`.
Click to see example responses with different temperature values.

For the prompt “What color is the sky?”, here are example responses with different temperature values:




| Temperature | Example response |
| --- | --- |
| 0.0 | The sky is blue. |
| 0.5 | The sky is usually blue during the day, but it can appear different colors depending on weather conditions and time of day. |
| 0.7 | The sky’s color can vary widely. While it’s often perceived as blue, it can also appear pale blue, azure, cyan, or even take on hues of orange, pink, or purple during sunrise or sunset. Clouds, pollution, and atmospheric conditions can further influence its appearance. |
| 1.0 | Ah, the enigmatic canvas above! Some say it’s an endless ocean of cerulean, others a chameleon of hues. Perhaps it’s a mood ring for Mother Nature, shifting from the softest baby blue to the deepest indigo, with detours through fiery oranges and dreamy purples. Or maybe it’s just a figment of our collective imagination, a shared hallucination we call “sky.” What do you think it looks like right now? |

- **Top P**: Defines the cumulative probability threshold for word selection, specified as a number between 0 and 1. Higher values allow for more diverse outputs, while lower values ensure focused and coherent responses. Values are rounded to the nearest hundredth. For example, if you enter a value of `0.255`, the value is rounded to `0.26`.
Click to see example responses with different Top P values.

For the prompt “What color is the sky?”, here are example responses with different Top P values:




| Top P | Example response |
| --- | --- |
| 0.1 | The sky is blue. |
| 0.5 | The sky is typically blue, but it can change color depending on weather conditions and time of day. |
| 0.7 | The sky’s color varies widely. It’s often blue during clear days, but can appear gray when cloudy, and takes on beautiful hues of orange, pink, and purple during sunrise and sunset. Atmospheric conditions like pollution or dust can also affect its appearance. |
| 1.0 | The sky is a ever-changing tapestry of colors! While we often think of it as blue, it’s really a dynamic canvas that shifts throughout the day. From the soft pastels of dawn to the vibrant azure of noon, and the fiery spectacle of sunset, the sky never ceases to amaze. Sometimes it’s a moody gray, other times a crisp cerulean. And let’s not forget those rare treats like the ethereal green of the aurora borealis or the ominous green tint before a tornado. What’s your favorite sky color? |


### Configure Response Generation Settings

In the **Settings** tab, you can configure the following settings to refine how the agent processes a query and how it retrieves information for RAG:

- **Top K**: The number of most relevant documents or document chunks to retrieve from your knowledge base to provide context for your agent’s response. Higher values may result in higher response accuracy, but may also increase token counts and impact the agent model’s context window management.

- **Retrieval Method**: These options provide agents with additional guidance for retrieving information and generating responses.
  - **Rewrite**: The agent uses the current input and the prior context of the conversation to refine the user’s input and remove any ambiguity. The agent uses this to generate a shorter and more precise response. This method uses fewer tokens.
  - **Step Back**: The agent uses the current input and the prior context of the conversation to generate responses with a slightly broader scope than the original input, but the response remains focused on the overall topic. This method uses more tokens.
  - **Sub Queries**: The agent uses the current input and the prior context of the conversation to generate two to four succinct versions of the original input. It then uses the original input plus the new versions to broaden and improve search effectiveness and generate a response. This method uses more tokens than the rewrite and step-back methods.
  - **None**: The agent uses only the current input to retrieve information and doesn’t use any prior context. This method uses fewer tokens.
- **Include citations**: Checking this box adds a **Message Info** link at the end of each response sent in the agent playground. The **Message Info** link provides the token usage and the knowledge base data used to generate the response.


Adjust and evaluate the agent’s responses as necessary. Once you are satisfied that the model responses meet your criteria, click **Update Settings**. This opens a confirmation prompt. Type the agent’s name to confirm the changes, and then click **Confirm**. This updates the agent with the new settings. The agent redeploys with the new settings.

To revert any changes you’ve made to the agent, click **Reset to current settings**.

In this article...

- [Use Agent Playground in Control Panel](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/test-agents/#use-agent-playground-in-control-panel)
  - [Adjust Agent Instructions](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/test-agents/#agent-instructions)
  - [Configure Model Settings](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/test-agents/#model-settings)
  - [Configure Response Generation Settings](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/test-agents/#retrieval-settings)

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