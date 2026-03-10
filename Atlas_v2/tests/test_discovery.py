"""
Unit tests for EnvironmentDiscoverer.
"""

import unittest
from unittest.mock import patch, MagicMock
import os
import shutil


class TestEnvironmentDiscoverer(unittest.TestCase):
    """Tests for the Environment Discoverer logic."""

    def setUp(self):
        from core.system.discovery import EnvironmentDiscoverer
        self.discoverer = EnvironmentDiscoverer()

    @patch("winreg.OpenKey")
    @patch("winreg.QueryValueEx")
    def test_scan_registry_finds_vscode(self, mock_query, mock_open):
        """Should detect VS Code if registry key exists."""
        # Mocking winreg to 'find' VS Code
        mock_query.return_value = ("C:\\Program Files\\Microsoft VS Code", 1)
        
        # We need to mock OpenKey twice (once for HKEY_CURRENT_USER, once for HKEY_LOCAL_MACHINE)
        # and different subkeys. Simplest: return a handle for the specific VS Code key.
        mock_open.return_value = MagicMock()
        
        ides = self.discoverer.scan_registry_for_ide()
        self.assertIn("VS Code", ides)
        self.assertEqual(ides["VS Code"], "C:\\Program Files\\Microsoft VS Code")

    @patch("shutil.which")
    def test_scan_registry_fallback_to_path(self, mock_which):
        """Should detect IDE via PATH if registry scan fails."""
        # Mock winreg to fail
        with patch("winreg.OpenKey", side_effect=FileNotFoundError):
            # Mock shutil.which to 'find' cursor.exe
            mock_which.side_effect = lambda x: "C:\\bin\\cursor.exe" if x == "cursor" else None
            
            ides = self.discoverer.scan_registry_for_ide()
            self.assertIn("Cursor", ides)
            self.assertEqual(ides["Cursor"], "C:\\bin")

    @patch("shutil.which")
    @patch("subprocess.check_output")
    def test_scan_path_for_tools(self, mock_output, mock_which):
        """Should detect git and its version."""
        mock_which.side_effect = lambda x: "/usr/bin/git" if x == "git" else None
        mock_output.return_value = b"git version 2.40.1"
        
        tools = self.discoverer.scan_path_for_tools()
        self.assertIn("git", tools)
        self.assertEqual(tools["git"]["version"], "git version 2.40.1")

    @patch("psutil.virtual_memory")
    @patch("psutil.cpu_count")
    @patch("subprocess.check_output")
    def test_scan_hardware(self, mock_output, mock_cpu, mock_ram):
        """Should detect RAM and NVIDIA GPU."""
        mock_ram.return_value.total = 16 * (1024**3)
        mock_cpu.return_value = 8
        mock_output.return_value = b"NVIDIA GeForce RTX 3060"
        
        hw = self.discoverer.scan_hardware()
        self.assertEqual(hw["ram_gb"], 16.0)
        self.assertEqual(hw["cpu_count"], 8)
        self.assertEqual(hw["gpu"], "NVIDIA GeForce RTX 3060")

    @patch("os.path.isdir")
    def test_map_workspaces(self, mock_isdir):
        """Should find Projects directory if it exists."""
        mock_isdir.side_effect = lambda x: True if "Projects" in x else False
        
        workspaces = self.discoverer.map_workspaces()
        self.assertTrue(any("Projects" in w for w in workspaces))

    def test_rag_injection_format(self):
        """Should call remember_fact with formatted strings."""
        mock_mem = MagicMock()
        self.discoverer.memory_manager = mock_mem
        self.discoverer.findings = {
            "hardware": {"ram_gb": 32, "cpu_count": 12, "gpu": "RTX 4090"},
            "ides": {"VS Code": "C:/VSCode"},
            "tools": {"python": {"version": "3.12", "path": "/bin/python"}},
            "workspaces": ["C:/Projects"]
        }
        
        self.discoverer._inject_into_memory()
        
        # Verify it called remember_fact exactly once for hardware, once for IDE, etc.
        calls = [c.args[0] for c in mock_mem.remember_fact.call_args_list]
        self.assertTrue(any("32GB RAM" in c for c in calls))
        self.assertTrue(any("RTX 4090" in c for c in calls))
        self.assertTrue(any("VS Code" in c for c in calls))
        self.assertTrue(any("3.12" in c for c in calls))


if __name__ == "__main__":
    unittest.main()
