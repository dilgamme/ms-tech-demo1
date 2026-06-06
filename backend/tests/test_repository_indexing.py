import pathlib
import sys
import tempfile
import unittest

SCRIPTS_DIR = pathlib.Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import manual_index_search


class RepositoryIndexingTests(unittest.TestCase):
    def test_repository_allowlist_excludes_secrets_and_generated_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = pathlib.Path(temp_dir)
            files = {
                "README.md": "public docs",
                "backend/app/main.py": "print('app')",
                "frontend/src/App.jsx": "export default App",
                ".github/workflows/deploy.yml": "name: deploy",
                "backend/.env": "SECRET=value",
                "frontend/node_modules/package/index.js": "generated",
                "notes/private.md": "not allowlisted",
            }
            for relative, content in files.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")

            indexed = {
                path.relative_to(root).as_posix()
                for path in manual_index_search.iter_repository_files(root)
            }

        self.assertEqual(
            indexed,
            {
                "README.md",
                "backend/app/main.py",
                "frontend/src/App.jsx",
                ".github/workflows/deploy.yml",
            },
        )

    def test_repository_chunks_have_stable_ids_and_github_sources(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = pathlib.Path(temp_dir)
            path = root / "README.md"
            path.write_text("Architecture overview", encoding="utf-8")

            first = manual_index_search.build_document_chunks(
                path,
                pathlib.Path("README.md"),
                "MS Tech Demo: README.md",
                "https://github.com/example/repo/blob/main/README.md",
                "repository",
            )
            path.write_text("Updated architecture overview", encoding="utf-8")
            second = manual_index_search.build_document_chunks(
                path,
                pathlib.Path("README.md"),
                "MS Tech Demo: README.md",
                "https://github.com/example/repo/blob/main/README.md",
                "repository",
            )

        self.assertEqual(first[0]["id"], second[0]["id"])
        self.assertEqual(
            second[0]["source"],
            "https://github.com/example/repo/blob/main/README.md",
        )


if __name__ == "__main__":
    unittest.main()
