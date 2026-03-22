import os
import json
from core.skills.wrapper import agent_tool
from core.brain.memory import memory_manager
from agent_skills.file_master.manifest import read_file, write_file, delete_file
from agent_skills.telegram_bridge.manifest import ask_user_confirmation, send_telegram_message
import subprocess
from core.logger import logger

@agent_tool
def refactor_code(path: str, instructions: str, new_code: str, **kwargs) -> str:
    """
    Expert-level refactoring tool (v2.8.7).
    1. Analyzes file and project context via RAG.
    2. Requires Commander's confirmation via Telegram with a preview.
    """
    if not path.lower().endswith(".py"):
        return f"❌ [REFACTOR REJECTED]: File '{path}' is not a Python file. 'refactor_code' uses Ruff and Pytest for verification, which ONLY support .py files. For HTML, JS, CSS, or MD, you MUST use 'replace_file_content' or 'write_file' instead."

    # 1. Gather Context
    current_content = read_file(path)
    if "Error" in current_content:
        return current_content
        
    # Semantic search for usages and patterns related to this file
    memory_manager.get_context_block(query=f"usages of {path} or architectural patterns", n_results=5)
    
    # 2. Prepare Proposal
    # Truncate preview for Telegram
    code_preview = new_code[:500] + "..." if len(new_code) > 500 else new_code
    
    proposal_summary = (
        f"🛠️ **REFACTOR PROPOSAL** for `{path}`:\n"
        f"📝 **Instructions**: {instructions}\n\n"
        f"📄 **New Code Preview**:\n```python\n{code_preview}\n```\n"
        "Do you want me to apply these changes?"
    )
    
    # 3. Human-In-The-Loop (HITL)
    confirmed = ask_user_confirmation(text=proposal_summary)
    
    if not confirmed:
        return "❌ [REFUSED]: Commander rejected the refactoring proposal."
    
    # 4. Shadow Workspace Verification (March 2026 Protocol)
    shadow_path = path + ".shadow_copy.py"
    logger.info("code_intelligence.shadow_verification_start", path=shadow_path)
    
    try:
        # Create shadow copy
        write_file(path=shadow_path, content=new_code)
        
        # A. Ruff Linting & Formatting
        logger.info("code_intelligence.ruff_check")
        ruff_res = subprocess.run(f"ruff check {shadow_path} --fix", shell=True, capture_output=True, text=True)
        
        if ruff_res.returncode != 0:
            os.remove(shadow_path) if os.path.exists(shadow_path) else None
            return f"❌ [VERIFICATION FAILED]: Ruff found fatal errors:\n{ruff_res.stdout or ruff_res.stderr}"
            
        # B. Pytest (if applicable)
        test_file = os.path.join("tests", "test_" + os.path.basename(path))
        if os.path.exists(test_file):
            logger.info("code_intelligence.pytest_check", test=test_file)
            pytest_res = subprocess.run(f"pytest {test_file}", shell=True, capture_output=True, text=True)
            if pytest_res.returncode != 0:
                os.remove(shadow_path) if os.path.exists(shadow_path) else None
                return f"❌ [VERIFICATION FAILED]: Unit tests failed for this change:\n{pytest_res.stdout[:500]}..."

        # 5. Apply Changes only after verification
        result = write_file(path=path, content=new_code)
        if os.path.exists(shadow_path): os.remove(shadow_path)
        
        if "✅" in result:
            send_telegram_message(text=f"🚀 **SUCCESS**: File `{path}` has been verified (Ruff/Pytest) and refactored.")
            return f"✅ [VERIFIED & REFACTORED]: {path} passed security checks and updated."
            
    except Exception as e:
        if os.path.exists(shadow_path): os.remove(shadow_path)
        return f"🔥 [SYSTEM ERROR] during verification: {e}"
    
    return result

@agent_tool
def verify_code(filepath: str, **kwargs) -> str:
    """
    Manual Verification Tool: Runs Ruff and Pytest on an existing file to check for regressions.
    """
    if not filepath.lower().endswith(".py"):
        return f"❌ [VERIFY REJECTED]: File '{filepath}' is not a Python file. Verification (Ruff/Pytest) is only available for .py files."

    logger.info("code_intelligence.manual_verify", path=filepath)
    ruff_res = subprocess.run(f"ruff check {filepath}", shell=True, capture_output=True, text=True)
    
    report = f"### Verification Report for `{filepath}`:\n"
    report += f"✅ Ruff: {'Clean' if ruff_res.returncode == 0 else 'Issues found'}\n"
    if ruff_res.returncode != 0:
        report += f"```\n{ruff_res.stdout or ruff_res.stderr}\n```\n"
        
    return report

@agent_tool
def refresh_code_index(force: bool = False, **kwargs) -> str:
    """
    Triggers a full project-wide re-indexing of all source files into the vector store.
    Use this if you feel AXIS has 'forgotten' recently added external files.
    """
    if not hasattr(memory_manager, 'indexer') or not memory_manager.indexer:
        return "❌ [ERROR]: Code Indexer is not initialized."
    
    # [v3.6.9] Infinite Indexing Loop Prevention
    if force and getattr(refresh_code_index, "_already_forced", False):
         return "⚠️ [WARNING]: You already performed a FORCE REFRESH in this session. Re-indexing again will not solve the issue. Please check 'get_workspace_summary' or call 'read_file' directly on specific paths to verify local contents."
    
    if force:
        refresh_code_index._already_forced = True

    logger.info("code_intelligence.refresh_index_triggered", force=force)
    stats = memory_manager.indexer.index_project(force=force)
    
    return (
        f"📊 **Index Refresh Complete**:\n"
        f"- Files Scanned: {stats['files_scanned']}\n"
        f"- Files Indexed: {stats['files_indexed']}\n"
        f"- Total Chunks: {stats['chunks_total']}\n"
        f"- Stale Entries Removed: {stats['stale_removed']}"
    )

@agent_tool
def find_code_usages(symbol_name: str, **kwargs) -> str:
    """
    [STRICT: CODE ONLY] Uses RAG to find where a specific programming symbol (class, function, variable) 
    is used across the codebase. DO NOT use this for general knowledge, history, or content search.
    """
    context = memory_manager.get_context_block(query=f"where is {symbol_name} used or defined?", n_results=10)
    if not context.strip():
        return f"No clear usages found for '{symbol_name}' in semantic memory."
    return context

@agent_tool
def apply_ast_patch(path: str, target_name: str, new_code: str, **kwargs) -> str:
    """
    [v3.8.8] Precision Delta-Coding (HITL). 
    Replaces a specific Function or Class by its name using AST manipulation.
    Requires Commander's approval via Telegram before applying.
    """
    import ast
    import re
    if not os.path.exists(path):
        return f"❌ [PATCH]: File not found: {path}."
        
    # [v3.8.11] Extension Guard: Prevent blind AST on non-Python files
    if not path.lower().endswith(".py"):
        return f"❌ [PATCH REJECTED]: File '{path}' is not a Python file. AST manipulation (apply_ast_patch) ONLY supports .py files. For .md, .sql, .json or .txt, you MUST use 'write_file' or 'append_to_file' instead."
        
    try:
        # 1. Verification Preview
        preview = f"🛠️ **PATCH PROPOSAL** for `{path}`:\n🎯 **Target**: `{target_name}`\n\n```python\n{new_code[:300]}...\n```\nApply this patch?"
        confirmed = ask_user_confirmation(text=preview)
        if not confirmed:
            return "❌ [REFUSED]: Patch cancelled by Commander."

        # 2. Logic (formerly patch_protocol)
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
            original_lines = source.splitlines(keepends=True)

        tree = ast.parse(source)
        target_node = None
        for node in ast.walk(tree):
            if hasattr(node, "name") and node.name == target_name:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    target_node = node
                    break
        
        if not target_node:
            return f"❌ [PATCH]: Node '{target_name}' not found."
            
        start_ln = target_node.lineno
        end_ln = target_node.end_lineno
        
        # Indentation Matching
        first_line_orig = original_lines[start_ln-1]
        indentation = first_line_orig[:len(first_line_orig) - len(first_line_orig.lstrip())]
        
        new_lines = new_code.splitlines(keepends=True)
        final_new_lines = []
        for line in new_lines:
            if line.strip() and not line.startswith((' ', '\t')):
                final_new_lines.append(indentation + line)
            else:
                final_new_lines.append(line)
        
        if final_new_lines and not final_new_lines[-1].endswith('\n'):
            final_new_lines[-1] += '\n'

        # Integrity Check
        lazy_patterns = [r"//\s*code\s*will\s*be", r"#\s*placeholder", r"\.\.\.\s*existing\s*code"]
        for pattern in lazy_patterns:
            if re.search(pattern, new_code, re.IGNORECASE):
                return f"❌ [LAZY CODE REJECTED]: Placeholder detected ('{pattern}')."

        modified_lines = original_lines[:start_ln - 1] + final_new_lines + original_lines[end_ln:]
        new_content = "".join(modified_lines)
        
        # Verify result is syntactically valid
        ast.parse(new_content)
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
            
        memory_manager.reindex_file(path)
        return f"✅ [PATCH SUCCESS]: '{target_name}' updated in {path}."
        
    except Exception as e:
        return f"🔥 [PATCH ERROR]: {str(e)}"

EXPORTED_TOOLS = [refactor_code, find_code_usages, refresh_code_index, verify_code, apply_ast_patch]
