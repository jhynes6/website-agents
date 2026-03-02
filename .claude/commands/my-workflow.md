---
description: my-workflow
allowed-tools: Bash,BashOutput,Edit,ExitPlanMode,Glob,Grep,KillShell,MCPSearch,NotebookEdit,Read,Skill,SlashCommand,Task,TodoWrite,WebFetch,WebSearch,Write,AskUserQuestion
model: sonnet
---
```mermaid
flowchart TD
    start_node_default([Start])
    prompt_message_input[{{client_slug}}]
    agent_query_optimizer[agent-query-optimizer]
    agent_result_formatter[agent-result-formatter]
    end_node_default([End])
    mcp_1769522712865[[MCP Task: Find all relevant info...]]

    prompt_message_input --> agent_query_optimizer
    agent_result_formatter --> end_node_default
    agent_query_optimizer --> mcp_1769522712865
    mcp_1769522712865 --> agent_result_formatter
    start_node_default --> prompt_message_input
```

## Workflow Execution Guide

Follow the Mermaid flowchart above to execute the workflow. Each node type has specific execution methods as described below.

### Execution Methods by Node Type

- **Rectangle nodes**: Execute Sub-Agents using the Task tool
- **Diamond nodes (AskUserQuestion:...)**: Use the AskUserQuestion tool to prompt the user and branch based on their response
- **Diamond nodes (Branch/Switch:...)**: Automatically branch based on the results of previous processing (see details section)
- **Rectangle nodes (Prompt nodes)**: Execute the prompts described in the details section below

## MCP Tool Nodes

#### mcp_1769522712865(MCP Auto-Selection) - AI Tool Selection Mode

<!-- MCP_NODE_METADATA: {"mode":"aiToolSelection","serverId":"pinecone","userIntent":"Find all relevant information related to the query. Only search index = 'sb-knowledge-bases' and namespace = {{client_slug}}","availableTools":[]} -->

**MCP Server**: pinecone

**Validation Status**: valid

**User Intent (Natural Language Task Description)**:

```
Find all relevant information related to the query. Only search index = 'sb-knowledge-bases' and namespace = {{client_slug}}
```

**Available Tools**: (snapshot not available, query server at runtime)

**Execution Method**:

Claude Code should analyze the task description above and select the most appropriate tool from the available tools list. Then, determine the appropriate parameter values for the selected tool based on the task requirements. If the available tools list is empty, query the MCP server at runtime to get the current list of tools.

### Prompt Node Details

#### prompt_message_input({{client_slug}})

```
{{client_slug}}
{{prospect_reply}}
```

**Available variables:**
- `{{prospectMessage}}`: [object Object]
