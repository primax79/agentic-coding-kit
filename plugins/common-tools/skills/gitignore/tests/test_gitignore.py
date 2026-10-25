#!/usr/bin/env python3
"""
Unit tests for gitignore skill rule preservation and deduplication.

Covers:
- rules after the generated block
- rules between two blocks
- comments attached to the rules that follow them
- an existing custom head
- idempotence on a second run
- the report content
- duplicate dropping only when identical
- dry-run mode
- real gCube Maven repository fixture
"""

import os
import sys
import tempfile
import unittest

# Ensure scripts directory is on sys.path
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(TESTS_DIR)
SCRIPTS_DIR = os.path.join(SKILL_DIR, "scripts")
FIXTURES_DIR = os.path.join(TESTS_DIR, "fixtures")

if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from preserve_rules import preserve_custom_rules, PreservationReport
from generate_gitignore import apply_gitignore


class TestGitignoreRulePreservation(unittest.TestCase):

    def _read_fixture(self, filename):
        path = os.path.join(FIXTURES_DIR, filename)
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def test_rules_after_generated_block(self):
        """Rules placed after a generated block must be preserved and moved to custom head."""
        existing = self._read_fixture("after_block.gitignore")
        template = (
            "# Created by https://www.toptal.com/developers/gitignore/api/java,maven\n"
            "### Java ###\n"
            "*.class\n"
            "*.log\n"
            "### Maven ###\n"
            "target/\n"
            "# End of https://www.toptal.com/developers/gitignore/api/java,maven\n"
        )

        final_content, report = preserve_custom_rules(existing, template)

        # Custom rules should be at the head under # Custom Project Rules
        self.assertTrue(final_content.startswith("# Custom Project Rules\n"))
        self.assertIn("src/test/resources/*.gcubekey", final_content)
        self.assertIn("src/test/resources/secret.properties", final_content)
        self.assertIn("config/local.ini", final_content)

        # The rules should appear before the generated block
        head_end = final_content.find("# Created by https://www.toptal.com")
        self.assertGreater(head_end, 0)
        rule_pos = final_content.find("src/test/resources/*.gcubekey")
        self.assertLess(rule_pos, head_end)

        # Report should list all moved lines
        expected_moved = [
            "# Project specific rules after generated block",
            "# Sensitive test keys",
            "src/test/resources/*.gcubekey",
            "src/test/resources/secret.properties",
            "config/local.ini",
        ]
        self.assertEqual(report.lines_moved, expected_moved)
        self.assertEqual(report.lines_dropped, [])

    def test_rules_between_two_blocks(self):
        """Rules placed between two blocks and after blocks must be preserved at head in original order."""
        existing = self._read_fixture("between_blocks.gitignore")
        template = (
            "### gCube Ecosystem ###\n"
            "token.properties\n"
            "local-config.properties\n"
            "gcube/extra-resources/local*\n"
            "*.war.failed\n\n"
            "# Created by https://www.toptal.com/developers/gitignore/api/java\n"
            "### Java ###\n"
            "*.class\n"
            "*.log\n"
            "# End of https://www.toptal.com/developers/gitignore/api/java\n"
        )

        final_content, report = preserve_custom_rules(existing, template)

        self.assertTrue(final_content.startswith("# Custom Project Rules\n"))
        self.assertIn("intermediate_cache.dat", final_content)
        self.assertIn("scratch/", final_content)
        self.assertIn("trailing_rule.txt", final_content)

        # Check relative order: intermediate_cache.dat must come before trailing_rule.txt
        pos_between = final_content.find("intermediate_cache.dat")
        pos_trailing = final_content.find("trailing_rule.txt")
        self.assertLess(pos_between, pos_trailing)

        expected_moved = [
            "# Custom rule between blocks",
            "intermediate_cache.dat",
            "scratch/",
            "# Custom rule after all blocks",
            "trailing_rule.txt",
        ]
        self.assertEqual(report.lines_moved, expected_moved)

    def test_comments_attached_to_rules(self):
        """Comments stay attached to the rules that follow them; dropped duplicates drop their comment."""
        existing = self._read_fixture("comments_attached.gitignore")
        template = (
            "# Created by https://www.toptal.com/developers/gitignore/api/java,maven\n"
            "### Java ###\n"
            "*.class\n"
            "*.log\n"
            "### Maven ###\n"
            "target/\n"
            "# End of https://www.toptal.com/developers/gitignore/api/java,maven\n"
        )

        final_content, report = preserve_custom_rules(existing, template)

        # Duplicate rule *.class and its comment must be dropped
        self.assertIn("*.class", report.lines_dropped)
        self.assertNotIn("# Comment for rule that is duplicate of template", final_content)

        # Kept rules must keep their comments
        self.assertIn("# Comment for rules that are kept\nkept_rule_1.txt\nkept_rule_2.txt", final_content)

        # Standalone comment without any rules must be kept
        self.assertIn("# Standalone comment without any rules", final_content)

        # Comment for single kept rule
        self.assertIn("# Comment for single kept rule\nkept_rule_3.txt", final_content)

    def test_existing_custom_head(self):
        """An existing custom head must be preserved, and trailing rules appended in order."""
        existing = self._read_fixture("existing_custom_head.gitignore")
        template = (
            "# Created by https://www.toptal.com/developers/gitignore/api/java,maven\n"
            "### Java ###\n"
            "*.class\n"
            "*.log\n"
            "### Maven ###\n"
            "target/\n"
            "# End of https://www.toptal.com/developers/gitignore/api/java,maven\n"
        )

        final_content, report = preserve_custom_rules(existing, template)

        self.assertTrue(final_content.startswith("# Custom Project Rules\n"))
        self.assertIn("# Existing custom head rule\nhead_rule.txt", final_content)
        self.assertIn("# Trailing rule moved\ntrailing_rule.txt", final_content)

        # Order check: head_rule.txt before trailing_rule.txt
        pos_head = final_content.find("head_rule.txt")
        pos_trailing = final_content.find("trailing_rule.txt")
        self.assertLess(pos_head, pos_trailing)

        # Only trailing_rule lines should be reported as moved (head_rule was already at head)
        self.assertEqual(report.lines_moved, ["# Trailing rule moved", "trailing_rule.txt"])
        self.assertEqual(report.lines_dropped, [])

    def test_idempotence_second_run(self):
        """Regenerating twice in a row must produce the exact same file (no changes, 0 moved, 0 dropped)."""
        existing = self._read_fixture("after_block.gitignore")
        template = (
            "# Created by https://www.toptal.com/developers/gitignore/api/java,maven\n"
            "### Java ###\n"
            "*.class\n"
            "*.log\n"
            "### Maven ###\n"
            "target/\n"
            "# End of https://www.toptal.com/developers/gitignore/api/java,maven\n"
        )

        # Run 1
        run1_content, run1_report = preserve_custom_rules(existing, template)
        self.assertGreater(len(run1_report.lines_moved), 0)

        # Run 2 on the output of Run 1
        run2_content, run2_report = preserve_custom_rules(run1_content, template)

        # Files must be byte-for-byte identical
        self.assertEqual(run1_content, run2_content)

        # Second run should have 0 lines moved and 0 lines dropped
        self.assertEqual(run2_report.lines_moved, [])
        self.assertEqual(run2_report.lines_dropped, [])

    def test_report_content(self):
        """Preservation report formatting accurately enumerates counts and lines."""
        report = PreservationReport(
            lines_moved=["custom_moved_1.txt", "custom_moved_2.txt"],
            lines_dropped=["target/"]
        )
        formatted = report.format_report()
        self.assertIn("Lines moved to custom head (2):", formatted)
        self.assertIn("  - custom_moved_1.txt", formatted)
        self.assertIn("  - custom_moved_2.txt", formatted)
        self.assertIn("Lines dropped as duplicates of template (1):", formatted)
        self.assertIn("  - target/", formatted)

        # Empty report formatting
        empty_report = PreservationReport([], [])
        formatted_empty = empty_report.format_report()
        self.assertIn("Lines moved to custom head (0):\n  (none)", formatted_empty)
        self.assertIn("Lines dropped as duplicates of template (0):\n  (none)", formatted_empty)

    def test_duplicates_dropped_only_when_identical(self):
        """Duplicates are dropped ONLY when identical; subtle differences like 'target' vs 'target/' are kept."""
        existing = (
            "target\n"
            ".settings\n"
            "target/\n"
            "custom.txt\n"
            "# Created by https://www.toptal.com/developers/gitignore/api/java\n"
            "### Java ###\n"
            "*.class\n"
            "# End of https://www.toptal.com/developers/gitignore/api/java\n"
        )
        template = (
            "# Created by https://www.toptal.com/developers/gitignore/api/java\n"
            "### Java ###\n"
            "target/\n"
            ".settings/\n"
            "*.class\n"
            "# End of https://www.toptal.com/developers/gitignore/api/java\n"
        )

        final_content, report = preserve_custom_rules(existing, template)

        # 'target/' was identical to template -> dropped
        self.assertIn("target/", report.lines_dropped)

        # 'target' is NOT identical to 'target/' -> must be KEPT
        self.assertIn("target\n", final_content)

        # '.settings' is NOT identical to '.settings/' -> must be KEPT
        self.assertIn(".settings\n", final_content)

        # 'custom.txt' not in template -> must be KEPT
        self.assertIn("custom.txt", final_content)

    def test_dry_run_mode(self):
        """Dry-run mode returns preserved content and report without modifying the file on disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gitignore_path = os.path.join(tmpdir, ".gitignore")
            original_content = (
                "# Created by https://www.toptal.com/developers/gitignore/api/java\n"
                "*.class\n"
                "# End of https://www.toptal.com/developers/gitignore/api/java\n"
                "my_custom_secret.key\n"
            )
            with open(gitignore_path, "w", encoding="utf-8") as f:
                f.write(original_content)

            template = (
                "# Created by https://www.toptal.com/developers/gitignore/api/java\n"
                "*.class\n"
                "# End of https://www.toptal.com/developers/gitignore/api/java\n"
            )

            # Dry run execution
            final_content, report = apply_gitignore(tmpdir, template, dry_run=True)

            # File on disk must remain unchanged!
            with open(gitignore_path, "r", encoding="utf-8") as f:
                disk_content = f.read()
            self.assertEqual(disk_content, original_content)

            # Report and final_content are properly generated
            self.assertIn("my_custom_secret.key", final_content)
            self.assertEqual(report.lines_moved, ["my_custom_secret.key"])

    def test_real_gcube_repo_fixture(self):
        """Test on fixture modeled from authorization-control-library/.gitignore."""
        existing = self._read_fixture("real_gcube_auth.gitignore")
        template = (
            "# Created by https://www.toptal.com/developers/gitignore/api/java,macos,linux,visualstudiocode,eclipse\n"
            "### Eclipse ###\n"
            ".metadata\n"
            "bin/\n"
            "tmp/\n"
            "*.tmp\n"
            "*.bak\n"
            "*.swp\n"
            "*~.nib\n"
            "local.properties\n"
            ".settings/\n"
            ".loadpath\n"
            ".recommenders\n"
            "# End of https://www.toptal.com/developers/gitignore/api/java,macos,linux,visualstudiocode,eclipse\n"
        )

        final_content, report = preserve_custom_rules(existing, template)

        # All rules from before the block must be present
        self.assertIn("ignore_me", final_content)
        self.assertIn("tomcat", final_content)
        self.assertIn("target", final_content)
        self.assertIn(".classpath", final_content)
        self.assertIn(".visual", final_content)
        self.assertIn(".project", final_content)
        self.assertIn(".settings", final_content)
        self.assertIn("/**/.DS_Store", final_content)

        # All rules from after the block must be preserved in custom head
        self.assertIn("./documentation/sphinx/_build/", final_content)
        self.assertIn("src/test/resources/*.gcubekey", final_content)
        self.assertIn("src/test/resources/*.properties*", final_content)
        self.assertIn("src/test/resources/config.ini", final_content)

        # Comments must remain intact
        self.assertIn("# Ignoring sensitive files in test resources", final_content)
        self.assertIn("# These files are not needed for the tests to run and should not be committed", final_content)
        self.assertIn("# to the repository as they may contain sensitive information.", final_content)

        # Moved lines must contain the rules and comments from after the block
        self.assertIn("./documentation/sphinx/_build/", report.lines_moved)
        self.assertIn("src/test/resources/*.gcubekey", report.lines_moved)
        self.assertIn("src/test/resources/*.properties*", report.lines_moved)
        self.assertIn("src/test/resources/config.ini", report.lines_moved)


if __name__ == "__main__":
    unittest.main()
