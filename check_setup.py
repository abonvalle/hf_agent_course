#!/usr/bin/env python3
"""
Setup script for the Final Assignment Template.
Run this to verify that all dependencies are properly installed.
"""

import sys
import importlib.util


def check_import(package_name: str, display_name: str | None = None) -> bool:
    """Check if a package can be imported."""
    if display_name is None:
        display_name = package_name
    
    try:
        spec = importlib.util.find_spec(package_name)
        if spec is not None:
            print(f"✅ {display_name}")
            return True
        else:
            print(f"❌ {display_name} - not found")
            return False
    except ImportError:
        print(f"❌ {display_name} - import error")
        return False


def main() -> None:
    """Check all required dependencies."""
    print("🔍 Checking dependencies...")
    print(f"Python version: {sys.version}")
    print("-" * 50)
    
    packages = [
        ("gradio", "Gradio"),
        ("requests", "Requests"),
        ("openai", "OpenAI"),
        ("pandas", "Pandas"),
        ("dotenv", "Python-dotenv"),
        ("langgraph", "LangGraph"),
        ("langchain", "LangChain"),
        ("langchain_openai", "LangChain OpenAI"),
        ("langchain_community", "LangChain Community"),
        ("youtube_transcript_api", "YouTube Transcript API"),
        ("langchain_tavily", "LangChain Tavily"),
    ]
    
    all_good = True
    for package, display in packages:
        if not check_import(package, display):
            all_good = False
    
    print("-" * 50)
    if all_good:
        print("🎉 All dependencies are properly installed!")
        print("You can now run: uv run python app.py")
    else:
        print("⚠️  Some dependencies are missing. Try running: uv sync")
        sys.exit(1)


if __name__ == "__main__":
    main()
