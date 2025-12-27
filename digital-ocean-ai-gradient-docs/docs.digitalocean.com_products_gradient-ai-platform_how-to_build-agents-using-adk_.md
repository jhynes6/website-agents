---
url: "https://docs.digitalocean.com/products/gradient-ai-platform/how-to/build-agents-using-adk/"
title: "How to Build, Test, and Deploy Agents on DigitalOcean Gradient™ AI Platform Using Agent Development Kit | DigitalOcean Documentation"
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
- Build Agents Using Agent Development Kit

[Give Feedback](https://ideas.digitalocean.com/documentation)

# How to Build, Test, and Deploy Agents on DigitalOcean Gradient™ AI Platform Using Agent Development Kitpublic

Validated on 9 Dec 2025 • Last edited on 17 Dec 2025

DigitalOcean Gradient™ AI Platform lets you build fully-managed AI agents with knowledge bases for retrieval-augmented generation, multi-agent routing, guardrails, and more, or use serverless inference to make direct requests to popular foundation models.

You can build, test, and deploy agent workflows from within your development framework using the Agent Development Kit (ADK). You can also add knowledge bases to your agent using the knowledge bases endpoint to give the agent access to custom data, view logs and traces, and run agent evaluations.

If you want to use the DigitalOcean Control Panel, CLI, or API instead, see [How to Create Agents on DigitalOcean Gradient™ AI Platform](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/create-agents/).

## Prerequisites

You must have the following to use the Agent Development Kit:

- Python version 3.13

- Dependencies listed in `requirements.txt` at the root of the folder or repo to deploy.

- `.env` file with environment variables to use in agent deployment.

- [Model access key for authentication](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/use-serverless-inference/#keys). Set the key in the `GRADIENT_MODEL_ACCESS_KEY` environment variable and add it to your `.env` file. For running your agent locally, you must export the key in your terminal for it to be accessible to the application.

- [Your account’s personal access token](https://docs.digitalocean.com/reference/api/create-personal-access-token/). The key must have all [CRUD scopes](https://docs.digitalocean.com/reference/api/create-personal-access-token/#about-custom-scopes) for `genai` and `read` scope for `project`. Set the API key in the `DIGITALOCEAN_API_TOKEN` environment variable and add it to your `.env` file to enable deploying the agent to your DigitalOcean account.


## About Entrypoint

Your agent code must have an `entrypoint` function that starts with the `@entrypoint` decorator. The entrypoint tells the Agent Development Kit runtime how to host your agent code and is called when you invoke your agent.

The `entrypoint` function requires two parameters:

- `payload` is the first parameter for the payload.

- `context` is the second parameter for the context that may get sent such as `trace_ids`.


The function can look similar to the following:

```python
@entrypoint
def entry(payload, context):
   query = payload["prompt"]
   inputs = {"messages": [HumanMessage(content=query)]}
   result = workflow.invoke(inputs)
   return result
```

The content of the payload is determined by the agent. In this example, the agent requires the payload in the JSON body of the `POST` request to contain a `prompt` field.

## Install Agent Development Kit

To start building an agent using the Agent Development Kit, you must first install the `gradient-adk` package using `pip`:

```
pip install gradient-adk
```

Installing the `gradient-adk` package automatically gives you access to the `gradient` CLI.

To view the version of the installed package, run:

```
gradient --version
```

## Set Up a Project

You can either use a project for an existing agent or initialize a new project to build, test, and deploy your agent.

Use Existing Project

If you have an existing agent, you can bring it on the Gradient AI Platform using the Agent Development Kit.

First, navigate to that agent folder and review the `requirements.txt` to verify that the Agent Development Kit is installed. The `requirements.txt` must have the `gradient-adk` and `gradient` lines listed as dependencies.

Then, import the `entrypoint` module from the Agent Development Kit by adding `from gradient_adk import entrypoint` in your agent code. This module lets you create an [`@entrypoint` decorator](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/build-agents-using-adk/#entrypoint) and enables you to add an `entrypoint` function in your agent code. For example, in an existing LangGraph agent code, you can add the following `import` statement at the top of your `main.py` file:

```python
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition
from gradient_adk import entrypoint
```

Finally, write your `entrypoint` function in the agent code. For more information about the entrypoint decorator, see [entrypoint decorator](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/build-agents-using-adk/#entrypoint).

Next, run the following command to create a Gradient configuration file:

```
gradient agent configure
```

The Gradient configuration file is required to run or deploy your agent. When prompted, enter the agent name, agent deployment name (such as production, staging, or beta), and the file your entrypoint lives in. For example, `example-agent`, `staging`, and `main.py` (if your agent code is in `main.py`), respectively. You see a `Configuration complete` message once the configuration completes. Next, run the agent locally.

Initialize New Project

You can initialize a new project for your agent. Navigate to the desired folder for your agent and run the following command:

```
gradient agent init
```

To provide an easy way for you to get started, the command creates folders and files (`requirements.txt`), sets up a base template for a simple LangGraph example agent that makes a call to a `openai-gpt-oss-120b` model using [serverless inference](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/use-serverless-inference/)(`main.py`), and sets up a Gradient configuration file which is required to run or deploy your agent.

When prompted, specify an agent workspace name and an agent deployment name. For example, `staging`, and `example-agent`, respectively.

After the project initialization is complete, your directory structure looks like the following:

![Agent Development Kit directory](https://docs.digitalocean.com/screenshots/gradient-ai-platform/adk-directory.6b8faad25b289055c850dcc532042701d6b63d0ea581c0e24e133690fa9f7833.png)

Next, update `main.py` to implement your agent and update the `.env` file with your `GRADIENT_MODEL_ACCESS_KEY` and `DIGITALOCEAN_API_TOKEN`. Then, run the agent locally.

## Run and Test Agents Locally

To run an agent, use the following command:

```
gradient agent run
```

This starts up a local server on `localhost:8080` and exposes an `/run` endpoint that you can use to interact with your agent.

You see the following output:

```
Entrypoint: main.py
Server: http://0.0.0.0:8080
Agent: example_agent
Entrypoint endpoint: http://0.0.0.0:8080/run
```

To invoke the agent, send a `POST` request to the `/run` endpoint using `curl`. For example:

```shell
curl -X POST http://localhost:8080/run
-H "Content-Type: application/json"
-d '{"prompt": "How are you?"}'
```

Your agent processes the request and returns a response, such as `Hello! I am doing good, thank you for asking. How can I assist you today?`.

To view more verbose debugging logs, use:

```
gradient agent run --verbose
```

Once you verify that your agent is working correctly, you can deploy it.

## Deploy and Test Your Agent

Use the following command to deploy your agent:

```
gradient agent deploy
```

This starts the build and deployment, which takes between 1 minute and 5 minutes. If your agent fails to build or deploy, see [Troubleshoot Build or Deployment Failures](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/build-agents-using-adk/#troubleshoot-agent-deployment).

After the deployment completes, you can see the deployment endpoint that the agent is running in your terminal. It includes the workspace identifier (`b1689852-xxxx-xxxx-xxxx-xxxxxxxxxxxx`) and deployment name (`staging`). For example:

```bash
✅ Deployment completed successfully! [01:20]
Agent deployed successfully! (example-agent/staging)
To invoke your deployed agent, send a POST request to https://agents.do-ai.run/b1689852-xxxx-xxxx-8c68-dce069403e97/v1/staging/run with your properly formatted payload.
```

To invoke your deployed agent and verify that it is running correctly, send a `POST` request to the deployment endpoint, passing the prompt in the request JSON body. For example:

```shell
curl -X POST \
  -H "Authorization: Bearer $DIGITALOCEAN_TOKEN" \
  -H "Content-Type: application/json" \
  "https://agents.do-ai.run/v1/b1689852-xxxx-xxxx-8c68-dce069403e97/staging/run" \
  -d '{"prompt": "hello"}'
```

The agent processes your request and returns a response, such as `"Hello! How can I assist you today?`.

Deploying the agent also creates a new workspace in the DigitalOcean Control Panel. The workspace is named the workspace name you specified previously and labeled `Managed by ADK`. Here you can [view and perform actions on agent deployments](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/build-agents-using-adk/#view-agents) and [run evaluations](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/build-agents-using-adk/#run-evaluations).

![Agent Development Kit deployment workspace](https://docs.digitalocean.com/screenshots/gradient-ai-platform/adk-workspace.fa9d00e8b9ce467437a441298699b93cc8fbc77e4f53a87c9c343fa487370413.png)Note
Agent deployments only include deployment timestamps and statuses, and have releases instead of versions. Automated rollback to a previous version is not available. To revert to a previous release of an agent deployment, you can re-deploy the agent code for that release to your environment.

### Troubleshoot Build or Deployment Failures

Builds or deployments can fail if you have any of the following issues:

- Python version other than 3.13.

- Missing `requirements.txt` file.

- The agent does not expose port `8080/run`. This likely means you have not defined an entrypoint correctly as the agent must pass a health check to finish deploying.

- Incorrect scope permissions for the DigitalOcean access token.

- Missing environment variables required by your agent in the `.env` file.


Check the Python version, the `requirements.txt` file, the `entrypoint` function defined, and all required environment variables in the `.env` file. Then, try building or deploying the agent again.

## View Traces and Logs

If you have previously deployed your agent, your agent automatically capture traces locally. LangGraph agents capture the intermediate input and outputs of the nodes while other agent frameworks capture the input and output to the agent itself. You can view these using:

```shell
gradient agent traces
```

You can view the agent’s logs using:

```shell
gradient agent logs
```

You can also [view the logs and traces in the control panel](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/build-agents-using-adk/#view-agents).

## View Agent Deployments in the DigitalOcean Control Panel

Agent deployments are organized in workspaces labeled `Managed by ADK`. These workspaces group agent deployments by development environments, such as production, staging, or test. However, you cannot move agent deployments from one workspace to another. To use the agent in another workspace, you must redeploy it to that workspace with the environment defined.

To view agent deployments, in the left menu of the control panel, click **Agent Platform**. In the **Workspaces** tab, click **+** to expand the workspace that has your agent deployment. Then, select an agent deployment to open its **Overview** page.

![Agent deployment in control panel](https://docs.digitalocean.com/screenshots/gradient-ai-platform/adk-deployment-control-panel.79e6ae37b48d16cc782d1332c3cad46b76e1d48e6d5358b83980c16def9f2ed7.png)

You can perform the following actions for the agent deployment:

- View agent insights and logs for the deployment in the **Observability** tab. See [View Agent Insights and Logs](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/view-agent-observability/) for more information.

- View the current and past agent deployments in the **Releases** tab. The release information includes the deployment timestamps and statuses.

- Create test cases, run evaluations, and view preview evaluation runs. See [Run Evaluations on Agent Deployments](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/build-agents-using-adk/#run-evaluations) for more information.

- Destroy the agent deployment. See [Destroy an Agent Deployment](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/build-agents-using-adk/#destroy-an-agent-deployment) for more information.


## Run Evaluations on Agent Deployments

You can create test cases and run evaluations on agent deployments that have deployed successfully at least once. The evaluation test cases belong to the ADK workspace and you can use them for any agent deployments within the workspace.

ADK agent evaluations use _judge_ input and output tokens. These tokens are used by the third-party LLM-as-judge to score the agent behavior against the metrics defined in the test case. These costs are waived during public preview.

First, create an evaluation dataset. The evaluation datasets for agent deployments are [similar to the evaluation datasets you use for agents built using the DigitalOcean Control Panel, CLI, or API](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/create-evaluation-datasets/), except the following differences:

- You must provide the full JSON payload in the `query` column. The string values must be properly escaped.

- You can use multi-field queries.

- For the `expected_response` column in a ground truth dataset, you can provide either a properly-escaped JSON payload or a string.


JSON Payload Examples

The following examples show some sample JSON payloads:

- Single field query

```js
ID,query
1,"{""prompt"": ""What's the weather in nyc?""}"
```

For ground truth dataset:

```js
ID,query,expected_response
1,"{"prompt": ""What's the weather in nyc?""}", "The weather in NYC is sunny with a high of 75°F."
```

- Multi field query

```js
ID,query
1,"{""prompt"": ""What's the weather in nyc?"", ""messages"": [""old message""]}"

```

For ground truth dataset:

```js
ID,query,expected_response
1,"{""prompt"": ""What's the weather in nyc?"", ""messages"": [""old message""]}", "The weather in NYC is sunny with a high of 75°F."
```

Then, run an evaluation:

```shell
gradient agent evaluate
```

When prompted, enter the following information:

- Path to the dataset CSV file

- Evaluation run name

- Metric categories

- Star metric and threshold


Once an evaluation run finishes, you can view the top-level results in the terminal. Click a link to open the agent’s **Evaluations** tab in the control panel and view the detailed results.

Alternatively, you can [create an evaluation dataset and run an evaluation in the control panel](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/evaluate-agents/).

To review how the agent responded to each prompt, click an evaluation run in the control panel and then scroll down the page to the **Scores** tab to view all scores for the entire trace.

Agent deployments also have a trace view where you can see the individual spans (decisions/stopping points) during the agent’s journey from input to output. Locate the prompt you want to review details for, select the **Queries** tab, and then click **Query details** for that prompt. Click on each span to see the scores specific to that span. Only certain metrics are associated with certain spans. For example:

- Input span shows the input the agent received along with any scores associated with the input. The scores shown depend on the metrics you selected - only some scores relate to the input.

- LLM span shows any scores associated with the LLM decision making at this point prior to any retrieval or tool calls.

- Tools called span provides scores for tool-call specific metrics, as well as which tool was called and what happened during that tool call.

- Knowledge base span shows what data was retrieved from which knowledge base, and scores related to each retrieved source, if relevant.

- Output span shows the agent output and any relevant metrics scores to the output.


## View Agent Deployments in the DigitalOcean Control Panel

Agent deployments are organized in workspaces labeled `Managed by ADK`. These workspaces group agent deployments by development environments, such as production, staging, or test. However, you cannot move agent deployments from one workspace to another. To use the agent in another workspace, you must redeploy it to that workspace with the environment defined.

To view agent deployments, in the left menu of the control panel, click **Agent Platform**. In the **Workspaces** tab, click **+** to expand the workspace that has your agent deployment. Then, select an agent deployment to open it’s **Overview** page.

You can perform the following actions for the agent deployment:

- View agent insights and logs for the deployment in the **Observability** tab. See [View Agent Insights and Logs](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/view-agent-observability/) for more information.

- View the current and past agent deployments in the **Releases** tab. The release information include the deployment timestamps and statuses.


- Destroy the agent deployment. See [Destroy an Agent Deployment](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/build-agents-using-adk/#destroy-an-agent-deployment) for more information.

## Destroy an Agent Deployment

You can destroy an agent deployment only using the DigitalOcean Control Panel. To destroy an agent deployment from the control panel, in the left menu, click **Agent Platform**. From the **Workspaces** tab, select the workspace that contains the agent you want to destroy and select the agent. Then, select **Destroy agent deployment** from the agent’s **Actions** menu. In the **Destroy Agent Deployment** window, type the agent’s name to confirm and then click **Destroy**.

Once all agent deployments within the workspace are destroyed, the workspace is also destroyed.

In this article...

- [Prerequisites](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/build-agents-using-adk/#prerequisites)
- [About Entrypoint](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/build-agents-using-adk/#entrypoint)
- [Install Agent Development Kit](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/build-agents-using-adk/#install-agent-development-kit)
- [Set Up a Project](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/build-agents-using-adk/#set-up-a-project)
- [Run and Test Agents Locally](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/build-agents-using-adk/#run-and-test-agents-locally)
- [Deploy and Test Your Agent](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/build-agents-using-adk/#deploy-and-test-your-agent)
  - [Troubleshoot Build or Deployment Failures](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/build-agents-using-adk/#troubleshoot-agent-deployment)
- [View Traces and Logs](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/build-agents-using-adk/#view-traces-and-logs)
- [View Agent Deployments in the DigitalOcean Control Panel](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/build-agents-using-adk/#view-agents)
- [Run Evaluations on Agent Deployments](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/build-agents-using-adk/#run-evaluations)
- [View Agent Deployments in the DigitalOcean Control Panel](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/build-agents-using-adk/#view-agents)
- [Destroy an Agent Deployment](https://docs.digitalocean.com/products/gradient-ai-platform/how-to/build-agents-using-adk/#destroy-an-agent-deployment)

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