
import sys
import os
import json

sys.path.append(os.getcwd())

from skills.code_analyzer import CodeAnalyzer

def test_code_analyzer():
    print("--- Testing Code Analyzer (Self-Awareness) ---")
    analyzer = CodeAnalyzer()
    
    current_dir = os.getcwd()
    print(f"Scanning directory: {current_dir}")
    
    project_data = analyzer.scan_project(current_dir)
    
    print(f"\nFiles found: {len(project_data['structure'])}")
    print("Sample structure:", project_data['structure'][:5])
    
    print(f"\nAnalyzed Python files: {len(project_data['analysis'])}")
    
    # Check analysis of this file or similar
    sample_file = "check_mic.py"
    if sample_file in project_data['analysis']:
        print(f"\nAnalysis for {sample_file}:")
        print(json.dumps(project_data['analysis'][sample_file], indent=2))
        
    # Generate prompt
    prompt = analyzer.generate_roadmap_prompt(project_data)
    print(f"\nGenerated Prompt Check (Length: {len(prompt)})")
    print(f"Prompt Preview:\n{prompt[:300]}...")

if __name__ == "__main__":
    test_code_analyzer()
