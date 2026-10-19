import unittest
from scripts.ai.seal_gemini_secret import validate_secret

class GeminiSecretFormatTests(unittest.TestCase):
    def test_google_authorization_and_legacy_keys(self):
        for key in ('AQ.'+'aB0_-.'*30,'AIza'+'b'*35,'AQ.'+'z'*315):
            self.assertEqual(validate_secret(key),key)

    def test_missing_malformed_and_oversize_secrets_are_redacted(self):
        for key in ('','x'*19,'x'*319,'AQ.'+'x'*30+'\n','AQ.'+'x'*30+' ','AQ.'+'é'*30):
            with self.subTest(length=len(key)):
                with self.assertRaises(ValueError) as error:
                    validate_secret(key)
                self.assertIn(str(error.exception),('GEMINI_SECRET_NOT_CONFIGURED','GEMINI_SECRET_FORMAT_INVALID'))
                if key:
                    self.assertNotIn(key,str(error.exception))
