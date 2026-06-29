import os
from pathlib import Path


# Returns the writable data directory used for logs and vector memory.
def get_data_dir() -> Path:
    return Path(os.getenv("DEV_CODE_DATA_DIR", "coderagent"))


# Returns the ChromaDB persistence directory.
def get_chroma_dir() -> Path:
    return get_data_dir() / "chroma_db"


# Returns the JSONL trace log path.
def get_trace_log_path() -> Path:
    return get_data_dir() / "traces.jsonl"
