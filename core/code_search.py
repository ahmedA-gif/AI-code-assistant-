import os
import fnmatch
import re
from pathlib import Path
from mcp.server.fastmcp import FastMCP

# LlamaIndex Imports
from llama_index.core import (
    VectorStoreIndex, 
    SimpleDirectoryReader, 
    StorageContext, 
    load_index_from_storage,
    Settings
)
from llama_index.llms.openai_like import OpenAILike
from llama_index.embeddings.openai import OpenAIEmbedding

mcp = FastMCP("GrokCodeAssistant")

Settings.llm = OpenAILike(
    model="grok-beta",  # or "grok-2-1212"
    api_base="https://api.x.ai/v1",
    api_key=os.getenv("GROK_API_KEY"),
    is_chat_model=True
)

# Embedding model – will fail gracefully if OPENAI_API_KEY is missing
try:
    Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")
except Exception as e:
    print(f"Warning: Could not initialize OpenAI embeddings: {e}")
    Settings.embed_model = None

class CodeSearch:
    def __init__(self, workspace_root="."):
        self.workspace_root = Path(workspace_root).resolve()
        self.persist_dir = self.workspace_root / ".mcp_grok_index"
        self.index = None  # Load lazily
        self._index_loaded = False

    def _ensure_index(self):
        """Load or create the vector index only when needed."""
        if self._index_loaded:
            return self.index is not None

        self._index_loaded = True

        if Settings.embed_model is None:
            print("No embedding model available – semantic search disabled.")
            return False

        # Try to load existing index
        if self.persist_dir.exists():
            try:
                storage_context = StorageContext.from_defaults(persist_dir=str(self.persist_dir))
                self.index = load_index_from_storage(storage_context)
                return True
            except Exception as e:
                print(f"Failed to load existing index: {e}")
                # Fall through to rebuild

        # Build new index
        try:
            reader = SimpleDirectoryReader(
                input_dir=str(self.workspace_root),
                recursive=True,
                required_exts=[".py", ".js", ".ts", ".md"],
                exclude_hidden=True
            )
            documents = reader.load_data()
            if not documents:
                print("No documents found for indexing.")
                return False

            self.index = VectorStoreIndex.from_documents(documents)
            self.index.storage_context.persist(persist_dir=str(self.persist_dir))
            return True
        except Exception as e:
            print(f"Index creation failed: {e}")
            self.index = None
            return False

    def get_index(self):
        """Return the index if available, else None."""
        if not self._index_loaded:
            self._ensure_index()
        return self.index

# Global engine instance (lazy)
engine = CodeSearch()

@mcp.tool()
def search_keyword(keyword, file_pattern="*", context_lines=2):
    results = []
    keyword_re = re.compile(re.escape(keyword), re.IGNORECASE)
    workspace = Path(".").resolve()

    for root, dirs, files in os.walk(workspace):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', 'venv', '__pycache__']]
        
        for file in files:
            if not fnmatch.fnmatch(file, file_pattern):
                continue
            
            file_path = Path(root) / file
            try:
                lines = file_path.read_text(encoding='utf-8', errors='ignore').splitlines()
                for i, line in enumerate(lines):
                    if keyword_re.search(line):
                        start = max(0, i - context_lines)
                        end = min(len(lines), i + context_lines + 1)
                        results.append({
                            'file': str(file_path.relative_to(workspace)),
                            'line': i + 1,
                            'context': "\n".join(lines[start:end])
                        })
            except Exception: 
                continue
    return results

@mcp.tool()
def search_semantic(query):
    """
    Perform semantic search using the vector index.
    Returns a message if index is unavailable.
    """
    idx = engine.get_index()
    if idx is None:
        return "Semantic search is unavailable. Please ensure:\n" \
               "- OPENAI_API_KEY is set correctly\n" \
               "- The workspace contains supported files (.py, .js, .ts, .md)\n" \
               "- Index creation succeeded (check console logs)."

    try:
        query_engine = idx.as_query_engine(similarity_top_k=5)
        response = query_engine.query(query)
        return str(response)
    except Exception as e:
        return f"Semantic search error: {str(e)}"