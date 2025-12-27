---
url: "https://docs.digitalocean.com/products/gradient-ai-platform/concepts/context-management/"
title: "Best Practices for Context Management when Generating Code with AI Agents | DigitalOcean Documentation"
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
- Context Management Best Practices

[Give Feedback](https://ideas.digitalocean.com/documentation)

# Best Practices for Context Management when Generating Code with AI Agents

Validated on 6 Aug 2025 • Last edited on 15 Aug 2025

DigitalOcean Gradient™ AI Platform lets you build fully-managed AI agents with knowledge bases for retrieval-augmented generation, multi-agent routing, guardrails, and more, or use serverless inference to make direct requests to popular foundation models.

A large language model’s (LLM) _context_ is data that it uses when processing requests to generate more relevant responses. For example, an AI agent’s context can include can include data from the end user (like their prompt or the preceding conversation) and data from its configuration (like relevant documentation or available tool calls).

LLMs work best with focused, relevant information. Poor context can mean:

- **Insufficient context**, or too little information. This may cause AI agents to hallucinate, increasing the likelihood of low quality responses with nonexistent APIs and packages, incorrect configurations, or generic boilerplate code.
- **Context overflow**, or too much information. Context overflow can cause AI agents to hit token limits and provide unfocused responses. [Chroma’s research on context rot](https://research.trychroma.com/context-rot) discusses how context degradation affects AI model performance over time.

We recommend the following structured approach for effective context management:

1. Start with a comprehensive [product requirements document (PRD)](https://en.wikipedia.org/wiki/Product_requirements_document).
2. Divide the PRD into focused tasks.
3. Execute each task one at a time with new context.
4. Maintain a focused working context
5. Avoid mixing requirements, files, and goals
6. Use `llms.txt`
Following these steps for context management can improve the quality of AI-generated code.

## Start with a Clear Product Requirements Document (PRD)

Begin every project with a focused PRD that defines the following:

```markdown
# Task Management App PRD

## Objective
Create a simple task management application for small teams.

## Core Features
- User authentication (email/password)
- Create, edit, delete tasks
- Assign tasks to team members
- Mark tasks as complete

## Technical Requirements
- Next.js frontend
- PostgreSQL database
- Deploy to DigitalOcean App Platform
- Support up to 50 concurrent users

## Out of Scope
- Real-time collaboration
- File attachments
- Advanced reporting
- Mobile app
```

## Break Large Tasks into Focused Issues

Next, create specific, actionable issues based on the PRD.

The following prompt is not specific and leads to poor results:

```markdown
Build a complete e-commerce platform with user management, product catalog,
shopping cart, payment processing, order management, inventory tracking, admin
dashboard, analytics, and mobile responsiveness.
```

Instead, prompt with one task at a time, including all relevant requirements and specifications:

```markdown
Create a PostgreSQL database schema for product catalog with the following
entities:

- Products (id, name, description, price, stock_quantity, created_at)
- Categories (id, name, slug, description)
- Product_Categories (product_id, category_id)

Include appropriate indexes and constraints.
```

## Work Issue-by-Issue with Focused Prompts

Process one issue at a time with clear, specific instructions:

```markdown
## Current Task: User Authentication API

### Context
- Next.js application using App Router
- PostgreSQL database already configured
- Using bcrypt for password hashing
- JWT tokens for session management

### Requirements
- POST /api/auth/register endpoint
- POST /api/auth/login endpoint
- Input validation and error handling
- Password strength requirements

### Constraints
- Follow existing project structure in /app/api/
- Use the database connection pattern from /lib/db.js
- Return consistent JSON error format
```

## Maintain Focused Working Context

Different tasks require different types of context. For authentication tasks, you need user management patterns and security libraries. For database work, you need schema designs and ORM patterns. For API development, you need routing conventions and error handling approaches. Keep your working context tailored to the specific task at hand.

You can provide a user guide or documentation chapter as context. Alternatively, you can use Model Context Protocol (MCP) tools like [Context 7](https://context7.com/) to automatically fetch relevant context based on your current task.

Consider writing test cases first. Tests help AI agents understand your expected behavior and generate more accurate implementations.

**Context Guidelines:**

- **One Task Focus**: Don’t mix authentication with database schema changes
- **Relevant Code Only**: Include files directly related to current work
- **Clear Objectives**: State exactly what you want accomplished
- **Start Fresh**: Begin new sessions to clear context when switching between major features

## Avoid Mixing Requirements, Files, and Goals

When working with language models, providing focused and relevant context helps generate accurate and useful responses. Instead of mixing goals and code, isolate one task at a time and include only the necessary details.

The following is an example of an unfocused prompt that mixes unrelated file context with requirements and goals:

```markdown
Here's my entire codebase (50 files), I want to add user authentication, also
fix the database performance issues, and can you also help me deploy this to
production, plus I'm thinking about adding real-time features later, what do you
think about WebSockets vs Server-Sent Events?
```

This prompt is focused on one task, includes relevant code only, and includes specific requirements:

```markdown
I need to add JWT-based authentication to my Next.js API. Here's the current
user model and database connection pattern:

[Relevant code files only]

Create login and register endpoints that:
1. Validate input data
2. Hash passwords with bcrypt
3. Return JWT tokens
4. Follow the existing error handling pattern
```

## DigitalOcean App Platform `llms.txt`

[`llms.txt`](https://llmstxt.org/) is a standardized file format designed to provide website contents in a format that is convenient for LLMs. An `llms.txt` file for App Platform is available at [`https://docs.digitalocean.com/products/app-platform/llms.txt`](https://docs.digitalocean.com/products/app-platform/llms.txt).

This file provides a comprehensive overview of the App Platform documentation including features, sample apps, best practices, and support articles.

To use the `llms.txt` file, download it and place it in your project root so AI agents can reference it.

### Benefits of Using this `llms.txt` File

1. **Accurate Platform Context**: AI agents get precise information about App Platform capabilities
2. **Reduces Hallucinations**: Prevents AI from inventing non-existent APIs or features
3. **Better Architecture Decisions**: AI suggests appropriate App Platform components for your use case
4. **Consistent Documentation References**: AI provides links to actual DigitalOcean documentation

## Conclusion

Effective context management is a skill that improves with practice. Follow these guidelines and use the DigitalOcean App Platform `llms.txt` file to get better results from AI agents and spend less time debugging generated code.

In this article...

- [Start with a Clear Product Requirements Document (PRD)](https://docs.digitalocean.com/products/gradient-ai-platform/concepts/context-management/#start-with-a-clear-product-requirements-document-prd)
- [Break Large Tasks into Focused Issues](https://docs.digitalocean.com/products/gradient-ai-platform/concepts/context-management/#break-large-tasks-into-focused-issues)
- [Work Issue-by-Issue with Focused Prompts](https://docs.digitalocean.com/products/gradient-ai-platform/concepts/context-management/#work-issue-by-issue-with-focused-prompts)
- [Maintain Focused Working Context](https://docs.digitalocean.com/products/gradient-ai-platform/concepts/context-management/#maintain-focused-working-context)
- [Avoid Mixing Requirements, Files, and Goals](https://docs.digitalocean.com/products/gradient-ai-platform/concepts/context-management/#avoid-mixing-requirements-files-and-goals)
- [DigitalOcean App Platform `llms.txt`](https://docs.digitalocean.com/products/gradient-ai-platform/concepts/context-management/#digitalocean-app-platform-llmstxt)
  - [Benefits of Using this `llms.txt` File](https://docs.digitalocean.com/products/gradient-ai-platform/concepts/context-management/#benefits-of-using-this-llmstxt-file)
- [Conclusion](https://docs.digitalocean.com/products/gradient-ai-platform/concepts/context-management/#conclusion)

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