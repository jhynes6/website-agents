"""
Central tool registry for agents.

This module is intentionally lightweight: it provides a consistent interface to
"tools" that an agent may call, with per-agent allowlisting.

Some tools are backed by:
- **MCP servers** (e.g. Bright Data, Supabase project ops, Firecrawl MCP)
- **Native Python clients already in this repo** (e.g. DigitalOcean, PineconeKBClient, FirecrawlClient)

How to use:
    from app.agent_tools import build_agent_tool_registry

    tools = build_agent_tool_registry(
        allowed_toolsets={"firecrawl", "pinecone", "digitalocean"},
        # optionally:
        mcp=MCPClientImpl(...),
    )
    tools["firecrawl.scrape"].call(url="https://example.com")
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, Optional, Protocol, Set


class MCPClient(Protocol):
    """
    Minimal interface an orchestrator can provide to let tools call MCP servers.

    We keep this intentionally generic: the runtime that hosts your agents can
    implement this however it wants (Cursor MCP, custom gateway, etc.).
    """

    def call(self, tool_name: str, params: Dict[str, Any]) -> Any: ...


@dataclass(frozen=True)
class AgentTool:
    """
    A callable tool with a stable name.

    `call` is a plain callable to keep agent-framework integration simple.
    """

    name: str
    description: str
    call: Callable[..., Any]


def _require_mcp(mcp: Optional[MCPClient], toolset: str) -> MCPClient:
    if mcp is None:
        raise RuntimeError(
            f"Toolset '{toolset}' requires an MCP client, but none was provided. "
            f"Pass mcp=... to build_agent_tool_registry()."
        )
    return mcp


# -----------------------------
# Bright Data (MCP-backed)
# -----------------------------


def _brightdata_tools(*, mcp: Optional[MCPClient]) -> Dict[str, AgentTool]:
    c = _require_mcp(mcp, "brightdata")

    return {
        "brightdata.search_engine": AgentTool(
            name="brightdata.search_engine",
            description="Scrape Google/Bing/Yandex SERP results via Bright Data.",
            call=lambda *, query, engine="google", cursor=None: c.call(
                "mcp_brightdata_search_engine",
                {"query": query, "engine": engine, **({"cursor": cursor} if cursor else {})},
            ),
        ),
        "brightdata.scrape_markdown": AgentTool(
            name="brightdata.scrape_markdown",
            description="Scrape a single URL and return extracted Markdown via Bright Data.",
            call=lambda *, url: c.call("mcp_brightdata_scrape_as_markdown", {"url": url}),
        ),
        "brightdata.scrape_html": AgentTool(
            name="brightdata.scrape_html",
            description="Scrape a single URL and return HTML via Bright Data.",
            call=lambda *, url: c.call("mcp_brightdata_scrape_as_html", {"url": url}),
        ),
        "brightdata.extract": AgentTool(
            name="brightdata.extract",
            description="Scrape + extract structured JSON from a URL via Bright Data.",
            call=lambda *, url, extraction_prompt=None: c.call(
                "mcp_brightdata_extract",
                {"url": url, **({"extraction_prompt": extraction_prompt} if extraction_prompt else {})},
            ),
        ),
    }


# -----------------------------
# Firecrawl (MCP-backed OR native client fallback)
# -----------------------------


def _firecrawl_tools(*, mcp: Optional[MCPClient]) -> Dict[str, AgentTool]:
    if mcp is not None:
        return {
            "firecrawl.search": AgentTool(
                name="firecrawl.search",
                description="Search the web via Firecrawl.",
                call=lambda **params: mcp.call("mcp_firecrawl-mcp_firecrawl_search", params),
            ),
            "firecrawl.scrape": AgentTool(
                name="firecrawl.scrape",
                description="Scrape a single URL via Firecrawl.",
                call=lambda **params: mcp.call("mcp_firecrawl-mcp_firecrawl_scrape", params),
            ),
            "firecrawl.map": AgentTool(
                name="firecrawl.map",
                description="Discover URLs on a site via Firecrawl map.",
                call=lambda **params: mcp.call("mcp_firecrawl-mcp_firecrawl_map", params),
            ),
            "firecrawl.crawl": AgentTool(
                name="firecrawl.crawl",
                description="Crawl a site via Firecrawl (returns operation id).",
                call=lambda **params: mcp.call("mcp_firecrawl-mcp_firecrawl_crawl", params),
            ),
        }

    # Native fallback uses our in-repo client for the most common operation (scrape).
    from .clients.firecrawl import firecrawl_client

    return {
        "firecrawl.scrape": AgentTool(
            name="firecrawl.scrape",
            description="Scrape a single URL via the in-repo Firecrawl HTTP client.",
            call=lambda *, url: firecrawl_client.scrape_url(url),
        ),
        "firecrawl.map": AgentTool(
            name="firecrawl.map",
            description="Map URLs on a site via the in-repo Firecrawl HTTP client.",
            call=lambda *, url, limit=500: firecrawl_client.map_urls(url, limit=int(limit)),
        ),
    }


# -----------------------------
# Pinecone (native client in this repo)
# -----------------------------


def _pinecone_tools(*, mcp: Optional[MCPClient]) -> Dict[str, AgentTool]:
    # Primary: native Pinecone wrapper already used by backend routes.
    from .clients.pinecone_client import pinecone_kb_client

    tools: Dict[str, AgentTool] = {
        "pinecone.search": AgentTool(
            name="pinecone.search",
            description="Search a client namespace in Pinecone (Records API) via the in-repo PineconeKBClient.",
            call=lambda *,
            client_slug,
            query,
            top_k=5,
            index_name=None,
            text_field="text",
            filter=None,
            fields=None: [
                h.__dict__
                for h in pinecone_kb_client.search(
                    client_slug=str(client_slug),
                    query=str(query),
                    top_k=int(top_k),
                    index_name=index_name,
                    text_field=str(text_field),
                    filter=filter,
                    fields=fields,
                )
            ],
        ),
        "pinecone.upsert_documents": AgentTool(
            name="pinecone.upsert_documents",
            description="Upsert documents into Pinecone for a client namespace via the in-repo PineconeKBClient.",
            call=lambda *,
            client_slug,
            documents,
            index_name=None,
            text_field="text",
            chunk_size=1200,
            overlap=200,
            chunker_name=None: pinecone_kb_client.upsert_documents(
                client_slug=str(client_slug),
                documents=list(documents or []),
                index_name=index_name,
                text_field=str(text_field),
                chunk_size=int(chunk_size),
                overlap=int(overlap),
                chunker_name=chunker_name,
            ),
        ),
    }

    # Optional: if an MCP Pinecone server exists in your runtime, you can call it too.
    # We expose a generic passthrough for convenience (does not assume a particular schema).
    if mcp is not None:
        tools["pinecone.mcp_call"] = AgentTool(
            name="pinecone.mcp_call",
            description="Call a Pinecone MCP tool by name (advanced; requires a Pinecone MCP server in your runtime).",
            call=lambda *, tool_name, **params: mcp.call(str(tool_name), dict(params)),
        )

    return tools


# -----------------------------
# DigitalOcean (native client in this repo)
# -----------------------------


def _digitalocean_tools(*, mcp: Optional[MCPClient]) -> Dict[str, AgentTool]:
    # NOTE: We rely on the existing in-repo DigitalOcean client implementation.
    # We are NOT adding new DO API endpoints here.
    from .clients.digital_ocean_client import do_client

    return {
        "digitalocean.list_knowledge_bases": AgentTool(
            name="digitalocean.list_knowledge_bases",
            description="List knowledge bases in DigitalOcean GenAI.",
            call=lambda: do_client.list_knowledge_bases(),
        ),
        "digitalocean.get_knowledge_base": AgentTool(
            name="digitalocean.get_knowledge_base",
            description="Get a DigitalOcean knowledge base by UUID.",
            call=lambda *, kb_uuid: do_client.get_knowledge_base(str(kb_uuid)),
        ),
        "digitalocean.list_agents": AgentTool(
            name="digitalocean.list_agents",
            description="List agents in DigitalOcean GenAI.",
            call=lambda: do_client.list_agents(),
        ),
        "digitalocean.get_agent": AgentTool(
            name="digitalocean.get_agent",
            description="Get a DigitalOcean agent by UUID.",
            call=lambda *, agent_uuid: do_client.get_agent(str(agent_uuid)),
        ),
        "digitalocean.create_agent": AgentTool(
            name="digitalocean.create_agent",
            description="Create a DigitalOcean agent (KB UUIDs optional).",
            call=lambda *,
            name,
            knowledge_base_uuids=None,
            instruction=None,
            project_id=None,
            region=None: do_client.create_agent(
                name=str(name),
                knowledge_base_uuids=list(knowledge_base_uuids or []),
                instruction=instruction,
                project_id=project_id,
                region=region,
            ),
        ),
    }


# -----------------------------
# Supabase Email Bison Project (MCP-backed)
# -----------------------------


def _supabase_email_bison_project_tools(*, mcp: Optional[MCPClient]) -> Dict[str, AgentTool]:
    c = _require_mcp(mcp, "supabase_email_bison_project")

    # These names map 1:1 to the MCP tool names available in this Cursor environment.
    return {
        "supabase.list_tables": AgentTool(
            name="supabase.list_tables",
            description="List tables in one or more schemas (Supabase MCP).",
            call=lambda *, schemas=None: c.call(
                "mcp_supabase_email_bison_project_list_tables",
                {**({"schemas": schemas} if schemas else {})},
            ),
        ),
        "supabase.execute_sql": AgentTool(
            name="supabase.execute_sql",
            description="Execute raw SQL (Supabase MCP). Prefer apply_migration for DDL.",
            call=lambda *, query: c.call("mcp_supabase_email_bison_project_execute_sql", {"query": query}),
        ),
        "supabase.apply_migration": AgentTool(
            name="supabase.apply_migration",
            description="Apply a migration (DDL) (Supabase MCP).",
            call=lambda *, name, query: c.call(
                "mcp_supabase_email_bison_project_apply_migration",
                {"name": name, "query": query},
            ),
        ),
        "supabase.get_logs": AgentTool(
            name="supabase.get_logs",
            description="Fetch Supabase logs by service (last 24h) (Supabase MCP).",
            call=lambda *, service: c.call("mcp_supabase_email_bison_project_get_logs", {"service": service}),
        ),
        "supabase.get_advisors": AgentTool(
            name="supabase.get_advisors",
            description="Fetch Supabase security/performance advisors (Supabase MCP).",
            call=lambda *, type: c.call("mcp_supabase_email_bison_project_get_advisors", {"type": type}),
        ),
        "supabase.get_project_url": AgentTool(
            name="supabase.get_project_url",
            description="Get Supabase project API URL (Supabase MCP).",
            call=lambda: c.call("mcp_supabase_email_bison_project_get_project_url", {}),
        ),
        "supabase.get_publishable_keys": AgentTool(
            name="supabase.get_publishable_keys",
            description="Get Supabase publishable API keys (Supabase MCP).",
            call=lambda: c.call("mcp_supabase_email_bison_project_get_publishable_keys", {}),
        ),
        "supabase.generate_typescript_types": AgentTool(
            name="supabase.generate_typescript_types",
            description="Generate TypeScript types for the project (Supabase MCP).",
            call=lambda: c.call("mcp_supabase_email_bison_project_generate_typescript_types", {}),
        ),
        "supabase.list_edge_functions": AgentTool(
            name="supabase.list_edge_functions",
            description="List Edge Functions (Supabase MCP).",
            call=lambda: c.call("mcp_supabase_email_bison_project_list_edge_functions", {}),
        ),
        "supabase.get_edge_function": AgentTool(
            name="supabase.get_edge_function",
            description="Get Edge Function contents by slug (Supabase MCP).",
            call=lambda *, function_slug: c.call(
                "mcp_supabase_email_bison_project_get_edge_function",
                {"function_slug": function_slug},
            ),
        ),
        "supabase.deploy_edge_function": AgentTool(
            name="supabase.deploy_edge_function",
            description="Deploy an Edge Function (Supabase MCP).",
            call=lambda **params: c.call("mcp_supabase_email_bison_project_deploy_edge_function", params),
        ),
        "supabase.list_migrations": AgentTool(
            name="supabase.list_migrations",
            description="List migrations (Supabase MCP).",
            call=lambda: c.call("mcp_supabase_email_bison_project_list_migrations", {}),
        ),
        "supabase.list_extensions": AgentTool(
            name="supabase.list_extensions",
            description="List DB extensions (Supabase MCP).",
            call=lambda: c.call("mcp_supabase_email_bison_project_list_extensions", {}),
        ),
        "supabase.list_branches": AgentTool(
            name="supabase.list_branches",
            description="List development branches (Supabase MCP).",
            call=lambda: c.call("mcp_supabase_email_bison_project_list_branches", {}),
        ),
        "supabase.create_branch": AgentTool(
            name="supabase.create_branch",
            description="Create a development branch (Supabase MCP).",
            call=lambda *, confirm_cost_id, name="develop": c.call(
                "mcp_supabase_email_bison_project_create_branch",
                {"confirm_cost_id": confirm_cost_id, "name": name},
            ),
        ),
        "supabase.merge_branch": AgentTool(
            name="supabase.merge_branch",
            description="Merge a development branch to production (Supabase MCP).",
            call=lambda *, branch_id: c.call(
                "mcp_supabase_email_bison_project_merge_branch",
                {"branch_id": branch_id},
            ),
        ),
        "supabase.rebase_branch": AgentTool(
            name="supabase.rebase_branch",
            description="Rebase a development branch on production (Supabase MCP).",
            call=lambda *, branch_id: c.call(
                "mcp_supabase_email_bison_project_rebase_branch",
                {"branch_id": branch_id},
            ),
        ),
        "supabase.reset_branch": AgentTool(
            name="supabase.reset_branch",
            description="Reset a development branch to a migration version (Supabase MCP).",
            call=lambda *, branch_id, migration_version=None: c.call(
                "mcp_supabase_email_bison_project_reset_branch",
                {**{"branch_id": branch_id}, **({"migration_version": migration_version} if migration_version else {})},
            ),
        ),
        "supabase.delete_branch": AgentTool(
            name="supabase.delete_branch",
            description="Delete a development branch (Supabase MCP).",
            call=lambda *, branch_id: c.call(
                "mcp_supabase_email_bison_project_delete_branch",
                {"branch_id": branch_id},
            ),
        ),
        "supabase.search_docs": AgentTool(
            name="supabase.search_docs",
            description="Search Supabase docs via MCP (GraphQL).",
            call=lambda *, graphql_query: c.call(
                "mcp_supabase_email_bison_project_search_docs",
                {"graphql_query": graphql_query},
            ),
        ),
    }


_TOOLSET_FACTORIES: Dict[str, Callable[[Optional[MCPClient]], Dict[str, AgentTool]]] = {
    "brightdata": lambda mcp: _brightdata_tools(mcp=mcp),
    "firecrawl": lambda mcp: _firecrawl_tools(mcp=mcp),
    "pinecone": lambda mcp: _pinecone_tools(mcp=mcp),
    "digitalocean": lambda mcp: _digitalocean_tools(mcp=mcp),
    "supabase_email_bison_project": lambda mcp: _supabase_email_bison_project_tools(mcp=mcp),
}


def build_agent_tool_registry(
    *,
    allowed_toolsets: Iterable[str],
    mcp: Optional[MCPClient] = None,
) -> Dict[str, AgentTool]:
    """
    Build a flat {tool_name: AgentTool} dict for an agent, based on allowlisted toolsets.

    Example:
        tools = build_agent_tool_registry(allowed_toolsets={"firecrawl", "pinecone"})
        tools["pinecone.search"].call(client_slug="acme", query="pricing")
    """
    allow: Set[str] = {str(s).strip() for s in allowed_toolsets if str(s).strip()}
    out: Dict[str, AgentTool] = {}

    for toolset in sorted(allow):
        factory = _TOOLSET_FACTORIES.get(toolset)
        if not factory:
            raise ValueError(
                f"Unknown toolset '{toolset}'. Supported: {sorted(_TOOLSET_FACTORIES.keys())}"
            )
        out.update(factory(mcp))

    return out


