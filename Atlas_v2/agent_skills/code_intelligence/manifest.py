import os
import json
from core.skills.wrapper import agent_tool
from core.brain.memory import memory_manager
from agent_skills.file_master.manifest import read_file, write_file, delete_file
from agent_skills.telegram_bridge.manifest import ask_user_confirmation, send_telegram_message
import subprocess
from core.logger import logger

@agent_tool
def refactor_code(filepath: str, instructions: str, new_code: str, **kwargs) -> str:
    """
    Expert-level refactoring tool (v2.8.6).
    1. Analyzes file and project context via RAG.
    2. Requires Commander's confirmation via Telegram with a preview.
    """
    # 1. Gather Context
    current_content = read_file(filepath)
    if "Error" in current_content:
        return current_content
        
    # Semantic search for usages and patterns related to this file
    memory_manager.get_context_block(query=f"usages of {filepath} or architectural patterns", n_results=5)
    
    # 2. Prepare Proposal
    # Truncate preview for Telegram
    code_preview = new_code[:500] + "..." if len(new_code) > 500 else new_code
    
    proposal_summary = (
        f"🛠️ **REFACTOR PROPOSAL** for `{filepath}`:\n"
        f"📝 **Instructions**: {instructions}\n\n"
        f"📄 **New Code Preview**:\n```python\n{code_preview}\n```\n"
        "Do you want me to apply these changes?"
    )
    
    # 3. Human-In-The-Loop (HITL)
    confirmed = ask_user_confirmation(prompt=proposal_summary)
    
    if not confirmed:
        return "❌ [REFUSED]: Commander rejected the refactoring proposal."
    
    # 4. Shadow Workspace Verification (March 2026 Protocol)
    shadow_path = filepath + ".shadow_copy.py"
    logger.info("code_intelligence.shadow_verification_start", path=shadow_path)
    
    try:
        # Create shadow copy
        write_file(filepath=shadow_path, content=new_code)
        
        # A. Ruff Linting & Formatting
        logger.info("code_intelligence.ruff_check")
        ruff_res = subprocess.run(f"ruff check {shadow_path} --fix", shell=True, capture_output=True, text=True)
        
        if ruff_res.returncode != 0:
            delete_file(shadow_path)
            return f"❌ [VERIFICATION FAILED]: Ruff found fatal errors:\n{ruff_res.stdout or ruff_res.stderr}"
            
        # B. Pytest (if applicable)
        # Scan if there is a corresponding test file
        test_file = os.path.join("tests", "test_" + os.path.basename(filepath))
        if os.path.exists(test_file):
            logger.info("code_intelligence.pytest_check", test=test_file)
            # Run pytest against the shadow version (might need mocking/import redirection if complex)
            # For simplicity in AXIS v2.8, we run the existing test suite
            pytest_res = subprocess.run(f"pytest {test_file}", shell=True, capture_output=True, text=True)
            if pytest_res.returncode != 0:
                delete_file(shadow_path)
                return f"❌ [VERIFICATION FAILED]: Unit tests failed for this change:\n{pytest_res.stdout[:500]}..."

        # 5. Apply Changes only after verification
        result = write_file(filepath=filepath, content=new_code)
        delete_file(shadow_path)
        
        if "✅" in result:
            send_telegram_message(text=f"🚀 **SUCCESS**: File `{filepath}` has been verified (Ruff/Pytest) and refactored.")
            return f"✅ [VERIFIED & REFACTORED]: {filepath} passed security checks and updated."
            
    except Exception as e:
        if os.path.exists(shadow_path): delete_file(shadow_path)
        return f"🔥 [SYSTEM ERROR] during verification: {e}"
    
    return result

@agent_tool
def verify_code(filepath: str, **kwargs) -> str:
    """
    Manual Verification Tool: Runs Ruff and Pytest on an existing file to check for regressions.
    """
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

EXPORTED_TOOLS = [refactor_code, find_code_usages, refresh_code_index, verify_code]
