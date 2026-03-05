from core.i18n import lang
from typing import Dict
import os
import json
from pathlib import Path

def analyze_performance() -> str:
    """
    Reads the logs and analyzes execution times of skills to find bottlenecks.
    Use this for the Self-Optimization Sprint.
    """
    log_dir = Path(__file__).parent.parent.parent.parent / "logs"
    log_file = log_dir / "axis.log"
    
    if not log_file.exists():
        return "No axis.log found for performance analysis."
        
    timings = {}
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if data.get("event") == "performance.timing":
                        func = data.get("function")
                        dur = data.get("duration_sec", 0)
                        if func not in timings:
                            timings[func] = []
                        timings[func].append(dur)
                except Exception:
                    pass
                    
        if not timings:
            return "No performance timings found in logs yet. Add @time_it decorator to functions to analyze them."
            
        report = "AXIS Performance Analysis:\n"
        for func, durs in timings.items():
            avg = sum(durs) / len(durs)
            max_d = max(durs)
            report += f"- {func}: Avg {avg:.3f}s | Max {max_d:.3f}s | Min {min(durs):.3f}s (Called {len(durs)} times)\n"
            
        return report
    except Exception as e:
        return f"Error analyzing performance: {str(e)}"

EXPORTED_TOOLS = [analyze_performance]
