"""
MergeMind — Heuristics Tool

Deterministic code analysis to extract statistical metrics from a git diff.
This acts as a grounded data source for the AI Arbitration Agent, preventing
hallucinations and providing objective measures of code impact.
"""

import re
from typing import Any, Dict


def analyze_diff(diff_content: str) -> Dict[str, Any]:
    """
    Analyzes a git unified diff and extracts heuristic metrics.

    This function acts as a tool for the ADK Agent. By providing hard numbers
    (lines changed, test coverage, file types), it grounds the LLM's evaluation
    in statistical reality.

    Args:
        diff_content: The raw string of a git unified diff.

    Returns:
        Dict containing metrics:
        - total_lines_added (int)
        - total_lines_removed (int)
        - net_line_delta (int)
        - files_modified (list[str])
        - file_types (dict[str, int])
        - test_files_added (int)
        - test_files_modified (int)
        - has_test_coverage (bool)
        - config_only_change (bool)
        - complexity_indicator (str: "trivial", "moderate", "complex")
    """
    total_lines_added = 0
    total_lines_removed = 0
    files_modified = set()
    file_types = {}
    test_files_added = 0
    test_files_modified = 0

    # Parse unified diff
    lines = diff_content.splitlines()
    current_file = None

    is_new_file = False

    for line in lines:
        # Detect file paths (e.g., "+++ b/src/main.py")
        if line.startswith("--- a/") or line.startswith("--- /dev/null"):
            is_new_file = line == "--- /dev/null"
            filename = line[6:]
            if filename != "/dev/null":
                files_modified.add(filename)
                
        elif line.startswith("+++ b/"):
            filename = line[6:]
            if filename != "/dev/null":
                current_file = filename
                files_modified.add(filename)

                # Extract extension
                if "." in filename:
                    ext = "." + filename.split(".")[-1]
                    file_types[ext] = file_types.get(ext, 0) + 1

                # Check if it's a test file
                if "test" in filename.lower():
                    if is_new_file:
                        test_files_added += 1
                    else:
                        test_files_modified += 1
            continue

        # Count line changes
        if line.startswith("+") and not line.startswith("+++"):
            total_lines_added += 1
        elif line.startswith("-") and not line.startswith("---"):
            total_lines_removed += 1

    # Heuristic: Config-only change?
    code_extensions = {".py", ".js", ".ts", ".go", ".java", ".cpp", ".c", ".rs"}
    config_only = True
    if files_modified:
        for f in files_modified:
            if any(f.endswith(ext) for ext in code_extensions):
                config_only = False
                break

    # Heuristic: Complexity
    total_changed = total_lines_added + total_lines_removed
    if total_changed < 10:
        complexity = "trivial"
    elif total_changed <= 100:
        complexity = "moderate"
    else:
        complexity = "complex"

    return {
        "total_lines_added": total_lines_added,
        "total_lines_removed": total_lines_removed,
        "net_line_delta": total_lines_added - total_lines_removed,
        "files_modified": list(files_modified),
        "file_types": file_types,
        "test_files_added": test_files_added,
        "test_files_modified": test_files_modified,
        "has_test_coverage": (test_files_added + test_files_modified) > 0,
        "config_only_change": config_only if files_modified else False,
        "complexity_indicator": complexity,
    }
