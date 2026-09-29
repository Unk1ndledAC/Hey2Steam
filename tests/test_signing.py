"""Unit tests for the HeyBox signing module.

Run with::

    python -m unittest tests.test_signing

or, from the project root::

    python -m pytest tests/
"""

import unittest

from hey2steam import signing


class TestByteTransforms(unittest.TestCase):
    """Hand-computed checks for the low-level byte primitives."""

    def test_vm(self):
        self.assertEqual(signing._vm(48), 96)    # 48 << 1
        self.assertEqual(signing._vm(102), 204)  # 102 << 1
        self.assertEqual(signing._vm(170), 79)   # 255 & ((170<<1)^27)

    def test_qm(self):
        self.assertEqual(signing._qm(48), 96 ^ 48)

    def test_normalize_path(self):
        self.assertEqual(signing._normalize_path("game/get_game_list_v3"),
                         "/game/get_game_list_v3/")
        self.assertEqual(signing._normalize_path("/a//b/"), "/a/b/")


class TestHkey(unittest.TestCase):
    PATH = "/game/get_game_list_v3"
    TS = 1726809839
    NONCE = "C8B6CB8884949DDE30311CC2281A9642"

    def test_web_format(self):
        key = signing.hkey(self.PATH, self.TS, self.NONCE, algo="web")
        self.assertIsInstance(key, str)
        self.assertEqual(len(key), 7)
        self.assertTrue(key[:5].isalnum())
        self.assertTrue(key[5:].isdigit())

    def test_chat_format(self):
        key = signing.hkey(self.PATH, self.TS, self.NONCE, algo="chat")
        self.assertIsInstance(key, str)
        self.assertEqual(len(key), 7)
        self.assertTrue(key[5:].isdigit())

    def test_deterministic(self):
        self.assertEqual(
            signing.hkey(self.PATH, self.TS, self.NONCE, algo="web"),
            signing.hkey(self.PATH, self.TS, self.NONCE, algo="web"),
        )

    def test_sensitive_to_input(self):
        # The "web" variant truncates the interleaved string to 20 chars, so
        # only the leading characters of each component influence the result.
        # Change a leading nonce char and the path to prove sensitivity.
        a = signing.hkey(self.PATH, self.TS, self.NONCE, algo="web")
        b = signing.hkey(self.PATH, self.TS, "D" + self.NONCE[1:], algo="web")
        c = signing.hkey("/other/path", self.TS, self.NONCE, algo="web")
        self.assertNotEqual(a, b)
        self.assertNotEqual(a, c)


class TestCreateSignature(unittest.TestCase):
    def test_keys(self):
        sig = signing.create_signature("/game/get_game_list_v3")
        self.assertIn("hkey", sig)
        self.assertIn("_time", sig)
        self.assertIn("nonce", sig)
        self.assertIsInstance(sig["_time"], int)
        self.assertEqual(len(sig["nonce"]), 32)


if __name__ == "__main__":
    unittest.main()
