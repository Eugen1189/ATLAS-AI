import os
"""
AXIS Environment Discovery Module
Performs deep system scanning (Registry, PATH, Hardware) to identify installed
IDEs, dev tools, and GPU capabilities.
"""

import sys
import shutil
import subprocess
import socket
import json
try:
    import winreg
    WINDOWS = True
except ImportError:
    WINDOWS = False

import psutil
from pathlib import Path
from core.logger import logger

class EnvironmentDiscoverer:
    """
    Scans the local machine for developer environment markers.
    Identifies IDEs, CLI tools, Workspace structure, and Hardware specs.
    """

    IDEs = {
        "VS Code": {"cmd": "code", "reg_paths": [
            r"Software\Microsoft\Windows\CurrentVersion\Uninstall\{EA457B26-2175-467E-B843-BA5638A37562}_is1",
            r"Software\Microsoft\Windows\CurrentVersion\Uninstall\Visual Studio Code",
        ]},
        "Cursor": {"cmd": "cursor", "reg_paths": [
            r"Software\Microsoft\Windows\CurrentVersion\Uninstall\Cursor",
        ]},
        "PyCharm": {"cmd": "pycharm", "reg_paths": [
            r"Software\Microsoft\Windows\CurrentVersion\Uninstall\PyCharm Community Edition",
            r"Software\Microsoft\Windows\CurrentVersion\Uninstall\PyCharm Professional Edition",
        ]},
        "Zed": {"cmd": "zed", "reg_paths": [
            r"Software\Microsoft\Windows\CurrentVersion\Uninstall\Zed",
        ]},
    }

    DEV_TOOLS = ["python", "git", "docker", "node", "npm", "ollama", "pip", "rustc", "go"]

    findings = {
        "ides": {},
        "tools": {},
        "hardware": {"ram_gb": 0, "cpu_count": 0, "gpu": "Unknown"},
        "workspaces": [],
        "primary_workspace": None
    }

    def __init__(self, memory_manager=None):
        self.memory_manager = memory_manager

    def scan_ides(self) -> dict:
        """
        Scans for IDEs using Registry (Windows) and PATH (Universal).
        """
        logger.debug("discovery.ide_scan_started")
        installed = {}

        for name, config in self.IDEs.items():
            found_path = None
            
            # 1. Registry Scan (Windows only)
            if WINDOWS:
                roots = [winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE]
                for root in roots:
                    for subkey in config["reg_paths"]:
                        try:
                            with winreg.OpenKey(root, subkey) as key:
                                path, _ = winreg.QueryValueEx(key, "InstallLocation")
                                if path:
                                    found_path = path
                                    break
                        except (FileNotFoundError, OSError):
                            continue
                    if found_path: break

            # 2. PATH Scan (Universal)
            if not found_path:
                cmd_path = shutil.which(config["cmd"])
                if cmd_path:
                    found_path = os.path.dirname(cmd_path)
                    logger.debug("discovery.ide_found_on_path", ide=name, cmd=config["cmd"])

            if found_path:
                installed[name] = found_path
                logger.debug("discovery.ide_located", ide=name, path=found_path)

        self.findings["ides"] = installed
        return installed

    def scan_path_for_tools(self) -> dict:
        """
        Checks for presence and versions of development CLI tools.
        """
        logger.debug("discovery.tool_scan_started")
        tools = {}

        for tool in self.DEV_TOOLS:
            path = shutil.which(tool)
            if path:
                version = "unknown"
                try:
                    cmd = [tool, "--version"]
                    if tool == "python": cmd = [tool, "-V"]
                    output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=2)
                    version = output.decode().strip()
                except Exception: pass

                tools[tool] = {"path": path, "version": version}
                logger.debug("discovery.tool_found", tool=tool, version=version)

        self.findings["tools"] = tools
        return tools

    def scan_hardware(self) -> dict:
        """
        Identifies CPU, RAM and GPU (NVIDIA preferred for Ollama).
        """
        logger.debug("discovery.hardware_scan_started")
        hw = {
            "ram_gb": round(psutil.virtual_memory().total / (1024**3), 1),
            "cpu_count": psutil.cpu_count(logical=True),
            "gpu": "None detected"
        }

        # Check for GPU via nvidia-smi (NVIDIA)
        try:
            output = subprocess.check_output(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], timeout=2)
            hw["gpu"] = output.decode().strip()
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        self.findings["hardware"] = hw
        return hw

    def map_workspaces(self) -> list:
        """
        Zero-Config Workspace Discovery.
        Searches for markers: .git, .vscode, pyproject.toml, package.json
        """
        logger.debug("discovery.workspace_mapping_started")
        
        # 1. Start from current directory
        current = Path(os.getcwd()).resolve()
        markers = [".git", ".vscode", "pyproject.toml", "package.json", ".atlas", ".axis"]
        
        primary = None
        # Check parents to find project root
        for parent in [current] + list(current.parents):
            if any((parent / m).exists() for m in markers):
                primary = str(parent)
                logger.info("discovery.primary_workspace_detected", path=primary)
                break
        
        self.findings["primary_workspace"] = primary
        
        # 2. Known common locations
        search_dirs = [
            Path.home() / "Projects",
            Path.home() / "dev",
            current.parent # Check sibling folders
        ]
        
        found = []
        if primary: found.append(primary)
        
        for d in search_dirs:
            if d.exists() and d.is_dir():
                found.append(str(d))
        
        # Remove duplicates
        seen = set()
        unique_found = []
        for f in found:
            if f not in seen:
                unique_found.append(f)
                seen.add(f)

        self.findings["workspaces"] = unique_found
        return unique_found

    def run_full_discovery(self, store_in_memory: bool = True) -> dict:
        """
        Runs all discovery modules and consolidates findings.
        """
        logger.info("discovery.full_scan_started")

        self.scan_ides()
        self.scan_path_for_tools()
        self.scan_hardware()
        self.map_workspaces()

        if store_in_memory and self.memory_manager:
            self._inject_into_memory()

        # Send findings to HUD via UDP (Process Isolation Bridge)
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # Simplest payload for HUD
            hud_data = {
                "ides": self.findings["ides"],
                "hardware": self.findings["hardware"]
            }
            sock.sendto(json.dumps(hud_data).encode(), ("127.0.0.1", 5005))
        except Exception:
            pass # HUD might not be running

        return self.findings

    def _inject_into_memory(self):
        """
        Converts findings into semantic facts and injects into memory.
        """
        if not self.memory_manager:
            return

        # 1. Hardware facts
        hw = self.findings.get("hardware", {})
        self.memory_manager.remember_fact(
            f"System has {hw.get('ram_gb')}GB RAM and {hw.get('cpu_count')} CPU logical cores.",
            category="system_config"
        )
        if hw.get("gpu") and hw.get("gpu") != "None detected":
            gpu_str = hw.get("gpu")
            msg = f"GPU detected: {gpu_str}."
            if "NVIDIA" in gpu_str.upper() or "RTX" in gpu_str.upper():
                msg += " This is great for local Ollama models."
            self.memory_manager.remember_fact(msg, category="system_config")

        # 2. IDE facts
        ides = self.findings.get("ides", {})
        for name, path in ides.items():
            self.memory_manager.remember_fact(
                f"IDE {name} is installed at {path}. I can open projects here.",
                category="dev_tools"
            )

        # 3. Tool facts
        tools = self.findings.get("tools", {})
        for tool, info in tools.items():
            self.memory_manager.remember_fact(
                f"{tool.capitalize()} is available ({info['version']}) at {info['path']}.",
                category="dev_tools"
            )

        # 4. Workspace facts
        workspaces = self.findings.get("workspaces", [])
        if workspaces:
            list_str = ", ".join(workspaces)
            self.memory_manager.remember_fact(
                f"User seems to store projects in: {list_str}.",
                category="workspace"
            )

        logger.info("discovery.rag_injection_complete", facts_added=len(ides) + len(tools) + len(workspaces) + 2)


if __name__ == "__main__":
    # Self-test if run directly
    discoverer = EnvironmentDiscoverer()
    results = discoverer.run_full_discovery(store_in_memory=False)
    import json
    print(json.dumps(results, indent=2))
