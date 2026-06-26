"""
Python REPL Tool — Safe sandboxed Python execution.
Used by agents to compute, format, or transform data.
"""

import io
import sys
import logging
import traceback
from typing import Dict, Any

logger = logging.getLogger("aria.tools.python_repl")

# Allowed built-ins for safety
SAFE_BUILTINS = {
    "abs", "all", "any", "bin", "bool", "chr", "dict", "dir",
    "divmod", "enumerate", "filter", "float", "format", "frozenset",
    "getattr", "hasattr", "hash", "hex", "int", "isinstance", "issubclass",
    "iter", "len", "list", "map", "max", "min", "next", "oct", "ord",
    "pow", "print", "range", "repr", "reversed", "round", "set", "setattr",
    "slice", "sorted", "str", "sum", "tuple", "type", "zip",
}


def python_repl(code: str, timeout: int = 5) -> Dict[str, Any]:
    """
    Execute Python code safely and return stdout + result.
    Returns: { success: bool, output: str, error: str }
    """
    # Filter allowed builtins
    safe_globals = {
        "__builtins__": {k: v for k, v in __builtins__.items() if k in SAFE_BUILTINS}
        if isinstance(__builtins__, dict)
        else {k: getattr(__builtins__, k) for k in SAFE_BUILTINS if hasattr(__builtins__, k)},
    }
    safe_globals["__builtins__"]["print"] = print  # allow print

    # Capture stdout
    old_stdout = sys.stdout
    sys.stdout  = buffer = io.StringIO()

    try:
        exec(compile(code, "<aria_repl>", "exec"), safe_globals)
        output = buffer.getvalue()
        logger.info(f"REPL executed successfully, output: {output[:80]}")
        return {"success": True, "output": output, "error": ""}
    except Exception:
        err = traceback.format_exc()
        logger.warning(f"REPL error: {err[:200]}")
        return {"success": False, "output": buffer.getvalue(), "error": err}
    finally:
        sys.stdout = old_stdout
