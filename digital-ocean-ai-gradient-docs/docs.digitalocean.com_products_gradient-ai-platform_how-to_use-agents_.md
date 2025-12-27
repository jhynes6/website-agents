---
url: "https://docs.digitalocean.com/products/gradient-ai-platform/how-to/use-agents/"
title: "How to Use Agents in Your Applications on DigitalOcean Gradient™ AI Platform | DigitalOcean Documentation"
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
- Use Agents

[Give Feedback](https://ideas.digitalocean.com/documentation)

# How to Use Agents in Your Applications on DigitalOcean Gradient™ AI Platform

Validated on 4 Mar 2025 • Last edited on 10 Dec 2025

DigitalOcean Gradient™ AI Platform lets you build fully-managed AI agents with knowledge bases for retrieval-augmented generation, multi-agent routing, guardrails, and more, or use serverless inference to make direct requests to popular foundation models.

You can access your agent through two different interfaces: an endpoint or a chatbot.

- **Endpoint**: Endpoints are URLs automatically generated upon agent creation and you can integrate them into your app to send requests to and receive JSON responses from. Similar to a chatbot interface, you can send the agent a string of text that the agent processes and responds to. Using an endpoint also allows you to configure additional request parameters, such as maximum tokens to generate and retrieval information settings.

- **Chatbot**: Chatbots allow users to interact with your agent through a chatbot interface that you embed into your site using a snippet of HTML code. You can only use the chatbot interface if the agent’s endpoint is set to public.


Using either an endpoint or chatbot depends on your use case. If you want to integrate your agent into a customized user interface or use it to produce content for your website, an endpoint is a good option. If you want to create a basic technical support chatbot for your company’s website, an embedded chatbot is a better option.

## Set Your Agent’s Endpoint Availability

Before using your agent, we recommend setting the endpoint’s availability to determine who can access it and what interfaces are available. You can set the agent’s endpoint to either private or public.

- **Private**: Agent endpoints are set to private by default. This means only other resources in your account, such as [other agents or functions](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/route-agents/) or requests authenticated with an access key can access the agent.

- **Public**: Public endpoints allow you to access and use the chatbot embed feature. You do not need to set up an access key to use an embedded chatbot, however, like private endpoints, requests sent directly to an agent’s endpoint still require an [access key](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/use-agents/#access-key).


To change endpoint’s availability in the [DigitalOcean Control Panel](https://cloud.digitalocean.com/), click **Agent Platform** in the left menu, then in the **Agent Workspaces** tab, select the workspace that contains the agent you want to set an endpoint for. From the workspace’s **Agents** tab, click the agent, and then in its **Overview** tab, scroll down to the **ENDPOINT** section and click the **Edit** button. In the **Set endpoint availability to private** window, select the availability you want and click **Save**.

If you set your agent’s endpoint to public, the chatbot embed code becomes available in the **CHATBOT** section below the **ENDPOINT** section.

### Using Automation

Changing an agent endpoint from private to public requires the unique identifier for the agent. To obtain a list of agents with their unique identifiers, use the [`/v2/gen-ai/agents` endpoint](https://docs.digitalocean.com/reference/api/digitalocean/#operation/genai_list_agents).

How to Change Status of Agent Endpoint Using the DigitalOcean API

1. [Create a personal access token](https://docs.digitalocean.com/reference/api/create-personal-access-token/) and save it for use with the API.
2. Send a PUT request to [`https://api.digitalocean.com/v2/gen-ai/agents/{uuid}/deployment_visibility`](https://docs.digitalocean.com/reference/api/digitalocean//#operation/genai_update_agent_deployment_visibility).

### cURL

Using cURL:

```shell
curl -X PUT \
  -H "Content-Type: application/json"  \
  -H "Authorization: Bearer $DIGITALOCEAN_TOKEN" \
  "https://api.digitalocean.com/v2/gen-ai/agents/1b418231-b7d6-11ef-bf8f-4e013e2ddde4/deployment_visibility" \
  -d '{
    "uuid": "1b418231-b7d6-11ef-bf8f-4e013e2ddde4",
    "visibility": "VISIBILITY_PUBLIC"
  }'
```

To use the public endpoint in your app, copy the URL from the `url` field returned in the response.

Setting the endpoint public displays a **Chatbot** section with a JavaScript code snippet in the **Overview** tab in the control panel. Copy and paste the code snippet directly into your application, such as WordPress, to use the chatbot. To learn more, see the [community articles on adding chatbots](https://www.digitalocean.com/community/tags/ai-ml).

## Create an Access Key for an Endpoint

To access an agent’s endpoint from an external source outside of DigitalOcean, you need create an access key. Access keys are used to authenticate requests to the agent’s endpoint.

To create the access key from the [DigitalOcean Control Panel](https://cloud.digitalocean.com/), click **Agent Platform** in the left menu, then in the **Agent Workspaces** tab, select the workspace that contains the agent you want to create an access key for. From the workspace’s **Agents** tab, click the agent, and then in its **Overview** page, click the **Settings** tab. In the **Endpoint Access Keys** section, click **Create Key** to open the **Create Agent Access Key** window. Provide a name for the key in the **Key name** field and then click **Create** to see your newly created key.

Then, copy the secret key and securely store it. We do not show it again for security reasons.

Once you have the key, you can integrate it into your app to authenticate requests.

### Using Automation

Creating an agent endpoint API key using the DigitalOcean API requires the unique identifier of the agent and a name for the key. To obtain a list of agents with their unique identifiers, use the [`/v2/gen-ai/agents` endpoint](https://docs.digitalocean.com/reference/api/digitalocean/#operation/genai_list_agents).

How to Create an Agent Endpoint Key Using the DigitalOcean API

1. [Create a personal access token](https://docs.digitalocean.com/reference/api/create-personal-access-token/) and save it for use with the API.
2. Send a POST request to [`https://api.digitalocean.com/v2/gen-ai/agents/{agent_uuid}/api_keys`](https://docs.digitalocean.com/reference/api/digitalocean//#operation/genai_create_agent_api_key).

### cURL

Using cURL:

```shell
curl -X POST \
  -H "Content-Type: application/json"  \
  -H "Authorization: Bearer $DIGITALOCEAN_TOKEN" \
  "https://api.digitalocean.com/v2/gen-ai/agents/1b418231-b7d6-11ef-bf8f-4e013e2ddde4/api_keys" \
  -d '{
    "agent_uuid": "1b418231-b7d6-11ef-bf8f-4e013e2ddde4",
    "name": "test-key"
  }'
```

You can [list all agent API keys](https://docs.digitalocean.com/reference/api/digitalocean/#operation/genai_list_agent_api_keys), [regenerate a key](https://docs.digitalocean.com/reference/api/digitalocean/#operation/genai_regenerate_agent_api_key), or [update a key](https://docs.digitalocean.com/reference/api/digitalocean/#operation/genai_update_agent_api_key) after creation.

## Use Agent’s Endpoints

In the [DigitalOcean Control Panel](https://cloud.digitalocean.com/), click **Agent Platform** in the left menu, then in the **Agent Workspaces** tab, select the workspace that contains the agent you want to use its endpoint for. From the workspace’s **Agents** tab, click the agent, and then from its **Overview** page, see the **ENDPOINT** section.

You can send requests to the endpoint’s API by appending `/api/v1/chat/completions` to the end of the URL and sending a JSON request body, like in this example cURL request:

```shell
curl -i \
  -X POST \
  $AGENT_ENDPOINT/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AGENT_ACCESS_KEY" \
  -d '{
    "messages": [\
      {\
        "role": "user",\
        "content": "What is the capital of France?"\
      }\
    ],
    "stream": false,
    "include_functions_info": false,
    "include_retrieval_info": false,
    "include_guardrails_info": false
  }'
```

This cURL example sends a request to the agent’s endpoint to generate a response to the user’s question `What is the capital of France?`. It uses an `AGENT_ENDPOINT` and `AGENT_ACCESS_KEY` environment variables to authenticate the request.

Each endpoint has its own API documentation that you can access by appending `/docs` to the end of the URL, like this: `https://<agent-indentifier>.ondigitalocean.app/docs`. The documentation contains a rendered OpenAPI specification of all available request body parameters and response schemas.

The following example shows how to use the [OpenAI Python library](https://platform.openai.com/docs/libraries) to send a request to an agent’s endpoint.

`use-agent-endpoint-key.py`

```python
# Install OS, JSON, and OpenAI libraries.
import os
import json
from openai import OpenAI

# Set your agent endpoint and access key as environment variables in your OS.
agent_endpoint = os.getenv("agent_endpoint") + "/api/v1/"
agent_access_key = os.getenv("agent_access_key")

if __name__ == "__main__":
    client = OpenAI(
        base_url = agent_endpoint,
        api_key = agent_access_key,
    )

    response = client.chat.completions.create(
        model = "n/a",
        messages = [{"role": "user", "content": "Can you provide the name of France's capital in JSON format."}],
        extra_body = {"include_retrieval_info": True}
    )

# Prints response's content and retrieval object.
    for choice in response.choices:
        print(choice.message.content)

    response_dict = response.to_dict()

    print("\nFull retrieval object:")
    print(json.dumps(response_dict["retrieval"], indent=2))
```

This script sends a request to an agent’s endpoint and asks it to return the name of France’s capital in JSON format in the console and its retrieval information. You do not need to append `/chat/completions` to the end of the endpoint URL when using the `openai` library.

### View Agent Response Citations

You can view the agent’s retrieval information in the response by setting the following retrieval parameters to `true`, like this:

- `include_retrieval_info`: Includes the knowledge bases and subsequent files accessed to generate the response.
- `include_functions_info`: Includes a list of functions used to generate the response.
- `include_guardrails_info`: Includes a list of guardrails used to generate the response and the reasons why the guardrails were triggered.

See the example requests above for an example of how to include retrieval information in a request.

The retrieval object in a response looks like this:

```json
{
    "retrieval": {
        "retrieved_data": [\
            {\
                "id": "...",\
                "index": "...",\
                "page_content": "some text",\
                "score": -9549511700,\
                "filename": "file name or url",\
                "data_source_id": "...",\
                "metadata": {...additional metadata for chunk}\
            },\
        ]
    },
    "guardrails": {
        "triggered_guardrails": [\
           { rule_name: "sensitive_data", message: "what trigggered it" }\
         ]
    },
    "functions": {
        "called_functions": ["get_weather"]
    },
}
```

## Use Chatbot Interface

To embed the chatbot widget on public sites, [set your agent’s endpoint to public](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/use-agents/#set-availability). Setting the endpoint public displays a **CHATBOT** section with an HTML `<script>` element code snippet. You can directly embed the snippet in your application, such as a WordPress or static HTML website, to use the chatbot.

For enhanced security with the chatbot, we strongly recommend that you add allowed domains. Doing so ensures that your agent endpoint can only be reached through those approved domains. In the **CHATBOT** section, click **Customize** to open the **Customize chatbot design** window. In the **Chatbot security** section, add the domains where you want to embed this chatbot. You can add multiple domains, separated by commas, such as `https://example.com, https://*.sammys.com`. Leaving this field blank means your chatbot code can be embedded on any website.

Copy and paste the code snippet into your application. The embed code looks like this:

```html
<script async
  src="https://<agent-indentifier>.ondigitalocean.app/static/chatbot/widget.js"
  data-agent-id="<agent-data-indentifier>"
  data-chatbot-id="<agent-chatbot-indentifier>"
  data-name="My Chatbot"
  data-primary-color="#031B4E"
  data-secondary-color="#E5E8ED"
  data-button-background-color="#0061EB"
  data-starting-message="Hello! I am an AI agent. How can I help you today?"
  data-logo="https://example.com/your-logo.svg">
</script>
```

The code contains several parameters that you can customize for your application. To add a chatbot logo, upload an image to your website and then set the `data-logo` parameter to the image’s URL. You do not need to treat the `data-agent-id` and `data-chatbot-id` fields as secrets.

You cannot view retrieval information in the chatbot interface.

In this article...

- [Set Your Agent’s Endpoint Availability](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/use-agents/#set-availability)
  - [Using Automation](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/use-agents/#using-automation)
- [Create an Access Key for an Endpoint](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/use-agents/#access-key)
  - [Using Automation](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/use-agents/#using-automation-1)
- [Use Agent’s Endpoints](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/use-agents/#use-endpoint)
  - [View Agent Response Citations](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/use-agents/#view-agent-response-citations)
- [Use Chatbot Interface](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/use-agents/#use-chatbot-interface)

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