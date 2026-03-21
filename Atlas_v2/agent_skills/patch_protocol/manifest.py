import ast
import os
from core.logger import logger
from core.skills.wrapper import agent_tool

@agent_tool
def apply_ast_patch(path: str, target_name: str, new_code: str, **kwargs) -> str:
    """
    Standard 2026 Delta-Coding (Patch Protocol). 
    Parses the file into an AST, locates the specifically named Function or Class node, and replaces it.
    This ensures only the relevant part of the file is modified, preserving comments and formatting elsewhere.
    """
    if not os.path.exists(path):
        current_ws = os.getcwd().replace("\\", "/").lower()
        return f"❌ [PATCH REJECTED]: File not found: {path}. Current workspace is {current_ws}. You are forbidden from jumping to other project folders like LegalMind unless explicitly ordered. Use 'list_directory' to verify your surroundings."
        
    try:
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
            # Splitlines(True) preserves the newline characters which is safer for exact reproduction
            original_lines = source.splitlines(keepends=True)

        tree = ast.parse(source)
        target_node = None
        
        # Search for FunctionDef or ClassDef
        for node in ast.walk(tree):
            if hasattr(node, "name") and node.name == target_name:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    target_node = node
                    break
        
        if not target_node:
            return f"❌ [PATCH]: Node '{target_name}' not found in {path}. Use 'list_functions' if unsure."
            
        # Get bounds (1-indexed from AST)
        start_ln = target_node.lineno  # 1-indexed
        end_ln = target_node.end_lineno # 1-indexed, inclusive
        
        logger.info("patch.applying", target=target_name, path=path, lines=f"{start_ln}-{end_ln}")
        
        # Prepare replacement lines
        # Determine original indentation of the node to maintain consistency
        # lines[start_ln-1] is the line where the node starts
        first_line_orig = original_lines[start_ln-1]
        indentation = first_line_orig[:len(first_line_orig) - len(first_line_orig.lstrip())]
        
        # Process new_code to match indentation if it's a raw body or fix it if it's a full node
        # User usually provides lines. We check if the first line starts with 'def' or 'class'
        new_lines = new_code.splitlines(keepends=True)
        if not new_lines:
            return "❌ [PATCH]: Replacement code is empty."

        final_new_lines = []
        for line in new_lines:
            # If the user didn't provide indentation, add original indentation
            if line.strip() and not line.startswith((' ', '\t')):
                final_new_lines.append(indentation + line)
            else:
                final_new_lines.append(line)
        
        # Ensure new lines end with a newline if they don't
        if final_new_lines and not final_new_lines[-1].endswith('\n'):
            final_new_lines[-1] += '\n'

        # Construct new content
        # Note: original_lines is 0-indexed. 
        # Range is [0, start_ln-2] + new_lines + [end_ln, ...]
        modified_lines = original_lines[:start_ln - 1] + final_new_lines + original_lines[end_ln:]
        new_content = "".join(modified_lines)
        
        # --- SEMANTIC INTEGRITY (2026 Safeguard) ---
        # 1. Preliminary check: Is the new snippet syntactically valid by itself?
        try:
            ast.parse(new_code.strip())
        except SyntaxError as se:
            logger.warning("patch.snippet_invalid", error=str(se))
            return f"❌ [SEMANTIC ERROR]: Your replacement code for '{target_name}' contains syntax errors: {se}. Patch rejected."

        # 1a. LAZY CODE DETECTION (2026 Safeguard)
        lazy_patterns = [
            r"//\s*code\s*will\s*be", 
            r"#\s*placeholder", 
            r"\.\.\.\s*existing\s*code",
            r"//\s*rest\s*of\s*the\s*code",
            r"#\s*rest\s*of\s*the\s*code"
        ]
        import re
        for pattern in lazy_patterns:
            if re.search(pattern, new_code, re.IGNORECASE):
                logger.error("patch.lazy_code_detected", pattern=pattern)
                return f"❌ [LAZY CODE REJECTED]: Placeholder detected ('{pattern}'). You MUST provide the full implementation of the function/class. Partial updates are forbidden."

        # 2. Construction
        modified_lines = original_lines[:start_ln - 1] + final_new_lines + original_lines[end_ln:]
        new_content = "".join(modified_lines)
        
        # 3. Final Integrity Check: Does the whole file remain valid?
        try:
            new_tree = ast.parse(new_content)
            
            # 4. Identity Check: Does the target node still exist and have the correct name?
            identity_found = False
            for node in ast.walk(new_tree):
                if hasattr(node, "name") and node.name == target_name:
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        identity_found = True
                        break
            
            if not identity_found:
                return f"❌ [INTEGRITY REJECTED]: The patch would accidentally rename or delete the target '{target_name}'. Action blocked."

        except SyntaxError as se:
            logger.error("patch.syntax_error", error=str(se))
            return f"❌ [SEMANTIC REJECTED]: The resulting file would have syntax errors. This usually means indentation mismatch. Patch discarded.\nDetails: {se}"
            
        # 5. Atomic Write (Only if all checks passed)
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
            
        from core.brain.memory import memory_manager
        memory_manager.reindex_file(path) # Keep RAG fresh
        
        return f"✅ [PATCH SUCCESS]: '{target_name}' updated in {path}. Delta-coding protocol applied."
        
    except Exception as e:
        logger.error("patch.unexpected_error", error=str(e))
        return f"🔥 [PATCH FATAL ERROR]: {str(e)}"

EXPORTED_TOOLS = [apply_ast_patch]
