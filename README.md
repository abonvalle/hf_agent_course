---
title: Template Final Assignment
emoji: 🕵🏻‍♂️
colorFrom: indigo
colorTo: indigo
sdk: gradio
sdk_version: 5.25.2
app_file: app.py
pinned: false
hf_oauth: true
# optional, default duration is 8 hours/480 minutes. Max duration is 30 days/43200 minutes.
hf_oauth_expiration_minutes: 480
---

# Final Assignment Template

This template provides a foundation for building AI agents with various tools and capabilities.

## Setup with uv

This project uses [uv](https://docs.astral.sh/uv/) for fast and reliable Python package management.

### Prerequisites

1. Install uv:
   ```bash
   # On macOS and Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # On Windows
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   
   # With pip (if you have Python already)
   pip install uv
   ```

### Installation

1. Clone the repository:
   ```bash
   git clone <your-repo-url>
   cd Final_Assignment_Template
   ```

2. Create and activate a virtual environment with dependencies:
   ```bash
   uv sync
   ```

3. Activate the virtual environment:
   ```bash
   # The virtual environment is automatically managed by uv
   # To run commands in the environment, use:
   uv run python app.py
   ```

### Running the Application

```bash
# Run the main application
uv run python app.py

# Run with specific Python interpreter
uv run --python 3.12 python app.py
```

### Adding Dependencies

```bash
# Add a new dependency
uv add package-name

# Add a development dependency
uv add --dev package-name

# Remove a dependency
uv remove package-name
```

### Environment Variables

Create a `.env` file in the project root with your API keys:

```env
OPENAI_API_KEY=your_openai_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
SPACE_ID=your_space_id_here
```

## Legacy pip Support

If you prefer to use pip, the original `requirements.txt` file is still available:

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

## Comparison: uv vs pip

| Task | uv | pip |
|------|----|----|
| **Installation** | `curl -LsSf https://astral.sh/uv/install.sh \| sh` | Comes with Python |
| **Create environment** | `uv sync` (automatic) | `python -m venv venv && source venv/bin/activate` |
| **Install dependencies** | `uv sync` | `pip install -r requirements.txt` |
| **Add dependency** | `uv add package-name` | `pip install package-name && pip freeze > requirements.txt` |
| **Run script** | `uv run python app.py` | `python app.py` (after activation) |
| **Lock dependencies** | `uv.lock` (automatic) | `pip freeze > requirements.txt` |
| **Speed** | ⚡ Very fast | 🐌 Slower |
| **Reproducibility** | 🔒 Built-in lockfile | 📝 Manual freeze required |

## Configuration Reference

Check out the configuration reference at https://huggingface.co/docs/hub/spaces-config-reference