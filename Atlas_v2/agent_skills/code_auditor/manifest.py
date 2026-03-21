import subprocess
import os
from core.logger import logger
from core.skills.wrapper import agent_tool

@agent_tool
def find_dead_code(target_dir: str = ".", min_confidence: int = 80, **kwargs) -> str:
    """
    Finds unused code (dead code) using 'vulture'.
    Helps identify variables, functions, and classes that are defined but never used.
    
    Args:
        target_dir: The directory to scan. Defaults to current directory.
        min_confidence: Confidence threshold for reporting (0-100). Default is 80.
    """
    logger.info("audit.dead_code_scan", dir=target_dir, confidence=min_confidence)
    
    # Ensure target_dir is absolute if possible
    abs_path = os.path.abspath(target_dir)
    
    try:
        # Run vulture with 30s timeout (safety v3.6.4)
        cmd = ["vulture", abs_path, f"--min-confidence={min_confidence}"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=30)
        
        output = result.stdout.strip()
        errors = result.stderr.strip()
        
        if not output and not errors:
            return f"✅ [CODE AUDIT]: No dead code found in '{target_dir}' with confidence > {min_confidence}%."
            
        report = f"🔍 [CODE AUDIT]: Dead Code Report for '{target_dir}' (Confidence > {min_confidence}%):\n\n"
        
        if output:
            report += f"### Findings:\n{output}\n"
        
        if errors:
            report += f"\n### Warnings/Errors:\n{errors}\n"
            
        return report
        
    except subprocess.TimeoutExpired:
        return f"⚠️ [AUDIT TIMEOUT]: Dead code scan of '{target_dir}' timed out after 30s."
    except FileNotFoundError:
        return "❌ [CODE AUDIT]: 'vulture' is not installed or not in PATH."
@agent_tool
def find_code_duplicates(target_dir: str = ".", min_similarity_lines: int = 4, **kwargs) -> str:
    """
    Finds duplicated code blocks using 'pylint --enable=similarities'.
    Identifies identical logic copied across different files.
    
    Args:
        target_dir: The directory to scan. Defaults to current directory.
        min_similarity_lines: Minimum number of identical lines to trigger a report. Default is 4.
    """
    logger.info("audit.duplicate_scan", dir=target_dir, min_lines=min_similarity_lines)
    
    abs_path = os.path.abspath(target_dir)
    
    try:
        # Run pylint similarities check with 30s timeout (safety v3.6.4)
        cmd = [
            "pylint", 
            "--disable=all", 
            "--enable=similarities", 
            f"--min-similarity-lines={min_similarity_lines}",
            abs_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=30)
        
        output = result.stdout.strip()
        
        # Pylint similarities output usually starts with 'TOTAL LINES' or specific matches
        if not output or "Your code has been rated at" in output and len(output) < 50:
             return f"✅ [DUPLICATE CHECK]: No significant code duplication found in '{target_dir}' (min {min_similarity_lines} lines)."

        report = f"🔍 [DUPLICATE CHECK]: Code Duplication Report for '{target_dir}' (min {min_similarity_lines} lines):\n\n"
        report += output
        
        return report
        
    except subprocess.TimeoutExpired:
        return f"⚠️ [AUDIT TIMEOUT]: Duplicate scan of '{target_dir}' timed out after 30s. This usually happens when scanning large directories like 'Projects'."
    except FileNotFoundError:
        return "❌ [DUPLICATE CHECK]: 'pylint' is not installed or not in PATH."
@agent_tool
def audit_dependencies(target_dir: str = ".", **kwargs) -> str:
    """
    Checks for unused, missing, and transitive dependencies using 'deptry'.
    Ensures the project's dependency list is clean and accurate.
    
    Args:
        target_dir: The directory to scan. Defaults to current directory.
    """
    logger.info("audit.dependency_scan", dir=target_dir)
    
    abs_path = os.path.abspath(target_dir)
    
    try:
        # Run deptry with 30s timeout (safety v3.6.4)
        cmd = ["deptry", abs_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=30)
        
        output = result.stdout.strip()
        errors = result.stderr.strip()
        
        if not output and not errors:
             return f"✅ [DEPENDENCY AUDIT]: No issues found in '{target_dir}' dependencies."
 
        report = f"🔍 [DEPENDENCY AUDIT]: Dependency Report for '{target_dir}':\n\n"
        if output:
            report += f"### Findings:\n{output}\n"
        if errors:
            report += f"\n### Warnings/Errors:\n{errors}\n"
            
        return report
        
    except subprocess.TimeoutExpired:
        return f"⚠️ [AUDIT TIMEOUT]: Analysis of '{target_dir}' took too long and was aborted. Try a smaller sub-directory."
    except FileNotFoundError:
        return "❌ [DEPENDENCY AUDIT]: 'deptry' is not installed or not in PATH."
@agent_tool
def analyze_architecture(target_file: str = "main.py", max_bacon: int = 2, **kwargs) -> str:
    """
    Analyzes architectural links and module dependencies using 'pydeps'.
    Helps identify circular dependencies and excessive module coupling.
    
    Args:
        target_file: The entry point or module to start analysis from.
        max_bacon: Max depth of dependency tracking (default 2).
    """
    logger.info("audit.architecture_scan", file=target_file, depth=max_bacon)
    
    try:
        # Check if target_file exists
        if not os.path.exists(target_file):
            alt_paths = ["Atlas_v2/main.py", "core/main.py"]
            found = False
            for p in alt_paths:
                if os.path.exists(p):
                    target_file = p
                    found = True
                    break
            if not found:
                return f"❌ [ARCHITECTURE]: Target file '{target_file}' not found."

        # 1. Attempt to generate SVG (Requires Graphviz)
        output_file = "architecture_graph.svg"
        cmd_svg = [
            "pydeps", 
            target_file, 
            f"--max-bacon={max_bacon}", 
            "--noshow", 
            "-o", output_file
        ]
        
        result_svg = subprocess.run(cmd_svg, capture_output=True, text=True, check=False)
        
        if result_svg.returncode == 0 and os.path.exists(output_file):
            return f"✅ [ARCHITECTURE]: Dependency graph generated: {os.path.abspath(output_file)}."

        # 2. Fallback: Generate JSON/Text Dependencies (Does NOT require Graphviz)
        logger.warning("architecture.graph_failed", reason="Likely missing Graphviz. Falling back to text mode.")
        cmd_text = [
            "pydeps", 
            target_file, 
            f"--max-bacon={max_bacon}", 
            "--show-deps", 
            "--nodot"
        ]
        result_text = subprocess.run(cmd_text, capture_output=True, text=True, check=False)
        
        if result_text.returncode == 0:
            return f"⚠️ [ARCHITECTURE]: Graph generation failed (Graphviz missing), but here is the dependency data:\n\n{result_text.stdout}"
        
        return f"❌ [ARCHITECTURE]: pydeps failed: {result_text.stderr or result_text.stdout}"
        
    except FileNotFoundError:
        return "❌ [ARCHITECTURE]: 'pydeps' is not installed or not in PATH."
@agent_tool
def analyze_impact(target_file: str, **kwargs) -> str:
    """
    [SYNC-OR-FAIL] Performs impact analysis for a file change.
    Identifies which other modules in the project depend on the target file.
    
    Args:
        target_file: The file being modified.
    """
    logger.info("audit.impact_analysis", file=target_file)
    
    if not os.path.exists(target_file):
        return f"❌ [IMPACT]: File '{target_file}' not found."
        
    try:
        # Use pydeps in JSON mode to find reverse dependencies
        # We start from the root main.py (or similar) to see the whole tree
        root_file = "Atlas_v2/main.py" if os.path.exists("Atlas_v2/main.py") else "main.py"
        
        cmd = ["pydeps", root_file, "--show-deps", "--nodot", "--max-bacon=3"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        if result.returncode != 0:
            return f"❌ [IMPACT]: Failed to gather dependency data: {result.stderr}"
            
        import json
        data = json.loads(result.stdout)
        
        # Search for modules that import target_file
        # Note: pydeps uses module names, so we need to convert path to module
        target_mod = os.path.basename(target_file).replace(".py", "")
        
        affected = []
        for mod_name, info in data.items():
            if target_mod in info.get("imports", []):
                affected.append(mod_name)
                
        if not affected:
            return f"✅ [IMPACT]: No direct downstream dependencies found for '{target_file}' in the current scope."
            
        report = f"⚠️ [IMPACT ALERT]: Modifications to '{target_file}' may affect the following modules:\n"
        for mod in affected:
            report += f"- {mod}\n"
        report += "\nAction: Please verify these modules after your changes."
        return report
        
    except Exception as e:
        logger.error("audit.impact_failed", error=str(e))
        return f"❌ [IMPACT]: Analysis failed: {str(e)}"

EXPORTED_TOOLS = [find_dead_code, find_code_duplicates, audit_dependencies, analyze_architecture, analyze_impact]
