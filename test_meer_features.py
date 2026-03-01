
import sys
import os
import time

sys.path.append(os.getcwd())

from skills.system_navigator import SystemNavigator
from skills.scenario_manager import ScenarioManager

def test_semantic_ui():
    print("--- Testing Semantic UI Map ---")
    nav = SystemNavigator()
    try:
        ui = nav.get_active_window_ui()
        print(f"UI Elements Found: {len(ui)}")
        if ui:
            print("Sample Element:", ui[0])
        else:
            print("No UI elements found (active window might be protected or empty).")
    except Exception as e:
        print(f"Error: {e}")

def test_diff_vision():
    print("\n--- Testing Diff-Driven Vision ---")
    nav = SystemNavigator()
    try:
        h1 = nav.get_screen_hash()
        print(f"Hash 1: {h1}")
        time.sleep(1)
        h2 = nav.get_screen_hash()
        print(f"Hash 2: {h2}")
        
        if h1 == h2:
            print("Hashes match (Screen static)")
        else:
            print("Hashes differ (Screen changed)")
    except Exception as e:
        print(f"Error: {e}")

def test_scenario_chain():
    print("\n--- Testing Scenario Chain ---")
    sm = ScenarioManager()
    
    # Mock ShellExecutor
    class MockShell:
        def execute(self, cmd):
            print(f"EXEC: {cmd}")
            return True, "Mock Output"
            
    steps = [
        "echo Start Chain",
        "CHAIN:ui_context",
        "CHAIN:wait:0.1",
        "CHAIN:ask:Should we proceed?"
    ]
    
    result = sm.execute_chain("test_chain", steps, MockShell())
    print("Chain Result:", result)

if __name__ == "__main__":
    test_semantic_ui()
    test_diff_vision()
    # test_scenario_chain() # Optional, just verify object creation
