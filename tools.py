import re
import tempfile
import requests
import pandas as pd
from youtube_transcript_api._api import YouTubeTranscriptApi
import logging
import os
import openai
from langchain_tavily import TavilySearch
from langchain_community.document_loaders import WikipediaLoader
from langchain_community.document_loaders import ArxivLoader
from langchain_core.tools import tool
import mimetypes

# --- New Tools ---


@tool
def multiply(a: int, b: int) -> int:
    """Multiply two numbers.
    Args:
        a: first int
        b: second int
    """
    return a * b


@tool
def add(a: int, b: int) -> int:
    """Add two numbers.

    Args:
        a: first int
        b: second int
    """
    return a + b


@tool
def subtract(a: int, b: int) -> int:
    """Subtract two numbers.

    Args:
        a: first int
        b: second int
    """
    return a - b


@tool
def divide(a: int, b: int) -> float:
    """Divide two numbers.

    Args:
        a: first int
        b: second int
    """
    if b == 0:
        raise ValueError("Cannot divide by zero.")
    return a / b


@tool
def modulus(a: int, b: int) -> int:
    """Get the modulus of two numbers.

    Args:
        a: first int
        b: second int
    """
    return a % b


@tool
def wiki_search(query: str) -> dict[str, str]:
    """Search Wikipedia for a query and return maximum 2 results.

    Args:
        query: The search query."""
    search_docs = WikipediaLoader(query=query, load_max_docs=2).load()
    formatted_search_docs = "\n\n---\n\n".join(
        [
            f'<Document source="{doc.metadata["source"]}" page="{doc.metadata.get("page", "")}"/>\n{doc.page_content}\n</Document>'
            for doc in search_docs
        ]
    )
    return {"wiki_results": formatted_search_docs}


@tool
def web_search(query: str) -> dict[str, str]:
    """Search Tavily for a query and return maximum 3 results.

    Args:
        query: The search query."""
    search_docs = TavilySearch(k=3).invoke(query)
    formatted_search_docs = "\n\n---\n\n".join(
        [
            f'<Document source="{doc.metadata["source"]}" page="{doc.metadata.get("page", "")}"/>\n{doc.page_content}\n</Document>'
            for doc in search_docs
        ]
    )
    return {"web_results": formatted_search_docs}


@tool
def arvix_search(query: str) -> dict[str, str]:
    """Search Arxiv for a query and return maximum 3 result.

    Args:
        query: The search query."""
    search_docs = ArxivLoader(query=query, load_max_docs=3).load()
    formatted_search_docs = "\n\n---\n\n".join(
        [
            f'<Document source="{doc.metadata["source"]}" page="{doc.metadata.get("page", "")}"/>\n{doc.page_content[:1000]}\n</Document>'
            for doc in search_docs
        ]
    )
    return {"arvix_results": formatted_search_docs}


@tool
def youtube_transcript(url: str) -> str:
    """Fetch YouTube video transcript for a given URL.

    Args:
        url: The YouTube video URL.
    """
    # Extract video ID
    m = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", url)
    if not m:
        return "Error: could not parse YouTube video ID from URL."
    vid = m.group(1)
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(vid)
        texts = [seg.get("text", "") for seg in transcript_list]
        transcript = "\n".join(texts)
        if len(transcript) > 20000:
            return transcript[:20000] + "\n...[truncated]"
        return transcript
    except Exception as e:
        return f"Error fetching transcript: {e}"


@tool
def excel_tool(path: str = None, url: str = None, query: str = None) -> str:
    """Fetch and query an Excel file.
    Args:
        path: Local file path to the Excel file.
        url: Remote URL to the Excel file.
        query: Optional pandas query expression to filter rows.
    If no query is provided, returns columns and first 5 rows of the first sheet.
    """
    df = None
    cache_key = None

    if path:
        if not isinstance(path, str):
            return "Error: 'path' must be a string local file path."
        if not os.path.isfile(path):
            return f"Error: local file not found: {path}"
        cache_key = os.path.abspath(path)
        try:
            df = pd.read_excel(path, sheet_name=0)
        except Exception as e:
            return f"Error reading Excel from local path '{path}': {e}"
    elif url:
        if not isinstance(url, str):
            return "Error: 'url' must be a string."
        cache_key = url
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
                tmp.write(resp.content)
                tmp_path = tmp.name
            df = pd.read_excel(tmp_path, sheet_name=0)
        except Exception as e:
            return f"Error fetching/reading Excel from URL '{url}': {e}"
    else:
        return "Error: must provide either 'path' or 'url'."

    if df is None:
        return "Error: failed to load DataFrame."

    if not query:
        cols = list(df.columns)
        preview = df.head(5).to_string(index=False)
        return f"Columns: {cols}\nFirst 5 rows:\n{preview}"
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


@tool
def file_tool(path: str, action: str = "inspect") -> str:
    """Inspect or process files. For audio files, transcribes speech to text.
    Args:
        path: Path to the file.
        action: 'inspect' (default) or 'transcribe' for audio files.
    """
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
        return excel_tool.invoke({"path": path})
    # Default: just report file info
    size = os.path.getsize(path)
    return f"File '{path}' ({mime}), size: {size} bytes."


@tool
def python_file_qa(path: str, question: str = "Summarize this file.") -> str:
    """Read a Python (.py) file and answer a question about its content.
    Args:
        path: Path to the Python file.
        question: The question to answer about the file (default: summarize).
    """
    import os
    import openai

    if not path or not os.path.exists(path):
        return f"File not found: {path}"
    if not path.endswith(".py"):
        return "Only Python (.py) files are supported."

    try:
        with open(path, "r") as f:
            code = f.read()
    except Exception as e:
        return f"Error reading file: {e}"

    # Use OpenAI to answer the question about the code
    prompt = (
        f"You are a Python expert. Here is a Python file:\n\n"
        f"{code}\n\n"
        f"Question: {question}\n"
        f"Answer:"
    )
    try:
        response = openai.chat.completions.create(
            model="o3-2025-04-16",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant for Python code understanding.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )
        content = response.choices[0].message.content
        if content is not None:
            return content.strip()
        else:
            return "No content returned from LLM."
    except Exception as e:
        return f"Error querying LLM: {e}"
