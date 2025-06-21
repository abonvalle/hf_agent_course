import re
import tempfile
import requests
import pandas as pd
from youtube_transcript_api._api import YouTubeTranscriptApi
from duckduckgo_search import DDGS
import json
import logging
import os
import openai


# --- New Tools ---


class YouTubeTool:
    def __init__(self, name="youtube_transcript", description=None):
        self.name = name
        self.description = description or (
            "Fetch YouTube video transcript. Args: {'url': '<YouTube URL>'}."
        )

    def invoke(self, args: dict) -> str:
        # Parse args robustly
        if not isinstance(args, dict):
            try:
                args = json.loads(args)
            except Exception:
                return "Error: args must be a dict with 'url'."
        url = args.get("url")
        if not url or not isinstance(url, str):
            return "Error: 'url' parameter missing or not a string."
        # Extract video ID
        vid = None
        # Patterns: https://www.youtube.com/watch?v=VIDEOID or youtu.be/VIDEOID
        m = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", url)
        if m:
            vid = m.group(1)
        else:
            return "Error: could not parse YouTube video ID from URL."
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(vid)
            # Combine segments
            texts = [seg.get("text", "") for seg in transcript_list]
            transcript = "\n".join(texts)
            # Optionally truncate or return full
            if len(transcript) > 20000:
                # Return first ~20000 chars
                return transcript[:20000] + "\n...[truncated]"
            return transcript
        except Exception as e:
            return f"Error fetching transcript: {e}"


class ExcelTool:
    def __init__(self, name="excel_tool", description=None):
        self.name = name
        self.description = description or (
            "Fetch and query an Excel file. "
            "Args: {'url': '<file URL>'} or {'path': '<local path>'}, optional 'query': '<pandas query expression>'. "
            "If no 'query', returns columns and first 5 rows of first sheet."
        )
        # cache DataFrames by identifier (URL or absolute path)
        self._cache: dict[str, pd.DataFrame] = {}

    def invoke(self, args: dict) -> str:
        # Robust JSON parsing if needed
        if not isinstance(args, dict):
            try:
                args = json.loads(args)
            except Exception:
                return "Error: args must be a dict with 'url' or 'path' and optional 'query'."
        url = args.get("url")
        path = args.get("path")
        query = args.get("query")

        df = None
        cache_key = None

        if path:
            # Local file path scenario
            if not isinstance(path, str):
                return "Error: 'path' must be a string local file path."
            # Ensure file exists
            if not os.path.isfile(path):
                return f"Error: local file not found: {path}"
            cache_key = os.path.abspath(path)
            if cache_key in self._cache:
                df = self._cache[cache_key]
            else:
                # Attempt to read first sheet
                try:
                    df = pd.read_excel(path, sheet_name=0)
                    self._cache[cache_key] = df
                except Exception as e:
                    return f"Error reading Excel from local path '{path}': {e}"
        elif url:
            # Remote URL scenario
            if not isinstance(url, str):
                return "Error: 'url' must be a string."
            cache_key = url
            if cache_key in self._cache:
                df = self._cache[cache_key]
            else:
                # Download and read
                try:
                    resp = requests.get(url, timeout=15)
                    resp.raise_for_status()
                    # Save to temp file
                    with tempfile.NamedTemporaryFile(
                        suffix=".xlsx", delete=False
                    ) as tmp:
                        tmp.write(resp.content)
                        tmp_path = tmp.name
                    df = pd.read_excel(tmp_path, sheet_name=0)
                    self._cache[cache_key] = df
                except Exception as e:
                    return f"Error fetching/reading Excel from URL '{url}': {e}"
        else:
            return "Error: must provide either 'path' or 'url'."

        # At this point, df is loaded
        if df is None:
            return "Error: failed to load DataFrame."

        # If no query, return summary of first sheet
        if not query:
            cols = list(df.columns)
            preview = df.head(5).to_string(index=False)
            return f"Columns: {cols}\nFirst 5 rows:\n{preview}"
        # If query provided
        if not isinstance(query, str):
            return "Error: 'query' must be a string pandas.query expression."
        try:
            result = df.query(query)
            if result.empty:
                return "Query returned no rows."
            preview = result.head(10).to_string(index=False)
            return f"Query result (first up to 10 rows):\n{preview}"
        except Exception as e:
            return f"Error applying query '{query}': {e}"


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DuckDuckGoTool:
    def __init__(self, name="duckduckgo_search", max_results=3):
        self.name = name
        self.max_results = max_results
        self.description = "Search the web using DuckDuckGo. Args: {'query': <search string>}. Returns formatted top results."

    def invoke(self, args: dict) -> str:
        # Robustly parse args
        try:
            if not isinstance(args, dict):
                args = json.loads(args)
        except Exception as e:
            logger.warning(
                f"DuckDuckGoTool: could not parse args as JSON: {e}. Treating args as raw string."
            )
            args = {"query": str(args)}
        query = args.get("query", "")
        if not isinstance(query, str):
            query = str(query)
        query = query.strip()
        if not query:
            return "Error: empty query."
        logger.info(f"DuckDuckGoTool: searching for query: {query!r}")
        return duckduckgo_search(query, max_results=self.max_results)


def duckduckgo_search(query: str, max_results: int = 3) -> str:
    try:
        # Attempt to open DDGS; if network blocked, this will raise
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
    except Exception as e:
        # Log full exception
        logger.error(
            f"Error during DuckDuckGo search for query {query!r}: {e}", exc_info=True
        )
        return f"Error during DuckDuckGo search: {e}"
    if not results:
        logger.info(f"DuckDuckGoTool: no results for query {query!r}")
        return "No results found."
    # Format results
    formatted = []
    for i, r in enumerate(results, start=1):
        title = r.get("title", "").strip()
        href = r.get("href", "").strip()
        snippet = r.get("body", "").strip()
        if len(snippet) > 300:
            snippet = snippet[:300].rstrip() + "..."
        formatted.append(f"{i}. {title}\nURL: {href}\nSnippet: {snippet}")
    output = "\n\n".join(formatted)
    logger.info(f"DuckDuckGoTool: returning {len(results)} results for query {query!r}")
    return output


class FileTool:
    def __init__(self, excel_tool=None, name="file_tool"):
        self.name = name
        self.description = (
            "Inspect or process files. For audio files, transcribes speech to text. "
            "Args: {'path': <file_path>, 'action': 'inspect' or 'transcribe'}."
        )
        self.excel_tool = excel_tool

    def invoke(self, args):
        path = args.get("path")
        action = args.get("action", "inspect")
        if not path or not os.path.exists(path):
            return f"File not found: {path}"

        mime, _ = mimetypes.guess_type(path)
        if not mime:
            return f"Could not determine file type for {path}"

        # Handle audio files
        if mime.startswith("audio"):
            if action == "transcribe":
                try:
                    with open(path, "rb") as audio_file:
                        transcript = openai.audio.transcriptions.create(
                            model="whisper-1", file=audio_file
                        )
                    return transcript.text
                except Exception as e:
                    logging.exception("Audio transcription failed")
                    return f"Audio transcription failed: {e}"
            else:
                return f"Audio file detected. To transcribe, use action='transcribe'."

        # Handle Excel files
        if mime in [
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ]:
            if self.excel_tool:
                return self.excel_tool.invoke({"path": path})
            else:
                return "Excel tool not available."

        # Default: just report file info
        size = os.path.getsize(path)
        return f"File '{path}' ({mime}), size: {size} bytes."
