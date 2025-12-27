---
url: "https://docs.digitalocean.com/products/gradient-ai-platform/how-to/use-serverless-inference/"
title: "How to Use Serverless Inference on DigitalOcean Gradient™ AI Platform | DigitalOcean Documentation"
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
- Use Serverless Inference

[Give Feedback](https://ideas.digitalocean.com/documentation)

# How to Use Serverless Inference on DigitalOcean Gradient™ AI Platform

Validated on 12 Aug 2025 • Last edited on 9 Dec 2025

DigitalOcean Gradient™ AI Platform lets you build fully-managed AI agents with knowledge bases for retrieval-augmented generation, multi-agent routing, guardrails, and more, or use serverless inference to make direct requests to popular foundation models.

Serverless inference lets you send API requests directly to foundation models without creating or managing an AI agent. This generates responses without any initial instructions or configuration to the model.

To use serverless inference, send a conventional HTTP request to any of the serverless inference API endpoints. You need to authenticate with a [model access key](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/use-serverless-inference/#keys), which you can create and manage in the DigitalOcean Control Panel.

Tip
You can also use the model keys you create for serverless inference for the model nodes to [build and deploy agents using the Agent Development Kit](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/build-agents-using-adk/).

All requests are [billed per input and output token](https://docs.digitalocean.com/products/gradient-ai-platform/details/pricing/).

## Serverless Inference API Endpoints

The serverless inference API is available at `https://inference.do-ai.run` and has the following endpoints:

| Endpoint | Verb | Description |
| --- | --- | --- |
| `/v1/models` | GET | Returns a list of available models and their IDs. |
| `/v1/chat/completions` | POST | Sends chat-style prompts and returns model responses. |

### /v1/models

To retrieve available models, send a GET request to `/models` using your model access key. For example, using `curl`:

```bash
curl -X GET https://inference.do-ai.run/v1/models \
  -H "Authorization: Bearer $MODEL_ACCESS_KEY" \
  -H "Content-Type: application/json"
```

This returns a list of available models with their corresponding model IDs (`id`).

### /v1/chat/completions

To send a prompt to a model, send a POST request to `/v1/chat/completions`. The request body must include:

- `model`: The model ID of the model you want to use. Get the model ID using `/v1/models` or on the [available models page](https://docs.digitalocean.com/products/gradient-ai-platform/details/models/).

- `messages`: The input prompt or conversation history. Serverless inference does not have sessions, so include all relevant context using this field.

- `temperature`: A value between `0.0` and `1.0` to control randomness and creativity.

- `max_tokens`: The maximum number of tokens to generate in the response. Use this to manage output length and cost.


The following example request sends a prompt to the specified model (Llama 3.3 Instruct-70B) with the prompt “What is the capital of France?”, a temperature of 0.7, and max tokens set to 50.

```bash
curl https://inference.do-ai.run/v1/chat/completions \
  -H "Authorization: Bearer $MODEL_ACCESS_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.3-70b-instruct",
    "messages": [{"role": "user", "content": "What is the capital of France?"}],
    "temperature": 0.7,
    "max_tokens": 50
  }'
```

The response includes the generated text and token usage details:

```json
{
  "choices": [\
    {\
      "finish_reason": "stop",\
      "index": 0,\
      "logprobs": null,\
      "message": {\
        "audio": null,\
        "content": "The capital of France is Paris.",\
        "refusal": null,\
        "role": ""\
      }\
    }\
  ],
  "created": 1747247763,
  "id": "",
  "model": "llama3.3-70b-instruct",
  "object": "chat.completion",
  "service_tier": null,
  "usage": {
    "completion_tokens": 8,
    "prompt_tokens": 43,
    "total_tokens": 51
  }
}
```

Alternatively, you can call serverless inference from your automation workflows. An [n8n community node](https://www.npmjs.com/package/@digitalocean/n8n-nodes-digitalocean-gradient-serverless-inference) is available that connects to any DigitalOcean-hosted model using your model access key. You can self-host n8n using the [n8n Marketplace app](https://marketplace.digitalocean.com/apps/n8n).

## Model Access Keys

You can create and manage model access keys on the [control panel’s **Serverless inference** page](https://cloud.digitalocean.com/gen-ai/model-access-keys) in the **Model Access Keys** section.

### Create Keys

To create a model access key, click **Create model access key** to open the **Add model access key** window. In the **Key name** field, choose a name for your model access key, then click **Save**.

Your new model access key with its creation date appears in the **Model Access Keys** section. The secret key is visible only once, immediately after creation, so copy and store it securely.

Model access keys are private and incur [usage-based charges](https://docs.digitalocean.com/products/gradient-ai-platform/details/pricing/). Do not share them or expose them in front-end code. We recommend storing them using a secrets manager (for example, AWS Secrets Manager, HashiCorp Vault, or 1Password) or a secure environment variable in your deployment configuration.

### Rename Keys

Renaming a model access key can help you organize and manage your keys more effectively, especially when using multiple keys for different projects or environments.

To rename a key, click **…** to the right of the key in the list to open the key’s menu, then click **Rename**. In the **Rename model access key** window that opens, in the **Key name** field, enter a new name for your key and then click **UPDATE**.

### Regenerate Keys

Regenerating a model access key creates a new secret key and immediately and permanently invalidates the previous one. If a key has been compromised or want to rotate keys for security purposes, regenerate the key, then update any applications using the previous key to use the new key.

To regenerate a key, click **…** to the right of the key in the list to open the key’s menu, then click **Regenerate**. In the **Regenerate model access key** window that opens, enter the name of your key to confirm the action, then click **Regenerate access key**. Your new secret key is displayed in the **Model Access Keys** section.

### Delete Keys

Deleting a model access key permanently and irreversibly destroys it. Any applications using a destroyed key lose access to the API.

To delete a key, click **…** to the right of the key in the list to open the key’s menu, then click **Delete**. In the **Delete model access key** window that opens, type the name of the key to confirm the deletion, then click **Delete access key**.

In this article...

- [Serverless Inference API Endpoints](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/use-serverless-inference/#serverless-inference-api-endpoints)
  - [/v1/models](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/use-serverless-inference/#v1models)
  - [/v1/chat/completions](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/use-serverless-inference/#v1chatcompletions)
- [Model Access Keys](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/use-serverless-inference/#keys)
  - [Create Keys](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/use-serverless-inference/#create)
  - [Rename Keys](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/use-serverless-inference/#rename-keys)
  - [Regenerate Keys](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/use-serverless-inference/#regenerate-keys)
  - [Delete Keys](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/use-serverless-inference/#delete-keys)

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