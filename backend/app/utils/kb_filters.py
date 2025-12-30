"""
Client-side filtering utilities for Knowledge Base retrieval results.

We parse YAML frontmatter embedded in chunk text to enable filtering by
content_type, document_source, etc. (Legacy pipelines used frontmatter to
carry metadata alongside Markdown content.)
"""

import re
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass


@dataclass
class FilteredChunk:
    """A KB chunk with parsed metadata from YAML frontmatter."""
    original_chunk: Any  # The original Gradient SDK chunk object
    metadata: Dict[str, Any]  # Original KB metadata
    yaml_metadata: Dict[str, str]  # Parsed YAML frontmatter
    text_content: str  # The chunk's text content
    
    def __getattr__(self, name):
        """Proxy attribute access to the original chunk."""
        return getattr(self.original_chunk, name)


def parse_yaml_frontmatter(text: str) -> Dict[str, str]:
    """
    Parse YAML frontmatter from parent_chunk_text.
    
    Handles two formats:
    1. Multi-line YAML (newline-separated):
        client_slug: wendt-partners
        url: https://example.com
        content_type: homepage
        
    2. Single-line YAML (space-separated):
        client_slug: wendt-partners url: https://example.com content_type: homepage
    
    Args:
        text: The parent_chunk_text field content
        
    Returns:
        Dictionary of YAML key-value pairs
    """
    yaml_data = {}
    
    if not text:
        return yaml_data
    
    # Get the first line
    first_line = text.split('\n')[0] if '\n' in text else text
    
    # Known YAML keys in our documents (in order they typically appear)
    known_keys = ['client_slug', 'url', 'title', 'content_type', 'document_source']
    
    # Try single-line format by finding positions of known keys
    # Build a map of positions
    key_positions = []
    for key in known_keys:
        # Look for " key:" or "^key:" (start of line or after space)
        pattern = rf'(?:^|\s)({key})\s*:\s*'
        match = re.search(pattern, first_line, re.IGNORECASE)
        if match:
            key_positions.append((match.start(1), match.end(), key))
    
    # Sort by position
    key_positions.sort()
    
    # Extract values between key positions
    for i, (start, end, key) in enumerate(key_positions):
        value_start = end
        
        # Value ends at the next key or end of line
        if i + 1 < len(key_positions):
            value_end = key_positions[i + 1][0]
        else:
            value_end = len(first_line)
        
        value = first_line[value_start:value_end].strip()
        yaml_data[key] = value
    
    # If we found YAML on first line, return it
    if yaml_data:
        return yaml_data
    
    # Otherwise, try multi-line format
    lines = text.split('\n')
    
    for line in lines:
        # Stop at first blank line
        if not line.strip():
            break
        
        # Parse key: value pairs
        match = re.match(r'^([a-z_][a-z0-9_-]*)\s*:\s*(.+)$', line.strip(), re.IGNORECASE)
        if match:
            key = match.group(1).strip()
            value = match.group(2).strip()
            yaml_data[key] = value
        else:
            # If we hit a line that doesn't match, stop parsing
            if yaml_data:  # Only stop if we've found some YAML already
                break
    
    return yaml_data


def filter_chunks_by_yaml(
    chunks: List[Any],
    content_type: Optional[str] = None,
    document_source: Optional[str] = None,
    custom_filter: Optional[Callable[[Dict[str, str]], bool]] = None,
    preserve_order: bool = True
) -> List[FilteredChunk]:
    """
    Filter KB chunks by parsing YAML frontmatter from parent_chunk_text.
    
    Args:
        chunks: List of chunks from Gradient retrieve.documents()
        content_type: Filter by content_type field (e.g., "case_studies", "homepage")
        document_source: Filter by document_source field (e.g., "website", "intake_form")
        custom_filter: Custom filter function that takes yaml_metadata dict and returns bool
        preserve_order: If True, maintains original chunk order (by relevance score)
        
    Returns:
        List of FilteredChunk objects that match the criteria
        
    Example:
        # Filter for case studies from website only
        filtered = filter_chunks_by_yaml(
            chunks,
            content_type="case_studies",
            document_source="website"
        )
        
        # Custom filter for multiple content types
        filtered = filter_chunks_by_yaml(
            chunks,
            custom_filter=lambda meta: meta.get("content_type") in ["case_studies", "testimonials"]
        )
    """
    filtered_chunks = []
    
    for chunk in chunks:
        # Get parent_chunk_text from metadata
        parent_text = chunk.metadata.get('parent_chunk_text', '')
        
        # Parse YAML frontmatter
        yaml_metadata = parse_yaml_frontmatter(parent_text)
        
        # Apply filters
        matches = True
        
        if content_type and yaml_metadata.get('content_type') != content_type:
            matches = False
        
        if document_source and yaml_metadata.get('document_source') != document_source:
            matches = False
        
        if custom_filter and not custom_filter(yaml_metadata):
            matches = False
        
        # If all filters pass, add to results
        if matches:
            filtered_chunk = FilteredChunk(
                original_chunk=chunk,
                metadata=chunk.metadata,
                yaml_metadata=yaml_metadata,
                text_content=getattr(chunk, 'text_content', '')
            )
            filtered_chunks.append(filtered_chunk)
    
    return filtered_chunks


def retrieve_with_yaml_filter(
    client,
    knowledge_base_id: str,
    query: str,
    num_results: int = 20,
    content_type: Optional[str] = None,
    document_source: Optional[str] = None,
    custom_filter: Optional[Callable[[Dict[str, str]], bool]] = None,
    max_filtered_results: Optional[int] = None,
    **retrieve_kwargs
) -> List[FilteredChunk]:
    """
    Retrieve from KB and filter by YAML frontmatter in one call.
    
    This is a convenience wrapper that:
    1. Retrieves extra results from the KB (since we'll filter some out)
    2. Applies client-side YAML filtering
    3. Returns up to max_filtered_results
    
    Args:
        client: Gradient client instance
        knowledge_base_id: KB UUID
        query: Search query
        num_results: Number of results to retrieve from KB (before filtering)
        content_type: Filter by content_type
        document_source: Filter by document_source
        custom_filter: Custom filter function
        max_filtered_results: Maximum results to return after filtering (None = all)
        **retrieve_kwargs: Additional kwargs for client.retrieve.documents()
        
    Returns:
        List of FilteredChunk objects
        
    Example:
        from gradient import Gradient
        from app.utils.kb_filters import retrieve_with_yaml_filter
        
        client = Gradient(access_token=token)
        
        # Get case studies only
        results = retrieve_with_yaml_filter(
            client,
            kb_uuid,
            query="customer success",
            num_results=30,  # Retrieve 30 to filter from
            content_type="case_studies",
            max_filtered_results=5  # Return top 5 after filtering
        )
    """
    # Retrieve from KB
    response = client.retrieve.documents(
        knowledge_base_id=knowledge_base_id,
        num_results=num_results,
        query=query,
        **retrieve_kwargs
    )
    
    # Filter by YAML
    filtered = filter_chunks_by_yaml(
        response.results,
        content_type=content_type,
        document_source=document_source,
        custom_filter=custom_filter,
        preserve_order=True
    )
    
    # Limit results if requested
    if max_filtered_results is not None:
        filtered = filtered[:max_filtered_results]
    
    return filtered


def get_available_content_types(chunks: List[Any]) -> Dict[str, int]:
    """
    Analyze chunks and return a count of content_types.
    
    Useful for understanding what content types are in your results.
    
    Args:
        chunks: List of chunks from KB
        
    Returns:
        Dict mapping content_type to count
        
    Example:
        response = client.retrieve.documents(...)
        types = get_available_content_types(response.results)
        # {'case_studies': 5, 'homepage': 2, 'blogs_resources': 8}
    """
    type_counts = {}
    
    for chunk in chunks:
        parent_text = chunk.metadata.get('parent_chunk_text', '')
        yaml_metadata = parse_yaml_frontmatter(parent_text)
        content_type = yaml_metadata.get('content_type', 'unknown')
        
        type_counts[content_type] = type_counts.get(content_type, 0) + 1
    
    return type_counts


def get_available_document_sources(chunks: List[Any]) -> Dict[str, int]:
    """
    Analyze chunks and return a count of document_sources.
    
    Args:
        chunks: List of chunks from KB
        
    Returns:
        Dict mapping document_source to count
    """
    source_counts = {}
    
    for chunk in chunks:
        parent_text = chunk.metadata.get('parent_chunk_text', '')
        yaml_metadata = parse_yaml_frontmatter(parent_text)
        doc_source = yaml_metadata.get('document_source', 'unknown')
        
        source_counts[doc_source] = source_counts.get(doc_source, 0) + 1
    
    return source_counts

