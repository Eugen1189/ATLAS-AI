import pytest
import os
import json
import tempfile
from unittest.mock import MagicMock, patch

# Mock core.i18n
from core.i18n import lang
lang.get = MagicMock(side_effect=lambda key, **kwargs: f"Mocked {key}")

# Now import the actual skills with the real @agent_tool wrapper
from agent_skills.file_master.manifest import _resolve_path, list_directory, open_item, write_file, read_file
from agent_skills.terminal_operator.manifest import execute_command, _check_safety
from agent_skills.audio_interface.manifest import speak
from agent_skills.telegram_bridge.manifest import send_telegram_message, send_telegram_photo

@pytest.fixture
def mock_env():
    with patch.dict(os.environ, {
        "TELEGRAM_BOT_TOKEN": "123456:ABC",
        "TELEGRAM_CHAT_ID": "987654321"
    }):
        yield

# --- TEST FILE MASTER ---

def test_write_and_read_json():
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Use a path within the temp directory
        fname = "axis_test.txt"
        fpath = os.path.join(tmp_dir, fname)
        content = "Modern AXIS v2.7.7"
        
        # Test Write
        write_res = write_file(fpath, content)
        data = json.loads(write_res)
        assert data["status"] == "success"
        assert os.path.exists(fpath)
        
        # Test Read
        read_res = read_file(fpath)
        rdata = json.loads(read_res)
        assert rdata["status"] == "success"
        assert content in rdata["content"]

def test_list_directory_json():
    with tempfile.TemporaryDirectory() as tmp_dir:
        os.makedirs(os.path.join(tmp_dir, "subdir"))
        fpath = os.path.join(tmp_dir, "file.txt")
        with open(fpath, "w") as f: f.write("test")
        
        res = list_directory(tmp_dir)
        data = json.loads(res)
        assert data["status"] == "success"
        assert "subdir/" in data["content"]
        assert "file.txt" in data["content"]

def test_resolve_path_magic_words():
    with patch("os.getlogin", return_value="testuser"):
        # Selective mock for expanduser: only replace '~'
        original_expanduser = os.path.expanduser
        def side_effect(path):
            if path == "~": return "C:\\Users\\testuser"
            return original_expanduser(path)
            
        with patch("os.path.expanduser", side_effect=side_effect):
            # Test Desktop expansion
            path = _resolve_path("Desktop/my_file.txt")
            path_norm = path.replace("\\", "/")
            assert "C:/Users/testuser/Desktop/my_file.txt" in path_norm

from agent_skills.vision_eye.manifest import take_screenshot

def test_take_screenshot_success():
    with patch("core.vision_engine.vision_engine.capture_screen", return_value="C:\\shots\\sc.png"):
        res = take_screenshot()
        data = json.loads(res)
        assert data["status"] == "success"
        assert "C:\\shots\\sc.png" in data["content"]

def test_open_item_windows_success():
    with patch("platform.system", return_value="Windows"):
        with patch("os.path.exists", return_value=True):
            with patch("os.startfile") as mock_start:
                res = open_item("C:\\test.txt")
                data = json.loads(res)
                assert data["status"] == "success"
                assert "✅ [OPENED]" in data["content"]
                mock_start.assert_called_once()

# --- TEST TERMINAL OPERATOR ---

def test_terminal_firewall_blocks_danger():
    danger = _check_safety("del C:\\Windows\\System32\\hal.dll")
    assert danger is not None
    danger = _check_safety("format C:")
    assert danger is not None
    safe = _check_safety("dir /w")
    assert safe is None

def test_execute_command_blocked_returns_json():
    res_json = execute_command("del system32")
    data = json.loads(res_json)
    assert data["status"] == "success"
    # Even though blocked, it returns 'success' to LLM but with System Instruction
    assert "заблокована Фаєрволом" in data["content"]
    assert "SYSTEM_INSTRUCTION" in data

@patch("subprocess.Popen")
def test_execute_command_success(mock_popen):
    mock_proc = MagicMock()
    mock_proc.communicate.return_value = (b"Volume in drive C is OS", b"")
    mock_proc.returncode = 0
    mock_popen.return_value = mock_proc
    
    res = execute_command("vol")
    data = json.loads(res)
    assert data["status"] == "success"
    assert "🚀 [SUCCESS]" in data["content"]
    assert "Volume in drive C is OS" in data["content"]

# --- TEST AUDIO INTERFACE ---

@patch("pyttsx3.init")
def test_speak_local_tts(mock_ttsx3_init):
    mock_engine = MagicMock()
    mock_ttsx3_init.return_value = mock_engine
    mock_engine.getProperty.return_value = []
    
    res = speak("Hello world")
    data = json.loads(res)
    assert data["status"] == "success"
    assert "Vocal confirmation" in data["content"]
    mock_engine.say.assert_called_with("Hello world")
    mock_engine.runAndWait.assert_called_once()

# --- TEST TELEGRAM BRIDGE ---

@patch("requests.post")
def test_send_telegram_msg_success(mock_post, mock_env):
    mock_post.return_value.status_code = 200
    res = send_telegram_message("Status report: OK")
    data = json.loads(res)
    assert data["status"] == "success"
    assert "✅ Повідомлення успішно відправлено" in data["content"]
    
    args, kwargs = mock_post.call_args
    assert "sendMessage" in args[0]
    assert kwargs["json"]["text"] == "Status report: OK"

@patch("requests.post")
@patch("os.path.exists", return_value=True)
@patch("builtins.open", new_callable=MagicMock)
def test_send_telegram_photo(mock_open, mock_exists, mock_post, mock_env):
    mock_post.return_value.status_code = 200
    res = send_telegram_photo("C:\\temp\\image.png", caption="Test Pic")
    data = json.loads(res)
    assert data["status"] == "success"
    assert "успішно відправлено" in data["content"]
    
    args, _ = mock_post.call_args
    assert "sendPhoto" in args[0]
