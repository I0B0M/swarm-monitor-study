"""Report kit checks (issue #12). Run: python -m unittest discover -s tests"""

import unittest

from tools import check_numbers, lint_vocab, report_stats


class NumberCheck(unittest.TestCase):
    NUMBERS = "| S2 | 0/50 | upper 7.1% |\nconfirmatory p = 2.6e-21\n"

    def test_traced_numbers_pass(self):
        report = "Undetected sabotage was 0/50 (upper 7.1%), and the test gave p = 2.6e-21."
        self.assertEqual(check_numbers.check(report, self.NUMBERS), [])

    def test_untraced_number_fails_with_its_line(self):
        report = "line one\nUndetected sabotage was 3/50."
        self.assertEqual(check_numbers.check(report, self.NUMBERS), [(2, "3/50")])

    def test_opt_out_and_code_are_skipped(self):
        report = "Others found 94% <!-- not data -->\n```\npython run.py --seeds 201-225 99%\n```"
        self.assertEqual(check_numbers.check(report, self.NUMBERS), [])


class VocabularyLint(unittest.TestCase):
    def test_clean_text_passes(self):
        text = "The saboteur launders a record's tag before the exit. Apart's Swarm Alignment Hackathon."
        self.assertEqual(lint_vocab.lint(text), [])

    def test_game_words_swarm_and_dashes_fail(self):
        text = "The imposter moved a crate \u2014 then the swarm cheered."
        msgs = [m for _, m in lint_vocab.lint(text)]
        self.assertIn("em dash", msgs)
        self.assertTrue(any("imposter" in m for m in msgs))
        self.assertTrue(any("crate" in m for m in msgs))
        self.assertTrue(any("swarm" in m for m in msgs))

    def test_code_spans_and_repo_name_are_skipped(self):
        text = "Run `python run.py --cells S2-imp` from github.com/I0B0M/swarm-monitor-study."
        self.assertEqual(lint_vocab.lint(text), [])


class FormatRules(unittest.TestCase):
    def test_abstract_word_count(self):
        md = "# Title\n\n## Abstract\n\n" + " ".join(["word"] * 180) + "\n\n## 1. Introduction\n\ntext"
        self.assertEqual(report_stats.abstract_words(md), 180)

    def test_pdf_page_count(self):
        fake = b"<< /Type /Pages /Count 2 >> << /Type /Page >> << /Type /Page >>"
        self.assertEqual(report_stats.pdf_pages(fake), 2)


if __name__ == "__main__":
    unittest.main()
