
from mcp.server.fastmcp import FastMCP
from core.mem0_config import create_memory
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP Server
mcp = FastMCP("Home AI Memory Stack - Official Mem0")

# Initialize official Mem0 Memory
try:
    memory = create_memory()
    logger.info("✅ Official Mem0 Memory initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize Mem0: {e}")
    memory = None

def extract_metadata(content: str) -> dict:
    """
    Extract categories and keywords from content using local Ollama LLM.
    
    Args:
        content: The text content to analyze.
    Returns:
        Dictionary with 'category' and 'keywords' fields.
    """
    try:
        import requests
        import json
        
        prompt = f"""Analyze this text and extract metadata. Return ONLY valid JSON with no explanation:

Text: "{content}"

Return JSON format:
{{
  "category": "single best-fit category from: health, work, personal, preferences, knowledge, events, other",
  "keywords": ["keyword1", "keyword2", "keyword3"]
}}

JSON only:"""
        
        # Call Ollama API with FunctionGemma - Google's tiny function-calling specialist
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "functiongemma",  # 270M params, purpose-built for JSON extraction (Dec 2025)
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1}
            },
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            response_text = result.get('response', '').strip()
            
            # Try to extract JSON from response
            # Sometimes models add text before/after JSON
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            
            if start != -1 and end > start:
                json_str = response_text[start:end]
                metadata = json.loads(json_str)
                
                # Validate and clean
                if 'category' in metadata and 'keywords' in metadata:
                    # Ensure keywords is a list of strings
                    if isinstance(metadata['keywords'], list):
                        metadata['keywords'] = [str(k) for k in metadata['keywords'][:5]]  # Max 5
                    return metadata
        
        logger.warning(f"Failed to extract metadata, using defaults")
    except Exception as e:
        logger.error(f"Error in extract_metadata: {e}")
    
    # Fallback: return minimal metadata
    return {"category": "other", "keywords": []}

@mcp.tool()
def remember(content: str, user_id: str = "user", metadata: dict = None, auto_categorize: bool = True) -> str:
    """
    Save a piece of knowledge, fact, or memory using official Mem0.
    The LLM will automatically extract facts and build relationships.
    Optionally auto-categorizes content for better organization.
    
    Args:
        content: The text content to remember.
        user_id: The ID of the user (default: 'user').
        metadata: Optional dictionary of extra data.
        auto_categorize: Automatically extract categories/keywords (default: True).
    """
    if not memory:
        return "❌ Memory system is offline."
    
    try:
        # Auto-categorize if enabled and no metadata provided
        if auto_categorize and not metadata:
            logger.info("Auto-categorizing content...")
            metadata = extract_metadata(content)
            logger.info(f"Extracted metadata: {metadata}")
        
        messages = [{"role": "user", "content": content}]
        result = memory.add(messages, user_id=user_id, metadata=metadata or {})
        
        # Include metadata in response if auto-categorized
        response = f"✅ Saved {len(result) if isinstance(result, list) else 1} memories"
        if auto_categorize and metadata:
            response += f" (category: {metadata.get('category', 'N/A')})"
        return response
    except Exception as e:
        logger.error(f"Error saving memory: {e}")
        return f"❌ Failed to save: {str(e)}"

@mcp.tool()
def recall(query: str, user_id: str = "user", limit: int = 5, filters: dict = None) -> str:
    """
    Search for relevant memories using semantic + graph retrieval.
    Supports optional advanced filtering with logical operators.
    
    Args:
        query: The semantic search query.
        user_id: The ID of the user (default: 'user').
        limit: Maximum number of results to return.
        filters: Optional filter dict with operators (AND/OR/NOT, eq/ne/gt/lt/contains).
                 Example: {"metadata.category": {"eq": "health"}}
    """
    if not memory:
        return "❌ Memory system is offline."
    
    try:
        # Pass filters if provided
        kwargs = {"user_id": user_id, "limit": limit}
        if filters:
            kwargs["filters"] = filters
            
        results = memory.search(query, **kwargs)
        
        if not results.get("results"):
            return "No memories found matching that query."
        
        formatted = "\n\n".join([
            f"**Memory {i+1}** (score: {r.get('score', 0):.3f})\n{r['memory']}"
            for i, r in enumerate(results["results"])
        ])
        return formatted
    except Exception as e:
        logger.error(f"Error recalling memory: {e}")
        return f"❌ Failed to recall: {str(e)}"

@mcp.tool()
def get_all_memories(user_id: str = "user") -> str:
    """
    Retrieve all memories for a specific user.
    """
    if not memory:
        return "❌ Memory system is offline."
    
    try:
        results = memory.get_all(user_id=user_id)
        
        if not results:
            return "No memories stored for this user."
        
        formatted = "\n\n".join([
            f"**Memory {i+1}**\n{r['memory']}"
            for i, r in enumerate(results)
        ])
        return f"Found {len(results)} memories:\n\n{formatted}"
    except Exception as e:
        logger.error(f"Error getting memories: {e}")
        return f"❌ Failed: {str(e)}"

@mcp.tool()
def get_memory_history(memory_id: str) -> str:
    """
    Get the version history of a specific memory.
    Shows how the memory has evolved over time.
    
    Args:
        memory_id: The unique identifier of the memory.
    """
    if not memory:
        return "❌ Memory system is offline."
    
    try:
        history = memory.history(memory_id)
        
        if not history:
            return f"No history found for memory '{memory_id}'."
        
        # Format the history timeline
        formatted = f"**Memory History for {memory_id}**\n"
        formatted += "━" * 40 + "\n\n"
        
        for i, entry in enumerate(reversed(history)):
            version_num = len(history) - i
            current_tag = " [Current]" if i == 0 else ""
            
            # Extract relevant fields
            event = entry.get('event', 'UPDATE')
            memory_text = entry.get('memory', entry.get('new_memory', 'N/A'))
            timestamp = entry.get('created_at', entry.get('timestamp', 'Unknown'))
            
            formatted += f"**v{version_num}{current_tag}** - {timestamp}\n"
            formatted += f"  {memory_text}\n\n"
        
        return formatted.strip()
    except Exception as e:
        logger.error(f"Error getting memory history: {e}")
        return f"❌ Failed to retrieve history: {str(e)}"

@mcp.tool()
def get_memory(memory_id: str, user_id: str = "user") -> str:
    """
    Get a single memory by its unique ID.
    
    Args:
        memory_id: The unique identifier of the memory to retrieve.
        user_id: The ID of the user (default: 'user').
    """
    if not memory:
        return "❌ Memory system is offline."
    
    try:
        result = memory.get(memory_id, user_id=user_id)
        
        if not result:
            return f"Memory '{memory_id}' not found."
        
        # Format the memory with metadata
        formatted = f"**Memory ID**: {memory_id}\n"
        formatted += f"**Content**: {result.get('memory', 'N/A')}\n"
        
        # Add metadata if available
        if result.get('metadata'):
            formatted += f"**Metadata**: {result['metadata']}\n"
        if result.get('created_at'):
            formatted += f"**Created**: {result['created_at']}\n"
        if result.get('updated_at'):
            formatted += f"**Updated**: {result['updated_at']}\n"
            
        return formatted
    except Exception as e:
        logger.error(f"Error getting memory: {e}")
        return f"❌ Failed to retrieve memory: {str(e)}"

@mcp.tool()
def update_memory(memory_id: str, content: str, user_id: str = "user") -> str:
    """
    Update an existing memory by its ID.
    
    Args:
        memory_id: The ID of the memory to update.
        content: The new content for the memory.
        user_id: The ID of the user (default: 'user').
    """
    if not memory:
        return "❌ Memory system is offline."
    
    try:
        memory.update(memory_id=memory_id, data=content, user_id=user_id)
        return f"✅ Updated memory {memory_id}"
    except Exception as e:
        logger.error(f"Error updating memory: {e}")
        return f"❌ Failed to update: {str(e)}"

@mcp.tool()
def delete_memory(memory_id: str, user_id: str = "user") -> str:
    """
    Delete a specific memory by its ID.
    
    Args:
        memory_id: The ID of the memory to delete.
        user_id: The ID of the user (default: 'user').
    """
    if not memory:
        return "❌ Memory system is offline."
    
    try:
        memory.delete(memory_id=memory_id, user_id=user_id)
        return f"✅ Deleted memory {memory_id}"
    except Exception as e:
        logger.error(f"Error deleting memory: {e}")
        return f"❌ Failed to delete: {str(e)}"

@mcp.tool()
def delete_all_memories(user_id: str = "user") -> str:
    """
    Delete all memories for a specific user.
    
    Args:
        user_id: The ID of the user (default: 'user').
    """
    if not memory:
        return "❌ Memory system is offline."
    
    try:
        memory.delete_all(user_id=user_id)
        return f"✅ Deleted all memories for user: {user_id}"
    except Exception as e:
        logger.error(f"Error deleting all memories: {e}")
        return f"❌ Failed to delete all: {str(e)}"

@mcp.tool()
def list_entities(user_id: str = "user", limit: int = 100) -> str:
    """
    List all entities (nodes) from the knowledge graph for a user.
    
    Args:
        user_id: The ID of the user (default: 'user').
        limit: Maximum number of entities to return (default: 100).
    """
    if not memory:
        return "❌ Memory system is offline."
    
    try:
        # Use memory's graph store to access Neo4j directly
        from mem0.configs.graph_store import Neo4jGraphStore
        
        # Access the graph store from memory instance
        if not hasattr(memory, 'graph') or not memory.graph:
            return "❌ Graph store not available."
        
        # Direct Neo4j query to get entities
        query = """
        MATCH (n)
        WHERE n.user_id = $user_id
        RETURN n.name as name, labels(n) as type, 
               n.created_at as created, id(n) as node_id
        LIMIT $limit
        """
        
        # Execute query through the graph store
        with memory.graph.driver.session() as session:
            result = session.run(query, user_id=user_id, limit=limit)
            entities = list(result)
        
        if not entities:
            return "No entities found in the knowledge graph."
        
        formatted_entities = []
        for entity in entities:
            name = entity.get('name', 'Unknown')
            types = entity.get('type', [])
            node_id = entity.get('node_id', 'N/A')
            type_str = ', '.join(types) if types else 'Unknown'
            formatted_entities.append(f"• **{name}** (Type: {type_str}, ID: {node_id})")
        
        return f"Found {len(entities)} entities:\n\n" + "\n".join(formatted_entities)
    except Exception as e:
        logger.error(f"Error listing entities: {e}")
        return f"❌ Failed to list entities: {str(e)}"

@mcp.tool()
def delete_entities_by_name(entity_name: str, user_id: str = "user") -> str:
    """
    Delete specific entities from the knowledge graph by name.
    
    Args:
        entity_name: The name of the entity to delete.
        user_id: The ID of the user (default: 'user').
    """
    if not memory:
        return "❌ Memory system is offline."
    
    try:
        if not hasattr(memory, 'graph') or not memory.graph:
            return "❌ Graph store not available."
        
        # Query to delete entity and its relationships
        query = """
        MATCH (n {name: $entity_name, user_id: $user_id})
        DETACH DELETE n
        RETURN count(n) as deleted_count
        """
        
        with memory.graph.driver.session() as session:
            result = session.run(query, entity_name=entity_name, user_id=user_id)
            record = result.single()
            deleted_count = record['deleted_count'] if record else 0
        
        if deleted_count > 0:
            return f"✅ Deleted {deleted_count} entity/entities named '{entity_name}'"
        else:
            return f"No entity found with name '{entity_name}'"
            
    except Exception as e:
        logger.error(f"Error deleting entity: {e}")
        return f"❌ Failed to delete entity: {str(e)}"

@mcp.tool()
def get_youtube_transcript(video_url: str, languages: str = "en", include_timestamps: bool = False) -> str:
    """
    Get the transcript from a YouTube video.
    Supports both manual and auto-generated transcripts.
    
    Args:
        video_url: YouTube video URL or video ID (e.g., 'https://youtube.com/watch?v=VIDEO_ID' or just 'VIDEO_ID')
        languages: Comma-separated language codes to try (default: 'en'). Example: 'en,es,fr'
        include_timestamps: If True, include timestamps with each segment (default: False)
    
    Returns:
        The video transcript as text, optionally with timestamps
    
    Examples:
        get_youtube_transcript("dQw4w9WgXcQ")
        get_youtube_transcript("https://youtube.com/watch?v=dQw4w9WgXcQ", languages="en,es")
        get_youtube_transcript("VIDEO_ID", include_timestamps=True)
    """
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
        
        # Extract video ID from URL if needed
        video_id = video_url
        if 'youtu.be/' in video_url:
            video_id = video_url.split('youtu.be/')[1].split('?')[0]
        elif 'watch?v=' in video_url:
            video_id = video_url.split('watch?v=')[1].split('&')[0]
        
        # Parse language codes
        lang_list = [lang.strip() for lang in languages.split(',')]
        
        # Fetch transcript
        api = YouTubeTranscriptApi()
        transcript = api.fetch(video_id, lang_list)
        
        if not transcript:
            return f"❌ No transcript found for video: {video_id}"
        
        # Format output
        if include_timestamps:
            formatted = []
            for segment in transcript:
                timestamp = f"[{segment.start:.2f}s]"
                formatted.append(f"{timestamp} {segment.text}")
            result = "\n".join(formatted)
        else:
            result = " ".join([segment.text for segment in transcript])
        
        # Add metadata
        char_count = len(result)
        segment_count = len(transcript)
        duration = transcript[-1].start + transcript[-1].duration if transcript else 0
        
        header = f"📝 **YouTube Transcript**\n"
        header += f"Video ID: {video_id}\n"
        header += f"Segments: {segment_count} | Duration: ~{duration:.0f}s | Characters: {char_count}\n"
        header += "─" * 50 + "\n\n"
        
        return header + result
        
    except TranscriptsDisabled:
        return f"❌ Transcripts are disabled for this video: {video_id}"
    except NoTranscriptFound:
        return f"❌ No transcript found for video: {video_id} in languages: {languages}"
    except Exception as e:
        logger.error(f"Error fetching YouTube transcript: {e}")
        return f"❌ Failed to fetch transcript: {str(e)}"

@mcp.tool()
def get_webpage_content(url: str, extract_text_only: bool = True, max_length: int = 50000) -> str:
    """
    Fetch and extract content from any webpage.
    Perfect for reading articles, documentation, or any web content.
    
    Args:
        url: The URL of the webpage to fetch
        extract_text_only: If True, extract clean text. If False, return raw HTML (default: True)
        max_length: Maximum characters to return (default: 50000)
    
    Returns:
        The webpage content as text or HTML
    
    Examples:
        get_webpage_content("https://example.com")
        get_webpage_content("https://news.ycombinator.com", extract_text_only=True)
        get_webpage_content("https://api.example.com/data", extract_text_only=False)
    """
    try:
        import requests
        from bs4 import BeautifulSoup
        
        # Set headers to mimic a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Fetch the webpage
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        content_type = response.headers.get('content-type', '').lower()
        
        # Handle JSON responses
        if 'application/json' in content_type:
            import json
            data = response.json()
            result = json.dumps(data, indent=2)
        # Handle HTML
        elif 'text/html' in content_type or extract_text_only:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header']):
                element.decompose()
            
            if extract_text_only:
                # Get clean text
                result = soup.get_text(separator='\n', strip=True)
                # Clean up extra whitespace
                lines = [line.strip() for line in result.splitlines() if line.strip()]
                result = '\n'.join(lines)
            else:
                result = str(soup)
        else:
            # Plain text or other content
            result = response.text
        
        # Truncate if too long
        if len(result) > max_length:
            result = result[:max_length] + f"\n\n... (truncated, total length: {len(result)} chars)"
        
        # Add metadata header
        header = f"🌐 **Webpage Content**\n"
        header += f"URL: {url}\n"
        header += f"Status: {response.status_code}\n"
        header += f"Content-Type: {content_type}\n"
        header += f"Length: {len(result)} characters\n"
        header += "─" * 50 + "\n\n"
        
        return header + result
        
    except requests.exceptions.Timeout:
        return f"❌ Request timed out for: {url}"
    except requests.exceptions.RequestException as e:
        return f"❌ Failed to fetch webpage: {str(e)}"
    except Exception as e:
        logger.error(f"Error fetching webpage: {e}")
        return f"❌ Error: {str(e)}"

@mcp.tool()
def browse_web(task: str, url: str = None, model: str = "llama3.2:3b") -> str:
    """
    Use Browser Use AI agent to perform complex web browsing tasks.
    The agent can navigate, click, type, extract data, and interact with websites.
    
    Args:
        task: Natural language description of what to do (e.g., "Find the latest news about AI")
        url: Optional starting URL (if None, agent will search/navigate as needed)
        model: Ollama model to use for the agent (default: "llama3.2:3b" for speed)
    
    Returns:
        Result of the browsing task
    
    Examples:
        browse_web("Find the top 3 posts on Hacker News")
        browse_web("Search for Python tutorials and summarize the first result")
        browse_web("Go to example.com and extract the main heading", url="https://example.com")
    """
    try:
        import requests
        import json
        
        # Call Browser Use API (assuming it has an API endpoint)
        # For now, return a helpful message about the manual UI
        # TODO: Implement actual Browser Use API integration
        
        browser_use_url = "http://localhost:8002"
        
        return f"""🌐 **Browser Use Agent**

Task: {task}
Starting URL: {url or 'Auto-navigate'}
Model: {model}

⚠️ **Browser Use Integration In Progress**

The Browser Use agent is currently available via web UI at:
{browser_use_url}

**Temporary Workaround:**
1. Open {browser_use_url} in your browser
2. Enter task: "{task}"
3. Select model: {model}
4. Click "Run Task"

**Coming Soon:**
Full API integration for automated browsing via MCP tools.

**Alternative:** Use `get_webpage_content(url)` for simple page fetching.
"""
        
    except Exception as e:
        logger.error(f"Error with browser agent: {e}")
        return f"❌ Browser Use error: {str(e)}"

if __name__ == "__main__":

    logger.info("🚀 Starting MCP Server with official Mem0 on SSE (HTTP)...")
    # Run using uvicorn directly to control host/port
    import uvicorn
    
    app = mcp.sse_app()
    
    # Note: Status page removed due to Starlette/FastAPI incompatibility
    # Access tools via SSE endpoint at http://192.168.1.211:8001/sse
    
    uvicorn.run(app, host="0.0.0.0", port=8001)

