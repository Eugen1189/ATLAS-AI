import pytest
import os
import json
from core.brain.healer import Healer

def test_healer_summarize_evolution(capsys, tmpdir):
    # Setup a dummy rules file
    rules_path = os.path.join(tmpdir, "dynamic_rules.json")
    with open(rules_path, "w", encoding="utf-8") as f:
        json.dump(["Rule 1", "Rule 2"], f)
        
    healer = Healer(rules_path=rules_path)
    healer.summarize_evolution()
    
    captured = capsys.readouterr()
    assert "[AXIS EVOLUTION REPORT]" in captured.out
    assert "1. Rule 1" in captured.out
    assert "2. Rule 2" in captured.out
    
def test_healer_empty_rules(capsys, tmpdir):
    rules_path = os.path.join(tmpdir, "empty_rules.json")
    with open(rules_path, "w", encoding="utf-8") as f:
        json.dump([], f)
        
    healer = Healer(rules_path=rules_path)
    healer.summarize_evolution()
    
    captured = capsys.readouterr()
    assert "- No rules learned yet." in captured.out
    
def test_healer_no_file(capsys, tmpdir):
    rules_path = os.path.join(tmpdir, "missing_rules.json")
    healer = Healer(rules_path=rules_path)
    healer.summarize_evolution()
    
    captured = capsys.readouterr()
    assert "Baseline state. No dynamic rules found." in captured.out
