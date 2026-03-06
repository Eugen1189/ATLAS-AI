import json
import os

class Healer:
    def __init__(self, rules_path="memories/dynamic_rules.json"):
        self.rules_path = rules_path

    def summarize_evolution(self):
        """Виводить список вивчених правил при старті системи."""
        if os.path.exists(self.rules_path):
            with open(self.rules_path, 'r', encoding='utf-8') as f:
                rules = json.load(f)
            
            print("\n🧬 [AXIS EVOLUTION REPORT]")
            print("Learned Lessons (Dynamic Micro-Rules):")
            if not rules:
                print("- No rules learned yet. System is in baseline state.")
            for i, rule in enumerate(rules, 1):
                print(f"{i}. {rule}")
            print("-" * 30 + "\n")
        else:
            print("🧬 [AXIS EVOLUTION]: Baseline state. No dynamic rules found.")
