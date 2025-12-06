# 📦 Installation Guide for SpoonOS Core Developer Framework

This guide walks you through setting up the **SpoonOS Core Developer Framework (SCDF)** — from dependencies to installation via pip or source.

---

## ✅ Prerequisites

- **Python ≥ 3.10**
- **pip** (Python package manager)
- **uv** _(optional)_ — a faster alternative to pip

---

## 🧪 Use a Virtual Environment (Recommended)

We strongly recommend using a virtual environment to isolate dependencies and avoid global conflicts.

```bash

# Create and activate a virtual environment (macOS/Linux)
python -m venv spoon-env
source spoon-env/bin/activate

# For Windows
python -m venv spoon-env
spoon-env\Scripts\activate
```

## Install methods

### 1. 📦 Install from PyPI

```python
pip install spoon-ai-sdk
```

### 2. 🚀 Install From Source

#### Option A: Using pip (Standard)

```bash
# Clone the repository
git clone https://github.com/XSpoonAi/spoon-core.git
cd spoon-core

# Install dependencies
pip install -r requirements.txt

# Optional: install in editable mode
pip install -e .
```

#### Option B: Using uv (Faster)

```bash
# Clone the repo
git clone https://github.com/XSpoonAi/spoon-core.git
cd spoon-core

# Install using uv
uv pip install -r requirements.txt
uv pip install -e .
```

## ✅ Next Steps

After installation, continue to:

- ⚙️ [Configure Environment & Keys](./configuration.md)
- 🤖 [Set up OpenRouter LLM models](./openrouter.md)
- 🧠 [Start the CLI or develop your custom agents](./cli.md)
- 🤖 [Explore agent capabilities](./agent.md)
- 🌐 [Use Web3 tools via MCP](./mcp_mode_usage.md)
