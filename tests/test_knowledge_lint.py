from pathlib import Path
import sys
import tempfile
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts import knowledge_lint


class KnowledgeLintTests(unittest.TestCase):
    def test_entity_ids_use_entity_namespace(self):
        self.assertTrue(knowledge_lint.is_entity_id("PART-000001"))
        self.assertTrue(knowledge_lint.is_entity_id("MACHINE-123456"))
        self.assertFalse(knowledge_lint.is_entity_id("SRC-000001"))
        self.assertFalse(knowledge_lint.is_entity_id("REL-000001"))
        self.assertFalse(knowledge_lint.is_entity_id("PART-123"))

    def test_relation_and_source_namespaces(self):
        self.assertTrue(knowledge_lint.is_relation_id("REL-000001"))
        self.assertFalse(knowledge_lint.is_relation_id("PART-000001"))
        self.assertTrue(knowledge_lint.is_source_id("SRC-000001"))
        self.assertFalse(knowledge_lint.is_source_id("ASSET-000001"))

    def test_markdown_link_parser(self):
        content = "[local](../README.md) and ![diagram](./diagram.png) plus [web](https://example.com)"
        self.assertEqual(
            knowledge_lint.parse_markdown_links(content),
            ["../README.md", "./diagram.png", "https://example.com"],
        )

    def test_resolve_local_and_external_links(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_dir = root / "docs" / "chapter"
            source_dir.mkdir(parents=True)
            target = root / "docs" / "README.md"
            target.write_text("# index", encoding="utf-8")
            source = source_dir / "article.md"
            source.write_text("# article", encoding="utf-8")
            self.assertEqual(
                knowledge_lint.resolve_internal_target(source, "../README.md", root),
                target,
            )
            self.assertIsNone(
                knowledge_lint.resolve_internal_target(source, "https://example.com", root)
            )

    def test_rejects_links_escaping_repository(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "docs" / "article.md"
            source.parent.mkdir(parents=True)
            source.write_text("# article", encoding="utf-8")
            with self.assertRaises(ValueError):
                knowledge_lint.resolve_internal_target(source, "../../../outside.txt", root)


if __name__ == "__main__":
    unittest.main()
