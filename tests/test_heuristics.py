"""
MergeMind — Tests for Heuristics Tool
"""

from src.tools.heuristics import analyze_diff


def test_analyze_diff_basic_addition():
    diff = """
+++ b/src/main.py
@@ -10,3 +10,4 @@
 def hello():
     print("world")
+    return True
"""
    result = analyze_diff(diff)
    assert result["total_lines_added"] == 1
    assert result["total_lines_removed"] == 0
    assert result["net_line_delta"] == 1
    assert "src/main.py" in result["files_modified"]
    assert result["file_types"].get(".py") == 1
    assert result["complexity_indicator"] == "trivial"
    assert not result["config_only_change"]


def test_analyze_diff_test_files():
    diff = """
+++ b/tests/test_main.py
@@ -0,0 +1,5 @@
+def test_hello():
+    assert True
"""
    # Simulate a new file by including /dev/null
    diff_with_dev_null = "--- a/dev/null\n" + diff
    
    result = analyze_diff(diff_with_dev_null)
    assert result["test_files_added"] > 0 or result["test_files_modified"] > 0
    assert result["has_test_coverage"] is True


def test_analyze_diff_config_only():
    diff = """
+++ b/README.md
@@ -1 +1,2 @@
 # Title
+Added a line
"""
    result = analyze_diff(diff)
    assert result["config_only_change"] is True
