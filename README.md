# Research Agentic (LangGraph + Groq + BrightData)

This project implements a multi-resource research agent using **LangGraph** for orchestration and **LangChain** for LLM calls. For a given user question, it:

1. Searches the web via **Google** and **Bing** (through the BrightData Search API).
2. Searches **Reddit** and selects the most relevant threads using an LLM (structured output).
3. Downloads the selected Reddit posts/comments (again via BrightData snapshot datasets).
4. Analyzes results from Google, Bing, and Reddit with the LLM.
5. Synthesizes everything into a single final answer.

## Features

- Concurrent multi-source research graph (Google, Bing, Reddit).
- LLM-based URL selection for Reddit to keep context sizes manageable.
- Context compaction to reduce prompt size before LLM calls.
- Interactive CLI runner (`python main.py`) that loops until you type `exit`.

## Architecture (LangGraph)

The system is defined as a `StateGraph` with a typed state object (`State` in `main.py`).

### State schema

In `main.py`, the graph state is a `TypedDict` containing:

- `messages`: running message history (for `add_messages`)
- `user_question`: the user query
- `google_results`, `bing_results`, `reddit_results`: raw search outputs
- `selected_reddit_urls`: URLs chosen by the LLM
- `reddit_post_data`: downloaded Reddit comments/posts data
- `google_analysis`, `bing_analysis`, `reddit_analysis`: LLM analyses per source
- `final_answer`: the synthesized final response

### Graph nodes and edges

The graph is built in `main.py` with nodes for: searching (Google/Bing/Reddit), selecting Reddit URLs (LLM structured output), downloading selected Reddit content, analyzing each source, and synthesizing a final answer.

### End-to-end flow (high level)

![Alt text that describes the image](image.png)


Key behaviors implemented in code:

- `web_operations.py` uses the BrightData Search API to run Google/Bing queries and BrightData Dataset snapshot APIs to discover Reddit posts and download selected Reddit content.
- `analyse_reddit_posts()` uses an LLM structured-output schema to select a small set of the most relevant Reddit URLs (to control context size).
- `main.py` runs an interactive loop: for each prompt it invokes the LangGraph compiled graph and prints `final_answer`.

## Setup

### 1) Prerequisites

- Python 3.10+ (the code uses modern typing like `str | None`)
- A `.env` file containing required API keys (see below)

### 2) Create and activate a virtual environment
Run: `python3 -m venv .venv` then `source .venv/bin/activate`.

### 3) Install dependencies
Run: `pip install -r requirements.txt`.

### 4) Configure environment variables (`.env`)

Create a `.env` file in the repo root with the following variables:

- `GROQ_API_KEY` (required): used to authenticate the Groq LLM
- `BRIGHTDATA_API_KEY` (required): used to authenticate BrightData search + dataset snapshot endpoints

Example:
- `GROQ_API_KEY="YOUR_GROQ_API_KEY"`
- `BRIGHTDATA_API_KEY="YOUR_BRIGHTDATA_API_KEY"`

### 5) Model + dataset IDs

Some values are currently hardcoded in code:

- LLM model string in `main.py`:
  - `init_chat_model('groq:llama-3.1-8b-instant')`
- BrightData dataset IDs in `main.py` / `web_operations.py`
If you want to use different BrightData datasets, update those IDs in the corresponding files.

## How to run

From the repo root:
Run: `python main.py`.

You will be prompted:
Type your question at `Enter your message:`.

Example:
Try: `Enter your message: What are the best practices for prompt engineering?`

When you are done:
Type `exit` to quit.

## Troubleshooting

- **Missing API keys / authentication errors**
  - Ensure `GROQ_API_KEY` and `BRIGHTDATA_API_KEY` are present in `.env`.
- **BrightData snapshot timeouts**
  - `poll_snapshot_status()` waits for `status == "ready"` (defaults: up to `max_attempts=60`, `delay=5`).
  - If you have slow data pipelines, consider increasing these parameters in `snapshot_operations.py`.
- **LLM structured output failures**
  - `analyse_reddit_posts()` catches exceptions and falls back to `selected_urls=[]`.
  - If outputs look empty, verify the LLM provider, model availability, and the prompts in `prompts.py`.

## Project layout

- `main.py`: LangGraph graph definition, research nodes, and the interactive CLI
- `llm.py`: a small standalone LLM experiment (not imported by `main.py`)
- `prompts.py`: prompt templates used for analysis/synthesis and Reddit URL selection
- `web_operations.py`: BrightData request helpers, web search, and Reddit snapshot triggers/downloads
- `snapshot_operations.py`: polling and downloading BrightData dataset snapshots

