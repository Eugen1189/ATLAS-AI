# Import necessary libraries
import unittest
from legal_parser import parse_document

class TestLegalParser(unittest.TestCase):
    def test_parse_document_error(self):
        # Define a sample document for testing that intentionally causes an error
        document = 'Invalid legal text here'
        with self.assertRaises(Exception) as context:
            parse_document(document)
        expected_error_message = 'Error in parsing the document'
        self.assertIn(expected_error_message, str(context.exception))

def main():
    unittest.main()

if __name__ == '__main__':
    main()