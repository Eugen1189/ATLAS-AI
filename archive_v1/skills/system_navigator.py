
import os
import subprocess
import time

class SystemNavigator:
    """
    Abstractions for controlling Windows UI using native PowerShell and Win32 C# Interop.
    This module works without external dependencies like pywinauto or pyautogui.
    """
    def __init__(self):
        pass

    def _execute_ps(self, script: str):
        """Executes a PowerShell script without opening a console window."""
        try:
            # We wrap the script in a way that handles execution policy and no profile for speed
            cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script]
            
            # Using creationflags to hide the window
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=startupinfo,
                text=True
            )
            stdout, stderr = process.communicate()
            if stderr:
                print(f"⚠️ [NAVIGATOR] PS Error: {stderr.strip()}")
            return stdout.strip()
        except Exception as e:
            print(f"❌ [NAVIGATOR] Execution Failed: {e}")
            return None

    def get_screen_size(self):
        """Returns the primary screen resolution (width, height)"""
        script = """
        Add-Type -AssemblyName System.Windows.Forms
        $Screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
        Write-Output "$($Screen.Width),$($Screen.Height)"
        """
        output = self._execute_ps(script)
        if output:
            try:
                 parts = output.strip().split(',')
                 if len(parts) >= 2:
                     w = int(parts[0].strip())
                     h = int(parts[1].strip())
                     return w, h
            except ValueError:
                pass
        return 1920, 1080 # Fallback

    def open_app(self, app_name: str):
        """Opens an application by name."""
        print(f"🖥️ [NAVIGATOR] Opening {app_name}...")
        try:
            # Common mappings to safe, known executable names or full paths
            apps = {
                "chrome": "chrome",
                "notepad": "notepad",
                "calc": "calc",
                "calculator": "calc",
                "explorer": "explorer",
                "cmd": "cmd",
                "terminal": "wt",
                "code": "code",
                "cursor": "cursor",
                "spotify": "spotify",
                "telegram": "telegram"
            }

            cmd = apps.get(app_name.lower(), app_name)

            # 🔒 FIX: Use os.startfile() instead of shell=True to prevent injection
            # os.startfile() is Windows-only but safe — no shell interpolation
            try:
                os.startfile(cmd)
            except FileNotFoundError:
                return f"❌ Application not found: {cmd}"
            except OSError as e:
                return f"❌ Failed to open {app_name}: {e}"

            time.sleep(1.5)  # Smart Wait: Give Windows time to render
            return f"✅ Opened {app_name}"
        except Exception as e:
            return f"❌ Failed to open {app_name}: {e}"

    def type_text(self, text: str):
        """Types text into the active window using SendKeys."""
        print(f"⌨️ [NAVIGATOR] Typing: {text}")
        # Escape single quotes for PowerShell
        safe_text = text.replace("'", "''")
        
        script = f"""
        Add-Type -AssemblyName System.Windows.Forms
        [System.Windows.Forms.SendKeys]::SendWait('{safe_text}')
        """
        self._execute_ps(script)
        return f"✅ Typed '{text}'"

    def press_key(self, key: str):
        """Presses a specific key using SendKeys."""
        print(f"⌨️ [NAVIGATOR] Pressing: {key}")
        # Map common names to SendKeys format
        key_map = {
            "enter": "{ENTER}",
            "tab": "{TAB}",
            "esc": "{ESC}",
            "backspace": "{BACKSPACE}",
            "delete": "{DELETE}",
            "up": "{UP}",
            "down": "{DOWN}",
            "left": "{LEFT}",
            "right": "{RIGHT}",
            "home": "{HOME}",
            "end": "{END}",
            "f5": "{F5}",
            "win": "^{ESC}" # Ctrl+Esc simulates Win key mostly
        }
        
        send_key = key_map.get(key.lower(), key)
        
        script = f"""
        Add-Type -AssemblyName System.Windows.Forms
        [System.Windows.Forms.SendKeys]::SendWait('{send_key}')
        """
        self._execute_ps(script)
        return f"✅ Pressed {key}"

    def click_at(self, x, y):
        """Clicks at specific coordinates using C# P/Invoke via PowerShell."""
        print(f"🖱️ [NAVIGATOR] Clicking at ({x}, {y})")
        
        script = f"""
        $code = @'
[DllImport("user32.dll")] public static extern bool SetCursorPos(int X, int Y);
[DllImport("user32.dll")] public static extern void mouse_event(int dwFlags, int dx, int dy, int cButtons, int dwExtraInfo);
'@
        
        $type = Add-Type -MemberDefinition $code -Name Win32 -Namespace Win32Utils -PassThru
        $type::SetCursorPos({x}, {y})
        Start-Sleep -Milliseconds 50
        $type::mouse_event(0x0002, 0, 0, 0, 0) # Left Down
        Start-Sleep -Milliseconds 50
        $type::mouse_event(0x0004, 0, 0, 0, 0) # Left Up
        """
        self._execute_ps(script)
        return f"✅ Clicked at ({x}, {y})"

    def get_active_window_ui(self):
        """
        Retrieves the UI tree of the active window using System.Windows.Automation.
        Returns a list of dictionaries containing element info (Name, ControlType).
        Zero-Dependency: Uses native PowerShell and .NET.
        """
        script = """
        try {
            Add-Type -AssemblyName UIAutomationClient
            Add-Type -AssemblyName UIAutomationTypes
            
            $code = @'
[DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
'@
            $win32 = Add-Type -MemberDefinition $code -Name Win32Utils -Namespace User32 -PassThru
            $handle = $win32::GetForegroundWindow()
            
            if ($handle -eq [IntPtr]::Zero) {
                Write-Output "No Active Window"
                exit
            }

            $element = [System.Windows.Automation.AutomationElement]::FromHandle($handle)
            $condition = [System.Windows.Automation.Condition]::TrueCondition
            $walker = [System.Windows.Automation.TreeWalker]::ControlViewWalker
            
            # Helper function to walk tree (simplified, non-recursive for speed or limited depth)
            # Actually, let's just get direct children for now, or use FindAll
            
            $children = $element.FindAll([System.Windows.Automation.TreeScope]::Descendants, $condition)
            
            $result = @()
            foreach ($child in $children) {
                try {
                    if (-not [string]::IsNullOrWhiteSpace($child.Current.Name)) {
                         $info = @{
                            Name = $child.Current.Name
                            Type = $child.Current.ControlType.ProgrammaticName
                            Rect = $child.Current.BoundingRectangle.ToString()
                        }
                        $result += $info
                    }
                } catch {}
            }
            
            # Output as JSON for easy parsing in Python
            $result | ConvertTo-Json -Depth 2 -Compress
        } catch {
            Write-Output "Error: $_"
        }
        """
        output = self._execute_ps(script)
        
        # Parse JSON output
        try:
            import json
            if output and output.strip() and not output.startswith("Error"):
                return json.loads(output)
            return []
        except Exception as e:
            print(f"⚠️ [NAVIGATOR] Failed to parse UI tree: {e}")
            return []

    def get_screen_hash(self):
        """
        Calculates a hash of the current screen content (resized) to detect changes.
        Efficient: Does not save to disk, runs in memory.
        """
        script = """
        Add-Type -AssemblyName System.Windows.Forms
        Add-Type -AssemblyName System.Drawing
        
        $Screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
        $Bitmap = New-Object System.Drawing.Bitmap $Screen.Width, $Screen.Height
        $Graphics = [System.Drawing.Graphics]::FromImage($Bitmap)
        $Graphics.CopyFromScreen($Screen.X, $Screen.Y, 0, 0, $Bitmap.Size)
        
        # Resize to small thumbnail for fast robust hashing (ignores minor noise)
        $Small = $Bitmap.GetThumbnailImage(64, 64, $null, [IntPtr]::Zero)
        
        $Stream = New-Object System.IO.MemoryStream
        $Small.Save($Stream, [System.Drawing.Imaging.ImageFormat]::Png)
        $Bytes = $Stream.ToArray()
        
        $MD5 = [System.Security.Cryptography.MD5]::Create()
        $Hash = [BitConverter]::ToString($MD5.ComputeHash($Bytes))
        
        Write-Output $Hash
        
        $Graphics.Dispose()
        $Bitmap.Dispose()
        $Small.Dispose()
        $Stream.Dispose()
        """
        return self._execute_ps(script)


    def click_element(self, element_name):
        """
        Attempts to click a named element. 
        Without Accessibility API, we can't do this reliably.
        """
        return f"⚠️ Start typing coordinates or switch to Vision mode. Coordinates unknown for '{element_name}'."

    def scroll(self, amount):
        """Scrolls the mouse wheel is complex in vanilla PS, skipping for now."""
        return "⚠️ Scroll not implemented in Zero-Dependency mode."

    def take_screenshot(self, save_path="screenshot.png"):
        """
        Takes a screenshot using native PowerShell .NET System.Drawing.
        No external libraries required.
        """
        try:
            import os
            # Ensure path is absolute for PS
            abs_path = os.path.abspath(save_path)
            
            script = f"""
            Add-Type -AssemblyName System.Windows.Forms
            Add-Type -AssemblyName System.Drawing
            
            $Screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
            $Bitmap = New-Object System.Drawing.Bitmap $Screen.Width, $Screen.Height
            $Graphics = [System.Drawing.Graphics]::FromImage($Bitmap)
            $Graphics.CopyFromScreen($Screen.X, $Screen.Y, 0, 0, $Bitmap.Size)
            
            $Bitmap.Save('{abs_path}', [System.Drawing.Imaging.ImageFormat]::Png)
            $Graphics.Dispose()
            $Bitmap.Dispose()
            Write-Output "Saved to {abs_path}"
            """
            
            self._execute_ps(script)
            
            if os.path.exists(abs_path):
                 return abs_path
            return None
        except Exception as e:
            print(f"❌ [NAVIGATOR] Screenshot failed: {e}")
            return None
