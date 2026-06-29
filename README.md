# Dev-Code

Dev-Code is an A2A ReAct debugging agent for Python code. It runs broken code in a local sandbox, analyzes the error, searches memory and web context, generates a fix with Gemini when needed, verifies the fix, and logs the full trace for review.

## What It Does

- Runs Python code through a guarded subprocess sandbox.
- Shows a visible ReAct-style trace with specialist agents.
- Uses an A2A flow: `OrchestratorAgent`, `AnalyzerAgent`, `FixerAgent`, and `VerifierAgent`.
- Stores verified fixes in ChromaDB memory.
- Skips Gemini when a matching remembered fix verifies successfully.
- Exposes the workflow through Streamlit, FastAPI, and MCP.
- Logs runs to JSONL for simple LLMOps metrics.

## Architecture

```text
User code
  -> VerifierAgent runs code
  -> AnalyzerAgent reads the error
  -> OrchestratorAgent checks fix memory
  -> VerifierAgent tests remembered fixes
  -> FixerAgent calls Gemini if memory cannot solve it
  -> VerifierAgent verifies generated fix
  -> OrchestratorAgent saves successful fixes
```

## Project Structure

```text
coderagent/
  app.py                  Streamlit UI
  api.py                  FastAPI wrapper
  mcp_server.py           MCP tool server
  logger.py               JSONL trace logger
  sandbox.py              local code execution guard
  fix_memory.py           ChromaDB fix memory
  agents/
    analyzer.py
    fixer.py
    verifier.py
    orchestrator.py
  tools/
    run_code.py
    search_error.py
    search_memory.py
    suggest_fix.py
```

## Setup

Install dependencies:

```powershell
pip install -r coderagent\requirements.txt
```

Create a local environment file:

```powershell
copy .env.example coderagent\.env
```

Then edit `coderagent\.env`:

```text
GEMINI_API_KEY=your_real_key_here
```

## Run The Streamlit App

```powershell
streamlit run coderagent\app.py
```

The app includes:

- `Debugger` tab for interactive debugging.
- `LLMOps Dashboard` tab for run counts, memory usage, Gemini usage, average steps, average time, and recent runs.
- Sidebar session history with a `Load Code` button that restores old input without rerunning the agent.

## Run The FastAPI Server

```powershell
uvicorn coderagent.api:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

Example request body for `POST /debug`:

```json
{
  "code": "print(10 / 0)"
}
```

Example response shape:

```json
{
  "success": true,
  "fixed_code": "...",
  "trace": []
}
```

## Run The MCP Server

```powershell
python -m coderagent.mcp_server
```

This starts a stdio MCP server. It is expected to wait silently until an MCP client connects.

Exposed tools:

- `run_python_code`
- `search_python_error`
- `search_fix_memory`
- `debug_python_code`

## Logs And Memory

Run logs are written to:

```text
coderagent/traces.jsonl
```

Each row records:

- timestamp
- input code
- fixed code
- success
- memory usage
- Gemini usage
- step count
- elapsed time

Verified fix memory is stored locally with ChromaDB under:

```text
coderagent/chroma_db/
```

This folder is intentionally ignored by Git.

## Demo Flow

1. Run `print(10 / 0)` once.
2. Watch Dev-Code analyze, search, generate, verify, and save a fix.
3. Run the same error again.
4. Dev-Code should use memory and skip Gemini if the remembered fix verifies.
5. Open the dashboard and confirm run count, memory usage, Gemini usage, and timing.

## Interview Summary

Dev-Code started as a manual ReAct debugging loop and grew into a small agentic system. It now has specialist agents, local code execution, web search, Gemini-based fixing, ChromaDB memory, MCP exposure, FastAPI access, and JSONL trace logging for observability.
