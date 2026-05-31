"""
MergeMind — Heuristics Tool

Deterministic code analysis to extract statistical metrics from a git diff.
This acts as a grounded data source for the AI Arbitration Agent, preventing
hallucinations and providing objective measures of code impact.
"""

import re
import httpx
from typing import Any, Dict
from config.settings import settings


def fetch_gitlab_mr_diff(project_id: str, merge_request_iid: str) -> str:
    """
    Fetches the raw unified diff of a GitLab Merge Request directly from the GitLab API.
    Use this tool to fetch diffs instead of the GitLab MCP server due to a known bug.

    Args:
        project_id: The ID of the GitLab project.
        merge_request_iid: The IID of the merge request.

    Returns:
        A single string containing the combined unified diff of all changed files.
    """
    url = f"{settings.gitlab_api_url}/projects/{project_id}/merge_requests/{merge_request_iid}/diffs"
    headers = {"PRIVATE-TOKEN": settings.gitlab_personal_access_token}
    
    try:
        response = httpx.get(url, headers=headers)
        response.raise_for_status()
        diffs = response.json()
        
        combined_diff = ""
        for d in diffs:
            # Reconstruct standard unified diff headers
            old_path = d.get('old_path', '/dev/null')
            new_path = d.get('new_path', '/dev/null')
            
            if d.get('new_file'):
                old_path = '/dev/null'
            if d.get('deleted_file'):
                new_path = '/dev/null'
                
            combined_diff += f"--- a/{old_path}\n"
            combined_diff += f"+++ b/{new_path}\n"
            combined_diff += d.get('diff', '') + "\n"
            
        return combined_diff if combined_diff else "No changes found."
    except Exception as e:
        return f"Error fetching diff: {e}"


def post_gitlab_mr_comment(project_id: str, merge_request_iid: str, body: str) -> str:
    """
    Posts a comment (note) to a GitLab Merge Request directly via the GitLab API.
    Use this tool instead of the GitLab MCP server's create_note tool due to a known bug.

    Args:
        project_id: The ID of the GitLab project.
        merge_request_iid: The IID of the merge request.
        body: The markdown-formatted text content of the comment.

    Returns:
        A success message or an error string.
    """
    url = f"{settings.gitlab_api_url}/projects/{project_id}/merge_requests/{merge_request_iid}/notes"
    headers = {"PRIVATE-TOKEN": settings.gitlab_personal_access_token}
    
    try:
        response = httpx.post(url, headers=headers, json={"body": body})
        response.raise_for_status()
        return f"Successfully posted comment to MR {merge_request_iid}."
    except Exception as e:
        return f"Error posting comment: {e}"


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
