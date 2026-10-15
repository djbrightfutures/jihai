"""JiHai locks the cascade. No live GLM. No key."""

import json
import os
import socket
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from jihai import __version__
from jihai import card as card_mod
from jihai import hands as hands_mod
from jihai import judge
from jihai import laps
from jihai import seat
from jihai.desk import answer, perform, prove


def _box_ok(test, text):
    width = card_mod.W + 2
    boxed = 0
    for line in text.splitlines():
        if line[:1] in "|+":
            boxed += 1
            test.assertEqual(len(line), width, line)
    test.assertGreater(boxed, 0)
    test.assertTrue(all(ord(ch) < 128 for ch in text))
    test.assertNotIn("\x1b", text)
    for line in text.splitlines():
        if "JIHAI" in line and "lap " in line:
            test.assertTrue(line.endswith(" |"), line)


class JiHaiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self._env = {
            name: os.environ.get(name)
            for name in (
                "JIHAI_GLM_KEY", "KEEN_GLM_KEY", "ZHIPU_API_KEY",
                "JIHAI_GLM_URL", "KEEN_GLM_URL", "JIHAI_FAST_URL", "KEEN_FAST_URL",
                "JIHAI_HOME", "KEEN_HOME",
            )
        }
        for name in self._env:
            os.environ.pop(name, None)
        os.environ["JIHAI_HOME"] = str(self.home)

    def tearDown(self):
        for name, value in self._env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        hands_mod._RUN = None
        self.tmp.cleanup()

    def test_version(self):
        self.assertEqual(__version__, "1.1.0")
        code, text = perform(["version"], self.home)
        self.assertEqual(code, 0)
        self.assertEqual(text, "1.1.0")

    def test_hostname_is_this_machine(self):
        self.assertEqual(hands_mod.hands("hostname"), socket.gethostname())

    def test_a_sentence_is_not_a_hand(self):
        self.assertIsNone(hands_mod.hands("what should we build next"))

    def test_run_is_an_argument_list(self):
        seen = {}

        def fake(argv):
            seen["argv"] = argv
            return "ok"

        hands_mod._RUN = fake
        self.assertEqual(hands_mod.hands('run tool "a&b"'), "ok")
        self.assertEqual(seen["argv"], ["tool", "a&b"])

    def test_stated_confidence_is_ignored(self):
        label, share, samples = judge.collect(
            "ship it", ["yes", "no"], lambda text, options: "yes 0.99", k=3
        )
        self.assertEqual(label, "yes")
        self.assertEqual(share, 1.0)
        self.assertEqual(samples, ["yes", "yes", "yes"])
        self.assertNotEqual(share, 0.99)

    def test_a_failed_sample_dilutes(self):
        calls = {"n": 0}

        def once(text, options):
            calls["n"] += 1
            if calls["n"] == 2:
                raise RuntimeError("down")
            return "yes"

        label, share, samples = judge.collect("ship", ["yes", "no"], once, k=3)
        self.assertEqual(label, "yes")
        self.assertAlmostEqual(share, 2 / 3)
        self.assertEqual(samples, ["yes", None, "yes"])
        self.assertFalse(judge.unanimous(label, share))

    def test_tie_keeps_the_earlier_label(self):
        answers = iter(["no", "yes"])
        label, share, _samples = judge.collect(
            "ship", ["yes", "no"], lambda text, options: next(answers), k=2
        )
        self.assertEqual(label, "no")
        self.assertAlmostEqual(share, 0.5)

    def test_hands_never_call_glm(self):
        def boom(messages):
            raise AssertionError("glm was called")

        row = answer("hostname", self.home, glm_fn=boom, fast_once=None)
        self.assertEqual(row["lane"], "hands")
        self.assertEqual(row["did"], socket.gethostname())
        self.assertEqual(row["proof"], "machine")
        self.assertEqual(row["stamp"], laps.stamp_of("hostname", row["did"]))

    def test_unanimous_skips_glm(self):
        def boom(messages):
            raise AssertionError("glm was called")

        row = answer(
            "choose yes|no :: ship it",
            self.home,
            glm_fn=boom,
            fast_once=lambda text, options: "yes 0.99",
        )
        self.assertEqual(row["lane"], "judge")
        self.assertEqual(row["proof"], "unanimous")
        self.assertEqual(row["did"], "yes")
        self.assertEqual(row["agree"], 1.0)
        self.assertEqual(row["ask"], "choose yes|no :: ship it")

    def test_split_keeps_the_model_text(self):
        seen = {}

        def glm(messages):
            seen["messages"] = messages
            return "I cannot\n<think>leave this</think>  "

        def once(text, options):
            once.n += 1
            return "yes" if once.n == 1 else "no"

        once.n = 0
        row = answer(
            "choose yes|no :: ship it",
            self.home,
            glm_fn=glm,
            fast_once=once,
            k=3,
        )
        self.assertEqual(row["lane"], "glm")
        self.assertEqual(row["proof"], "escalate")
        self.assertEqual(row["did"], "I cannot\n<think>leave this</think>  ")
        self.assertEqual(seen["messages"][-1]["content"], "choose yes|no :: ship it")
        self.assertTrue(all(item["role"] != "system" for item in seen["messages"]))
        self.assertAlmostEqual(row["agree"], round(2 / 3, 4))

    def test_prior_lap_is_context_only(self):
        answer("hostname", self.home, glm_fn=lambda messages: "no", fast_once=None)
        seen = {}

        def glm(messages):
            seen["messages"] = messages
            return "four"

        row = answer("what is 2 + 2", self.home, glm_fn=glm, fast_once=None)
        self.assertEqual(seen["messages"][0]["content"], "hostname")
        self.assertEqual(seen["messages"][-1]["content"], "what is 2 + 2")
        self.assertEqual(row["ask"], "what is 2 + 2")
        self.assertEqual(row["did"], "four")

    def test_no_key_does_not_call_out(self):
        def opener(req, timeout=0):
            raise AssertionError("the public seat was called")

        text = seat.live_glm([{"role": "user", "content": "hi"}], opener=opener)
        self.assertEqual(text, "seat dark: glm has no key")

    def test_model_words_survive_a_local_seat(self):
        def opener(req, timeout=0):
            class Resp:
                def read(self):
                    return b'{"choices":[{"message":{"content":"I cannot\\nstay"}}]}'

                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    return False

            return Resp()

        os.environ["JIHAI_GLM_URL"] = "http://127.0.0.1:9/v1/chat/completions"
        os.environ.pop("JIHAI_GLM_KEY", None)
        text = seat.live_glm([{"role": "user", "content": "hi"}], opener=opener)
        self.assertEqual(text, "I cannot\nstay")

    def test_a_failure_hides_the_address(self):
        def opener(req, timeout=0):
            raise urllib.error.URLError("https://user:secret@api.z.ai/private")

        text = seat.complete(
            [{"role": "user", "content": "hi"}],
            url="https://api.z.ai/api/paas/v4/chat/completions",
            key="test-key",
            model="glm-5.3",
            opener=opener,
        )
        self.assertEqual(text, "seat dark: glm")
        self.assertNotIn("secret", text)
        self.assertNotIn("test-key", text)

    def test_public_host_drops_userinfo(self):
        shown = seat.public_host("https://user:secret@api.z.ai/api/paas/v4/chat/completions")
        self.assertEqual(shown, "api.z.ai")
        self.assertNotIn("secret", shown)

    def test_the_old_keen_key_still_counts(self):
        os.environ["KEEN_GLM_KEY"] = "supersecret"
        text = seat.seats_text()
        self.assertIn("key", text)
        self.assertNotIn("supersecret", text)

    def test_seats_do_not_print_a_key(self):
        os.environ["JIHAI_GLM_KEY"] = "supersecret"
        text = seat.seats_text()
        self.assertIn("key", text)
        self.assertNotIn("supersecret", text)
        self.assertIn("glm-5.3", text)

    def test_newlines_stay_on_their_own_lines(self):
        drawn = card_mod.card({
            "lap": 3,
            "lane": "prove",
            "proof": "witnessed",
            "ms": 0.5,
            "ask": "prove",
            "did": "witnessed 1\ndrifted 0",
            "stamp": "abcd1234",
            "votes": [],
            "agree": None,
        })
        _box_ok(self, drawn)
        self.assertIn("| witnessed 1", drawn)
        self.assertIn("| drifted 0", drawn)
        self.assertNotIn("?", drawn)

    def test_card_is_a_box(self):
        row = answer("hostname", self.home, glm_fn=lambda messages: "no", fast_once=None)
        row["did"] = "DjBFs ca\u00f1on"
        drawn = card_mod.card(row)
        _box_ok(self, drawn)
        saved = json.loads(laps.path_of(self.home).read_text(encoding="utf-8"))
        self.assertEqual(saved["did"], socket.gethostname())

    def test_prove_witnesses_a_fact_and_leaves_the_model(self):
        answer("hostname", self.home, glm_fn=lambda messages: "no", fast_once=None)
        answer("a real sentence", self.home, glm_fn=lambda messages: "raw", fast_once=None)
        row = prove(self.home)
        self.assertIn("witnessed 1", row["did"])
        self.assertIn("left alone 1", row["did"])
        self.assertIn("model laps are not re-run", row["did"])
        self.assertEqual(row["proof"], "witnessed")

    def test_a_bad_stamp_is_tampered(self):
        answer("hostname", self.home, glm_fn=lambda messages: "no", fast_once=None)
        file_path = laps.path_of(self.home)
        row = json.loads(file_path.read_text(encoding="utf-8"))
        row["stamp"] = "deadbeef"
        file_path.write_text(json.dumps(row) + "\n", encoding="utf-8")
        proved = prove(self.home)
        self.assertIn("tampered 1", proved["did"])
        self.assertIn("witnessed 0", proved["did"])

    def test_stamp_finds_the_lap(self):
        row = answer("hostname", self.home, glm_fn=lambda messages: "no", fast_once=None)
        code, text = perform(["stamp", row["stamp"]], self.home)
        self.assertEqual(code, 0)
        self.assertIn(row["stamp"], text)
        _box_ok(self, text)

    def test_empty_prove(self):
        row = prove(self.home)
        self.assertEqual(row["proof"], "empty")
        self.assertIn("facts checked 0", row["did"])

    def test_default_model_and_url(self):
        self.assertEqual(seat.DEFAULT_MODEL, "glm-5.3")
        self.assertEqual(seat.DEFAULT_URL, "https://api.z.ai/api/paas/v4/chat/completions")

    def test_hop_is_slower_than_hands(self):
        from jihai.desk import measured_hop
        hands_ms, hop_ms = measured_hop(8)
        self.assertGreater(hop_ms, hands_ms)
        self.assertGreater(hands_ms, 0)


if __name__ == "__main__":
    unittest.main()
