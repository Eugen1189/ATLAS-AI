"""
Code Analyzer - модуль самоусвідомлення ATLAS.
Дозволяє аналізувати структуру проекту, знаходити залежності та генерувати roadmap.
Zero-Dependency: Використовує тільки стандартні бібліотеки Python (ast, os).
"""

import os
import ast
import json
from pathlib import Path
from typing import Dict, List, Optional

class CodeAnalyzer:
    """
    Аналізатор коду для ATLAS.
    Сканує проект, розуміє структуру і готує звіт для LLM.
    """
    
    def __init__(self, ignore_patterns: List[str] = None):
        self.ignore_patterns = ignore_patterns or [
            ".git", "venv", "__pycache__", "node_modules", 
            ".idea", ".vscode", "dist", "build", "generated_images",
            "audio_output", "Screenshots", "memories", ".pytest_cache"
        ]

    def _is_ignored(self, path: str) -> bool:
        """Перевіряє, чи треба ігнорувати шлях."""
        for pattern in self.ignore_patterns:
            if pattern in path:
                return True
        return False

    def get_file_structure(self, root_path: str) -> Dict[str, str]:
        """
        Сканує структуру файлів проекту.
        Повертає словник {шлях: тип}.
        """
        structure = {}
        root = Path(root_path)
        
        for path in root.rglob("*"):
            if self._is_ignored(str(path)):
                continue
                
            if path.is_file():
                # Зберігаємо відносний шлях
                rel_path = str(path.relative_to(root))
                structure[rel_path] = "file"
            elif path.is_dir():
                # Для папок теж можна зберігати, але rglob і так проходить все
                pass
                
        return structure

    def analyze_python_file(self, file_path: str) -> Dict:
        """
        Аналізує Python файл за допомогою AST.
        Витягує імпорти, класи, функції та docstrings.
        """
        try:
            if os.path.getsize(file_path) > 100 * 1024: # 100KB limit
                return {"error": "File too large (>100KB)"}
                
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            info = {
                "imports": [],
                "classes": {},
                "functions": {},
                "docstring": ast.get_docstring(tree)
            }
            
            for node in ast.walk(tree):
                # Imports
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        info["imports"].append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module if node.module else ""
                    for alias in node.names:
                        info["imports"].append(f"{module}.{alias.name}")
                
                # Classes
                elif isinstance(node, ast.ClassDef):
                    class_doc = ast.get_docstring(node)
                    methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                    info["classes"][node.name] = {
                        "doc": class_doc,
                        "methods": methods
                    }
                
                # Functions (top-level)
                elif isinstance(node, ast.FunctionDef):
                    # Check if it's top level by seeing if it's directly pending extraction
                    # Але ast.walk плоский. Тому просто додамо всі функції, 
                    # хоча методи класів теж потраплять сюди.
                    # Можна покращити через NodeVisitor, але для MVP вистачить.
                    if not getattr(node, "name", "").startswith("_"): # Skip private
                         info["functions"][node.name] = ast.get_docstring(node)

            return info
        except Exception as e:
            return {"error": str(e)}

    def scan_project(self, root_path: str) -> Dict:
        """
        Комплексне сканування проекту.
        """
        print(f"🔍 [ANALYZER] Сканую проект: {root_path}")
        
        project_data = {
            "root": root_path,
            "structure": [],
            "analysis": {}
        }
        
        # 1. Structure
        files_map = self.get_file_structure(root_path)
        project_data["structure"] = list(files_map.keys())
        
        # 2. Logic Scrutiny (Python files)
        py_files = [f for f in files_map.keys() if f.endswith(".py")]
        
        for rel_path in py_files:
            abs_path = os.path.join(root_path, rel_path)
            analysis = self.analyze_python_file(abs_path)
            project_data["analysis"][rel_path] = analysis
            
        return project_data

    def generate_roadmap_prompt(self, project_data: Dict) -> str:
        """
        Генерує промпт для LLM на основі зібраних даних.
        """
        # Стиснення даних для промпту (щоб не перевищити ліміт токенів)
        summary = {
            "files_count": len(project_data["structure"]),
            "python_files": list(project_data["analysis"].keys()),
            "key_modules_info": {}
        }
        
        # Беремо деталі тільки для важливих файлів (не __init__, не config)
        for path, info in project_data["analysis"].items():
            if "error" in info: continue
            if "__init__" in path: continue
            
            summary["key_modules_info"][path] = {
                "classes": list(info["classes"].keys()),
                "doc": info["docstring"] or "No description",
                "imports": info["imports"][:5] # Top 5 imports
            }
        
        prompt = f"""
        ACT AS: Senior Software Architect & Tech Lead.
        TASK: Perform a "Contextual Onboarding" based on the project metadata below.
        
        PROJECT METADATA:
        {json.dumps(summary, indent=2)}
        
        Please provide a concise Actionable Report:
        1. **Architecture Overview**: What is this project? (Tech stack, patterns).
        2. **Weak Spots**: Potential vulnerabilities or technical debt based on file structure/imports.
        3. **Roadmap**: 3 concrete next steps to improve this codebase.
        
        Tone: Professional, Insightful, "Zero-Dependency Style".
        """
        return prompt
