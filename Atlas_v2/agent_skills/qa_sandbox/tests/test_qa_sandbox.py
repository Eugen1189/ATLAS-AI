import pytest
from agent_skills.qa_sandbox.manifest import example_tool

def test_example_tool():
    result = example_tool(param="test")
    assert "test" in result
