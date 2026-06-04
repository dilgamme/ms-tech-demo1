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


def upload_documents(docs_dir: pathlib.Path) -> None:
    if not docs_dir.exists():
        raise SystemExit(f"Docs directory does not exist: {docs_dir}")

    docs = []
    for path in iter_source_files(docs_dir):
        text = path.read_text(encoding="utf-8")
        title = path.stem.replace("-", " ").replace("_", " ").strip() or path.name
        for idx, chunk in enumerate(chunk_text(text), start=1):
            digest = hashlib.sha256(f"{path}:{idx}:{chunk}".encode("utf-8")).hexdigest()[:32]
            docs.append(
                {
                    "@search.action": "mergeOrUpload",
                    "id": digest,
                    "title": title,
                    "chunk": chunk,
                    "source": str(path.relative_to(docs_dir)),
                }
            )

    if not docs:
        print(f"No .md or .txt files found under {docs_dir}")
        return

    name = urllib.parse.quote(index_name(), safe="")
    for start in range(0, len(docs), 500):
        batch = docs[start:start + 500]
        request("POST", f"/indexes/{name}/docs/index", {"value": batch})
        print(f"Uploaded {start + len(batch)} / {len(docs)} chunks")


def main() -> None:
    parser = argparse.ArgumentParser(description="Manually manage the demo Azure AI Search index.")
    parser.add_argument("--delete-index", action="store_true", help="Delete the configured index before recreating it.")
    parser.add_argument("--create-index", action="store_true", help="Create or update the free-tier lexical index.")
    parser.add_argument("--docs-dir", type=pathlib.Path, help="Directory containing .md and .txt files to index.")
    args = parser.parse_args()

    if args.delete_index:
        delete_index()
    if args.create_index:
        create_index()
    if args.docs_dir:
        upload_documents(args.docs_dir)
    if not args.delete_index and not args.create_index and not args.docs_dir:
        parser.error("Specify --delete-index, --create-index, --docs-dir, or a combination.")


if __name__ == "__main__":
    main()
