---
url: "https://docs.digitalocean.com/products/gradient-ai-platform/concepts/prompts/"
title: "Prompt Writing Best Practices for DigitalOcean Gradient™ AI Platform | DigitalOcean Documentation"
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
- Prompt Writing Best Practices

[Give Feedback](https://ideas.digitalocean.com/documentation)

# Prompt Writing Best Practices for DigitalOcean Gradient™ AI Platform

Validated on 6 Mar 2025 • Last edited on 15 Aug 2025

DigitalOcean Gradient™ AI Platform lets you build fully-managed AI agents with knowledge bases for retrieval-augmented generation, multi-agent routing, guardrails, and more, or use serverless inference to make direct requests to popular foundation models.

Effective prompts guide your agent to accurate, relevant responses by ensuring specificity, context, and intent, similar to asking well-structured questions to a support team.

When [testing your agent](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/test-agents/), well-designed prompts identify training gaps, refine responses, and improve accuracy and consistency, enhancing the user experience.

## Maintain a Neutral Tone

When writing prompts for your agent, maintain a neutral tone and avoid sarcasm or figurative language. Sarcasm or figurative language may confuse the agent, leading to literal but unhelpful responses. A neutral tone ensures concise, balanced, and unbiased answers.

Maintain neutrality by:

- Using direct, straightforward language.
- Replacing figurative expressions (for example, metaphors, idioms, sarcasm) with literal statements.
- Avoiding emotional language or biased terms.

| Prefer | Avoid |
| --- | --- |
| > Summarize the key points of the generative AI article accurately. | > Can you summarize the main points of this article about generative AI? |

## Ask Intentional Questions

When asking your agent questions, make them explicit, concise, and tailored to your needs. Avoid vague or broad phrasing to ensure accurate and actionable responses.

Ask intentional questions by:

- Providing clear context for the agent to focus.
- Including desired outcomes or format, like a code snippet, step-by-step instructions, list, or paragraph.
- Indicating the level of detail needed, such as a brief overview or detailed explanation.
- Adding relevant background information for context.

| Prefer | Avoid |
| --- | --- |
| > Explain how I can improve the accuracy of my model, specifically through hyperparameter tuning? | > Can you explain how I can improve the accuracy of my model? |

## Limit Prompts to One Question

When writing prompts, ask one question at a time and avoid combining multiple questions in a single prompt.

Compound questions can confuse the agent, leading to incomplete or skipped answers. Simple, focused prompts ensure direct and relevant responses.

| Prefer | Avoid |
| --- | --- |
| > What is RAG?" After receiving the answer, follow up with, “How is RAG useful? | > Can you explain what RAG is, and also tell me how it is useful? |

## Separate Complex Prompts

If your prompt is complex, divide it into smaller questions to guide your agent effectively toward the desired answer.

Separating complex prompts ensures specific, accurate, and complete responses while avoiding vague or partial answers. It also helps address each part of your query systematically.

Separate complex prompts by:

1. Identifying the components of the prompt and creating smaller, focused questions for each.
2. Starting with foundational questions to gather background information before addressing the main topic.
3. Using a step-by-step approach to cover different aspects of the query and combining the answers for a complete response.

| Prefer | Avoid |
| --- | --- |
| 1. > How do I create a model for text generation?<br>   <br>2. > How do I train a model for text generation?<br>   <br>3. > How do I evaluate the performance of a model for text generation? | > How do I create, train, and evaluate a model for text generation? |

## Add Examples or Screenshots

When writing prompts, add examples or screenshots if the question alone might confuse the agent.

Examples or screenshots provide context, clarify your query, and help the agent understand the situation or desired outcome.

Use examples or screenshots to improve prompts by:

- Showing the response you want with an example or screenshot.
- Highlighting incorrect outcomes to help the agent avoid them.
- Including step-by-step examples or screenshots to illustrate issues, such as an error in a script.
- Demonstrating how specific inputs should produce specific outputs.

| Prefer | Avoid |
| --- | --- |
| > I tried running a Python script (see the attached screenshot), but I keep getting a ‘TypeError: unsupported operand type(s)’. Could you help identify the cause of this error? | > I tried running a Python script, but I keep getting a type error. |

In this article...

- [Maintain a Neutral Tone](https://docs.digitalocean.com/products/gradient-ai-platform/concepts/prompts/#maintain-a-neutral-tone)
- [Ask Intentional Questions](https://docs.digitalocean.com/products/gradient-ai-platform/concepts/prompts/#ask-intentional-questions)
- [Limit Prompts to One Question](https://docs.digitalocean.com/products/gradient-ai-platform/concepts/prompts/#limit-prompts-to-one-question)
- [Separate Complex Prompts](https://docs.digitalocean.com/products/gradient-ai-platform/concepts/prompts/#separate-complex-prompts)
- [Add Examples or Screenshots](https://docs.digitalocean.com/products/gradient-ai-platform/concepts/prompts/#add-examples-or-screenshots)

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