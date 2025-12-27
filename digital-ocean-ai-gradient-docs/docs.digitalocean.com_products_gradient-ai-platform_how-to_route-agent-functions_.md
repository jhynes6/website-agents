---
url: "https://docs.digitalocean.com/products/gradient-ai-platform/how-to/route-agent-functions/"
title: "How to Route Functions in Agents on DigitalOcean Gradient™ AI Platform | DigitalOcean Documentation"
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
- Route Functions in Agents

[Give Feedback](https://ideas.digitalocean.com/documentation)

# How to Route Functions in Agents on DigitalOcean Gradient™ AI Platform

Validated on 5 Nov 2024 • Last edited on 28 Aug 2025

DigitalOcean Gradient™ AI Platform lets you build fully-managed AI agents with knowledge bases for retrieval-augmented generation, multi-agent routing, guardrails, and more, or use serverless inference to make direct requests to popular foundation models.

Functions are blocks of code that you can call in your agent. Functions let the agent’s foundation model to access external data sources, APIs, and databases. This lets your agent get real-time, third-party information that may not be present in a static knowledge base.

You can call functions if your agent needs to perform any of the following:

- Fetch external data to enrich knowledge and provide timely, relevant information from 3rd-party APIs.

- Retrieve and analyze user profile data from application user databases to provide personalized recommendations and support.

- Trigger reports, alerts, or workflows based on API data and user context.

- Monitor user activity patterns to detect anomalies or issues that require proactive intervention.

- Consolidate support tickets from various databases, analyze them to identify trending issues or common problems, or automatically escalate high-priority tickets that require immediate attention based on predefined criteria.


In addition to [function pricing](https://docs.digitalocean.com/products/functions/details/pricing/), we charge for tokens the agent uses to determine whether the user question needs to be routed to a function, which functions, and in what order they are required.

## Function Requirements

You need to first [create a function using DigitalOcean Functions](https://docs.digitalocean.com/products/functions/how-to/create-functions/) that meets the following requirements:

- The function must be a [web function](https://docs.digitalocean.com/products/functions/how-to/configure-functions/#access--security).

- All data types in your schema must be either a `string`, `boolean`, or a `number`.

- The function’s response must be in a `body` key as shown below:


```
...
return {
      body: {<function response>}
}
...
```

- Private functions require a secure web function for authentication. When enabled, we apply the function’s password and restrict access to secure mechanisms. We recommend [enabling this setting to protect your function from unauthorized access](https://docs.digitalocean.com/products/functions/how-to/configure-functions/#access--security).


We also recommend using Node.js 18 with a 128 MB memory limit and Python 3.9 with a 256 MB memory limit for optimal cold start performance (when the function’s code is downloaded and the execution environment set up). For more information on function runtimes and memory limits, see [Configure Functions](https://docs.digitalocean.com/products/functions/how-to/configure-functions/).

### Function Example

To get weather data, you can create a function in JavaScript using the following code:

`get_weather.js`

```js
import axios from 'axios';

async function main(args) {
  const zipCode = args.zipCode || '';
  const measurement = args.measurement || 'F';

  try {
    const response = await axios.get(`https://your-api.com/weather/${zipCode}`, {
      params: { measurement }
    });

    const { temperature = 0.0, conditions = 'Unknown' } = response.data;

    return {
      body: {
        temperature,
        conditions,
        measurement
      }
    };
  } catch (error) {
    console.error("Error fetching weather data:", error);
    return {
      body: {
        temperature: 0.0,
        conditions: "Unknown",
        measurement
      }
    };
  }
}

export default main;
```

## Add a Function Route Using Automation

Adding a function route using the DigitalOcean API requires the unique identifier of the agent and one or more [functions to route to](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/route-agent-functions/#function-requirements). You also need to provide a name and namespace of the function, instructions on when the agent should call the function, and types of data that the function expects as input and output schema.

To obtain a list of agents with their unique identifiers, use the [`/v2/gen-ai/agents` endpoint](https://docs.digitalocean.com/reference/api/digitalocean/#operation/genai_list_agents). You can get the namespace for your function in the **Namespace Info** section in the **Settings** tab of your function.

How to Add a Function Route Using the DigitalOcean API

1. [Create a personal access token](https://docs.digitalocean.com/reference/api/create-personal-access-token/) and save it for use with the API.
2. Send a POST request to [`https://api.digitalocean.com/v2/gen-ai/agents/{agent_uuid}/functions`](https://docs.digitalocean.com/reference/api/digitalocean//#operation/genai_attach_agent_function).

### cURL

Using cURL:

```shell
curl -X POST \
  -H "Content-Type: application/json"  \
  -H "Authorization: Bearer $DIGITALOCEAN_TOKEN" \
  "https://api.digitalocean.com/v2/gen-ai/agents/1b418231-b7d6-11ef-bf8f-4e013e2ddde4/functions" \
  -d '{
    "agent_uuid": "1b418231-b7d6-11ef-bf8f-4e013e2ddde4",
    "function_name": "funzip",
    "description": "Use when you need the zipcode for a city",
    "input_schema": {
      "city": {
        "description": "the city you want a zipcode for",
        "required": true,
        "type": "string"
      }
    },
    "output_schema": {
      "zip_code": {
        "description": "The zipcode of the desired city",
        "type": "number"
      }
    },
    "faas_namespace": "fn-2014dc98-faa1-45f4-ba1f-59910cb3d399",
    "faas_name": "default/get-zipcode"
  }'

```

To view function routes for an agent, use the [`/v2/gen-ai/agents/{uuid}/child_agents` endpoint](https://docs.digitalocean.com/reference/api/digitalocean/#operation/genai_get_agent_children).

## Add a Function Route Using the Control Panel

To call the function in the agent from the [DigitalOcean Control Panel](https://cloud.digitalocean.com/), click **Agent Platform** in the left menu, then in the **Agent Workspaces** tab, select the workspace that contains the agent you want to add a function route for. From the workspace’s **Agents** tab, click the agent, and then click the **Resources** tab.

In the **Resources** tab, scroll to the **Function Route** section, and click **Add function route** to open the **Add a function route** page.

In the **Define the function** section, specify the following:

- **Namespace**: Select the namespace for your function from the **Namespace** drop-down list.

- **Function**: Select the function name, for example `get-weather`, from the **Select function** drop-down list.

- **Function instructions**: Specify when the agent should call the function in the text box. For example, you can enter something like `Call this function when asked about the weather for a zip code`.


Next, define the input and output schema that the agent accepts. The schema provides a detailed description of the inputs, outputs, and the logic required for the agent to call and use these functions:

- **Input schema**: Specifies the types of data that the function expects as inputs. Input schemas must follow the [OpenAPI 3.0 specification](https://spec.openapis.org/oas/v3.0.3). Each input must define an object in a `parameters` array using the OpenAPI format. If your schema is invalid or missing required fields like `type`, your function route may fail to register.

In the **Define input schema** section, specify the input schema parameters. For the `get-weather` function example, add these parameters in the format as shown:



```json
{
    "parameters": [\
      {\
        "name": "zipCode",\
        "in": "query",\
        "description": "The ZIP code for which to fetch the weather",\
        "required": true,\
        "schema": {\
          "type": "string"\
        }\
      },\
      {\
        "name": "measurement",\
        "in": "query",\
        "description": "The measurement unit for temperature (F or C)",\
        "required": false,\
        "schema": {\
          "type": "string"\
        }\
      }\
    ]
}
```

- **Output schema (optional)**: Specifies the data structure a function returns, helping the agent interpret and use the output. While an input schema and function description work for standalone functions, an output schema helps when functions depend on each other. It shows the agent where data comes from and how it flows through multiple functions. This improves accuracy, especially for complex data structures.

For example, two functions can get the weather for a location: `get-zip-code` and `get-weather`. If `get-weather` needs a zip code, the function routing starts with `get-zip-code`, which then routes to `get-weather`. `get-weather` retrieves the weather data and passes it to the agent to display or use.

In the **Define output schema** section, specify the output schema parameters. For the `get-weather` function example, you should add these parameters in the format as shown:



```json
{
      "temperature": {
        "description": "The temperature for the specified location",
        "type": "number"
      },
      "measurement": {
        "description": "The measurement unit used for the temperature (F or C)",
        "type": "string"
      },
      "conditions": {
        "description": "A description of the current weather conditions (Sunny, Cloudy, etc)",
        "type": "string"
      }
}
```


In the **Function route name** field, enter a name for the function route and then click **Add Function**.

Next, you can [test the agent in the Agent Playground](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/test-agents/) and then [use your agent](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/use-agents/) in a chat bot or embed it in your application.

In this article...

- [Function Requirements](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/route-agent-functions/#function-requirements)
  - [Function Example](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/route-agent-functions/#function-example)
- [Add a Function Route Using Automation](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/route-agent-functions/#add-a-function-route-using-automation)
- [Add a Function Route Using the Control Panel](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/route-agent-functions/#add-a-function-route-using-the-control-panel)

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