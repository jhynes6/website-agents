---
url: "https://docs.digitalocean.com/products/gradient-ai-platform/concepts/function-instructions/"
title: "Function Instructions Best Practices for DigitalOcean Gradient™ AI Platform | DigitalOcean Documentation"
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
- Function Instructions Best Practices

[Give Feedback](https://ideas.digitalocean.com/documentation)

# Function Instructions Best Practices for DigitalOcean Gradient™ AI Platform

Validated on 13 Feb 2025 • Last edited on 15 Aug 2025

DigitalOcean Gradient™ AI Platform lets you build fully-managed AI agents with knowledge bases for retrieval-augmented generation, multi-agent routing, guardrails, and more, or use serverless inference to make direct requests to popular foundation models.

Learning to write clear and concise function instructions helps agents determine when and how to call functions effectively. This improves access to external data sources, APIs, and databases while ensuring accurate responses. Well-structured function instructions define the function’s purpose, inputs, outputs, and constraints, making them more reliable. Following these best practices when [routing functions in your agent](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/route-agent-functions/) reduces errors and improves execution.

The following examples provide well-structured function instructions for a `get-weather.js` JavaScript function. We have provided the `get-weather.js` function along with its input and output JSON below for reference.

## Function Example Reference

Below is an example implementation of the `get-weather.js` function with input and output schema examples.

### Input Example

The input schema defines the data the `get-weather.js` function requires. The function needs a ZIP code and optionally accepts a temperature measurement unit.

```json
{
    "zipCode": {
      "type": "string",
      "required": true,
      "description": "The ZIP code of the location. Only US ZIP codes are supported."
    },
    "measurement": {
      "type": "string",
      "required": false,
      "description": "The temperature measurement unit, either 'C' or 'F'.  The default is 'F'"
    }
}
```

### Function Example

The `get-weather.js` function retrieves weather details based on the [input schema](https://docs.digitalocean.com/products/gradient-ai-platform/concepts/function-instructions/#input-example) and returns data in the [output schema](https://docs.digitalocean.com/products/gradient-ai-platform/concepts/function-instructions/#output-example).

`get-weather.js`

```js
import axios from 'axios';

async function main(args) {
  const zipCode = args.zipCode;
  const measurement = args.measurement || 'F';

  const weatherResponse = await axios.get(`https://your-api.com/weather/${zipCode}`, {
    params: { measurement }
  });

  const { temperature, conditions } = weatherResponse.data;

  return {
    body: { temperature, measurement, conditions }
  };
}
```

### Output Example

The output schema defines what the `get-weather.js` function returns. The function returns the temperature, the measurement unit used, and the weather conditions.

```json
{
    "temperature": {
      "description": "The current temperature",
      "type": "number"
    },
    "measurement": {
      "description": "The measurement unit used for the temperature (F or C)",
      "type": "string"
    },
    "conditions": {
      "description": "The unit of temperature measurement.",
      "type": "string"
    }
}
```

## Specify the Function’s Purpose

Agents need straightforward, concise function instructions to determine when and how to call a function. Avoid vague or overly technical descriptions that obscure the function’s purpose.

Define the function’s purpose by:

- Using a descriptive name, such as `get_weather`.
- Stating its role and the data it provides.
- Specifying the exact data it retrieves and how it is structured.
- Avoiding implementation details like API calls or database queries.
- Removing redundant phrasing, such as unnecessary mentions of JSON format.

| Prefer | Avoid |
| --- | --- |
| > **Function Name:**`get_weather`<br>> <br>> **Description:** Retrieves the current temperature and weather conditions for a given ZIP code. Supports Celsius and Fahrenheit. | > **Function Name:**`get_weather`<br>> <br>> **Description:** Gets weather data. |

## Specify the Function’s Input

Define the function’s parameters to ensure agents pass the correct values. Avoid vague descriptions, and explicitly state required and optional parameters.

Describe the function’s input and parameters by:

- Listing all required parameters and their expected data types.
- Describing each parameter’s purpose and how it affects the function.
- Specifying constraints like valid ranges, formats, or supported values.
- Providing an example of a properly formatted function call.
- Defining function constraints like geographic limits or required conditions.

| Prefer | Avoid |
| --- | --- |
| > **Parameters:**<br>> <br>> • `zipCode (string, required)`: The ZIP code of the location. Only US ZIP codes are supported.<br>> <br>> • `measurement (string, optional, default: "F")`: The temperature measurement unit, either “C” or “F”.<br>> <br>> **Example Call:**`get_weather({"zipCode": "10001", "measurement": "C"})`<br>> <br>> **Constraints:**<br>> <br>> • Only retrieves weather data for ZIP codes within the United States. | > **Parameters:**<br>> <br>> • `zipCode`: Location.<br>> <br>> • `measurement`: Temperature format.<br>> <br>> **Example Call:**`get_weather({"zipCode": "90210"})` |

## Specify the Function’s Output

Agents need to understand what data a function returns, not how it retrieves it. Avoid mentioning algorithms, API calls, or database queries, as they don’t help the agent determine when or how to use the function. Define what the function returns and any limitations on the data provided.

Define the function’s output by:

- Defining the structure of the returned data.
- Describing all relevant output fields.
- Providing an example of the expected output.
- Specifying supported regions, formats, or data availability.
- Defining limitations with exact values, ranges, or conditions.

| Prefer | Avoid |
| --- | --- |
| > **Response:**<br>> <br>> • `temperature (number)`: The current temperature.<br>> <br>> • `conditions (string)`: The weather conditions (for example, “Cloudy”, “Sunny”).<br>> <br>> • `measurement (string)`: The unit of temperature measurement.<br>> <br>> **Example Response:**`{"temperature": 22.5, "conditions": "Sunny", "measurement": "C"}` | > **Response:** Calls an external API to fetch weather data and returns the results in JSON format.<br>> <br>> **Example Response:**`{"temperature": 22.5, "conditions": "Sunny"}` |

## Full Example

This example integrates function purpose, output, description, and constraints into a complete instruction set, ensuring clarity and usability for agents.

| Prefer | Avoid |
| --- | --- |
| > **Function Name:**`get_weather`<br>> <br>> **Description:** Retrieves the current temperature and weather conditions for a given ZIP code. Supports Celsius and Fahrenheit.<br>> <br>> **Parameters:**<br>> <br>> • `zipCode (string, required)`: The ZIP code of the location. Only US ZIP codes are supported.<br>> <br>> • `measurement (string, optional, default: "F")`: The temperature measurement unit, either “C” or “F”.<br>> <br>> **Example Call:**`get_weather({"zipCode": "10001", "measurement": "C"})`<br>> <br>> **Constraints:**<br>> <br>> • Only retrieves weather data for ZIP codes within the United States.<br>> <br>> **Response:**<br>> <br>> • `temperature (number)`: The current temperature.<br>> <br>> • `conditions (string)`: The weather conditions (for example, “Cloudy”, “Sunny”).<br>> <br>> • `measurement (string)`: The unit of temperature measurement.<br>> <br>> **Example Response:**`{"temperature": 22.5, "conditions": "Sunny", "measurement": "C"}` | > **Function Name:**`get_weather`<br>> <br>> **Description:** Gets weather data.<br>> <br>> **Parameters:**<br>> <br>> • `zipCode`: Location.<br>> <br>> • `measurement`: Temperature format.<br>> <br>> **Example Call:**`get_weather({"zipCode": "90210"})`<br>> <br>> **Response:** Calls an external API to fetch weather data and returns the results in JSON format.<br>> <br>> **Example Response:**`{"temperature": 22.5, "conditions": "Sunny"}` |

In this article...

- [Function Example Reference](https://docs.digitalocean.com/products/gradient-ai-platform/concepts/function-instructions/#function-example-reference)
  - [Input Example](https://docs.digitalocean.com/products/gradient-ai-platform/concepts/function-instructions/#input-example)
  - [Function Example](https://docs.digitalocean.com/products/gradient-ai-platform/concepts/function-instructions/#function-example)
  - [Output Example](https://docs.digitalocean.com/products/gradient-ai-platform/concepts/function-instructions/#output-example)
- [Specify the Function’s Purpose](https://docs.digitalocean.com/products/gradient-ai-platform/concepts/function-instructions/#specify-the-functions-purpose)
- [Specify the Function’s Input](https://docs.digitalocean.com/products/gradient-ai-platform/concepts/function-instructions/#specify-the-functions-input)
- [Specify the Function’s Output](https://docs.digitalocean.com/products/gradient-ai-platform/concepts/function-instructions/#specify-the-functions-output)
- [Full Example](https://docs.digitalocean.com/products/gradient-ai-platform/concepts/function-instructions/#full-example)

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