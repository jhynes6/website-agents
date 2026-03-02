---
name: agent-query-optimizer
description: Optimize query for vector retrieval
model: sonnet
---
query
index = sb-knowledge-bases
namespace = {{client_slug}}

generate an optimized vector database query to retrieve all relevant information to answer {{prospect_reply}} from pinecone. 