import unittest
from unittest.mock import patch, mock_open
from core.i18n import LangModule

class TestI18n(unittest.TestCase):
    def test_get_logic(self):
        obj = object.__new__(LangModule)
        obj.texts = {
            "test": {
                "hello": "Hello, {name}!",
                "nested": {"key": "Value"}
            }
        }
        
        self.assertEqual(obj.get("test.nested.key"), "Value")
        self.assertEqual(obj.get("test.hello", name="AXIS"), "Hello, AXIS!")
        self.assertEqual(obj.get("missing"), "missing")

    def test_format_error(self):
        obj = object.__new__(LangModule)
        obj.texts = {"test": "Hello {missing}"}
        result = obj.get("test")
        self.assertIn("[fmt error:", result)

    @patch("builtins.open", new_callable=mock_open, read_data='{"test": "value"}')
    @patch("os.path.exists", return_value=True)
    def test_init_lang_success(self, mock_exists, mock_file):
        obj = object.__new__(LangModule)
        obj.language = "en"
        # We don't care about locales_dir since open is mocked
        obj._init_lang()
        self.assertEqual(obj.texts, {"test": "value"})

    @patch("builtins.open", side_effect=Exception("File not found"))
    def test_init_lang_fail_all(self, mock_file):
        obj = object.__new__(LangModule)
        obj.language = "en"
        obj._init_lang()
        self.assertEqual(obj.texts, {})

if __name__ == "__main__":
    unittest.main()
