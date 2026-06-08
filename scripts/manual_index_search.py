#!/usr/bin/env python3
"""Create and manually populate the demo Azure AI Search RAG index.

Required environment variables:
  AZURE_SEARCH_ENDPOINT=https://<service>.search.windows.net
  AZURE_SEARCH_KEY=<admin key>

Optional:
  AZURE_SEARCH_INDEX=rag-1779444354799
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import urllib.error
import urllib.parse
import urllib.request


API_VERSION = "2024-07-01"
DEFAULT_INDEX = "rag-1779444354799"
CHUNK_CHARS = 1800
CHUNK_OVERLAP = 200
DEFAULT_GITHUB_REPOSITORY = "https://github.com/dilgamme/ms-tech-demo1"
REPOSITORY_ROOT_FILES = {
    "README.md",
    "PRIVATE_ENDPOINT_RESTORE.md",
    "REPOSITORY_SELF_KNOWLEDGE.md",
    "SOLUTION_ARCHITECTURE.md",
    "AZURE_AI_TRANSLATOR.md",
    "FOUNDRY_MIGRATION.md",
    "WEB_IQ.md",
    "IMAGE_UPLOAD.md",
    "deploy.sh",
}
REPOSITORY_ALLOWED_PREFIXES = (
    "backend/app/",
    "frontend/src/",
    "infra/",
    ".github/workflows/",
)
REPOSITORY_ALLOWED_FILES = {
    "backend/requirements.txt",
    "frontend/package.json",
}
REPOSITORY_ALLOWED_SUFFIXES = {
    ".bicep",
    ".css",
    ".html",
    ".js",
    ".jsx",
    ".json",
    ".md",
    ".py",
    ".sh",
    ".txt",
    ".yaml",
    ".yml",
}
REPOSITORY_EXCLUDED_PARTS = {
    ".env",
    ".git",
    ".python_packages",
    "__pycache__",
    "dist",
    "node_modules",
    "venv",
}


def request(method: str, path: str, body: dict | None = None) -> dict:
    endpoint = required_env("AZURE_SEARCH_ENDPOINT").rstrip("/")
    key = required_env("AZURE_SEARCH_KEY")
    data = json.dumps(body).encode("utf-8") if body is not None else None
    url = f"{endpoint}{path}{'&' if '?' in path else '?'}api-version={API_VERSION}"
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Content-Type": "application/json",
            "api-key": key,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"{method} {url} failed: {exc.code} {detail}") from exc
    return json.loads(raw.decode("utf-8")) if raw else {}


def required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def index_name() -> str:
    return os.environ.get("AZURE_SEARCH_INDEX", DEFAULT_INDEX)


def create_index() -> None:
    name = index_name()
    body = {
        "name": name,
        "fields": [
            {"name": "id", "type": "Edm.String", "key": True, "filterable": True},
            {"name": "title", "type": "Edm.String", "searchable": True, "filterable": True, "sortable": True},
            {"name": "chunk", "type": "Edm.String", "searchable": True},
            {"name": "source", "type": "Edm.String", "filterable": True, "sortable": True},
        ],
    }
    request("PUT", f"/indexes/{urllib.parse.quote(name, safe='')}", body)
    print(f"Created or updated index: {name}")


def delete_index() -> None:
    name = index_name()
    try:
        request("DELETE", f"/indexes/{urllib.parse.quote(name, safe='')}")
    except SystemExit as exc:
        if "404" not in str(exc):
            raise
        print(f"Index did not exist: {name}")
        return
    print(f"Deleted index: {name}")


def iter_source_files(docs_dir: pathlib.Path):
    for path in sorted(docs_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".md", ".txt"}:
            yield path


def iter_repository_files(repo_root: pathlib.Path):
    paths = []
    for current_root, dir_names, file_names in os.walk(repo_root):
        dir_names[:] = sorted(
            name
            for name in dir_names
            if name not in REPOSITORY_EXCLUDED_PARTS and not name.startswith(".env")
        )
        current_path = pathlib.Path(current_root)
        for file_name in sorted(file_names):
            path = current_path / file_name
            relative = path.relative_to(repo_root)
            relative_posix = relative.as_posix()
            if file_name.startswith(".env") or path.suffix.lower() not in REPOSITORY_ALLOWED_SUFFIXES:
                continue
            allowed = (
                relative_posix in REPOSITORY_ROOT_FILES
                or relative_posix in REPOSITORY_ALLOWED_FILES
                or any(relative_posix.startswith(prefix) for prefix in REPOSITORY_ALLOWED_PREFIXES)
            )
            if allowed:
                paths.append(path)
    yield from sorted(paths)


def chunk_text(text: str) -> list[str]:
    normalized = "\n".join(line.rstrip() for line in text.splitlines()).strip()
    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(start + CHUNK_CHARS, len(normalized))
        chunks.append(normalized[start:end].strip())
        if end == len(normalized):
            break
        start = max(0, end - CHUNK_OVERLAP)
    return [chunk for chunk in chunks if chunk]


def build_document_chunks(
    path: pathlib.Path,
    relative_path: pathlib.Path,
    title: str,
    source: str,
    namespace: str,
) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    documents = []
    for idx, chunk in enumerate(chunk_text(text), start=1):
        digest = hashlib.sha256(
            f"{namespace}:{relative_path.as_posix()}:{idx}".encode("utf-8")
        ).hexdigest()[:32]
        documents.append(
            {
                "@search.action": "mergeOrUpload",
                "id": digest,
                "title": title,
                "chunk": f"Repository file: {relative_path.as_posix()}\n\n{chunk}",
                "source": source,
            }
        )
    return documents


def upload_chunks(docs: list[dict]) -> None:
    if not docs:
        return
    name = urllib.parse.quote(index_name(), safe="")
    for start in range(0, len(docs), 500):
        batch = docs[start:start + 500]
        request("POST", f"/indexes/{name}/docs/index", {"value": batch})
        print(f"Uploaded {start + len(batch)} / {len(docs)} chunks")


def upload_documents(docs_dir: pathlib.Path) -> None:
    if not docs_dir.exists():
        raise SystemExit(f"Docs directory does not exist: {docs_dir}")

    docs = []
    for path in iter_source_files(docs_dir):
        relative_path = path.relative_to(docs_dir)
        title = path.stem.replace("-", " ").replace("_", " ").strip() or path.name
        docs.extend(
            build_document_chunks(
                path,
                relative_path,
                title,
                relative_path.as_posix(),
                "documents",
            )
        )

    if not docs:
        print(f"No .md or .txt files found under {docs_dir}")
        return

    upload_chunks(docs)


def upload_repository(repo_root: pathlib.Path, github_repository: str) -> None:
    if not repo_root.exists():
        raise SystemExit(f"Repository directory does not exist: {repo_root}")

    docs = []
    github_base = github_repository.rstrip("/")
    for path in iter_repository_files(repo_root):
        relative_path = path.relative_to(repo_root)
        relative_posix = relative_path.as_posix()
        source_url = f"{github_base}/blob/main/{urllib.parse.quote(relative_posix)}"
        docs.extend(
            build_document_chunks(
                path,
                relative_path,
                f"MS Tech Demo: {relative_posix}",
                source_url,
                "repository",
            )
        )

    if not docs:
        print(f"No allowlisted repository files found under {repo_root}")
        return

    upload_chunks(docs)


def main() -> None:
    parser = argparse.ArgumentParser(description="Manually manage the demo Azure AI Search index.")
    parser.add_argument("--delete-index", action="store_true", help="Delete the configured index before recreating it.")
    parser.add_argument("--create-index", action="store_true", help="Create or update the free-tier lexical index.")
    parser.add_argument("--docs-dir", type=pathlib.Path, help="Directory containing .md and .txt files to index.")
    parser.add_argument("--repo-root", type=pathlib.Path, help="Repository root to index using the safe allowlist.")
    parser.add_argument(
        "--github-repository",
        default=os.environ.get("GITHUB_REPOSITORY_URL", DEFAULT_GITHUB_REPOSITORY),
        help="Public GitHub repository URL used for source citations.",
    )
    args = parser.parse_args()

    if args.delete_index:
        delete_index()
    if args.create_index:
        create_index()
    if args.docs_dir:
        upload_documents(args.docs_dir)
    if args.repo_root:
        upload_repository(args.repo_root, args.github_repository)
    if not args.delete_index and not args.create_index and not args.docs_dir and not args.repo_root:
        parser.error("Specify --delete-index, --create-index, --docs-dir, --repo-root, or a combination.")


if __name__ == "__main__":
    main()
