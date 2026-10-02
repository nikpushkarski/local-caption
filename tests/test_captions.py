import unittest

from local_caption.captions import single_line_captions


def segment(tokens, gap=0.0):
    return {
        "text": " ".join(tokens),
        "words": [
            {"word": " " + token, "start": i * (0.2 + gap), "end": i * (0.2 + gap) + 0.2}
            for i, token in enumerate(tokens)
        ],
    }


class CaptionTests(unittest.TestCase):
    def test_word_limit_and_timing(self):
        result = single_line_captions([segment(["one", "two", "three", "four", "five"])])
        self.assertEqual([cue["text"] for cue in result], ["one two three four", "five"])
        self.assertEqual(result[0]["start"], 0)
        self.assertAlmostEqual(result[0]["end"], 0.8)
        self.assertAlmostEqual(result[1]["start"], 0.8)

    def test_character_limit(self):
        result = single_line_captions([segment(["extraordinary", "performance"])])
        self.assertEqual(len(result), 2)

    def test_pause_and_punctuation(self):
        self.assertEqual(len(single_line_captions([segment(["hello", "there"], gap=0.5)])), 2)
        result = single_line_captions([segment(["Hello!", "How", "are", "you?"])])
        self.assertEqual([cue["text"] for cue in result], ["Hello!", "How are you?"])

    def test_duration_limit(self):
        item = segment(["one", "two", "three"])
        item["words"][0].update(start=0, end=0.8)
        item["words"][1].update(start=0.8, end=1.6)
        item["words"][2].update(start=1.6, end=2.4)
        self.assertEqual(len(single_line_captions([item])), 3)

    def test_whitespace_and_long_word_preserved(self):
        token = "supercalifragilisticexpialidocious"
        result = single_line_captions([segment(["hello\nthere", token])])
        self.assertEqual([cue["text"] for cue in result], ["hello there", token])
        self.assertTrue(all("\n" not in cue["text"] for cue in result))

    def test_empty_and_missing_timestamps(self):
        self.assertEqual(single_line_captions([]), [])
        with self.assertRaises(ValueError):
            single_line_captions([{"text": "Missing word timestamps"}])


if __name__ == "__main__":
    unittest.main()
