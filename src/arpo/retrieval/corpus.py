from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from arpo.models import Document


class Corpus:
    def __init__(self, documents: Iterable[Document]):
        self.documents = list(documents)
        self._by_id = {document.id: document for document in self.documents}

    @classmethod
    def from_jsonl(cls, path: str | Path) -> "Corpus":
        documents: list[Document] = []
        with Path(path).open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                record = json.loads(line)
                try:
                    documents.append(
                        Document(
                            id=str(record["id"]),
                            title=str(record.get("title", record["id"])),
                            text=str(record["text"]),
                            metadata=dict(record.get("metadata", {})),
                        )
                    )
                except KeyError as exc:
                    raise ValueError(f"Missing {exc} in {path} line {line_number}") from exc
        return cls(documents)

    def get(self, document_id: str) -> Document | None:
        return self._by_id.get(document_id)

    def related(self, document: Document) -> list[Document]:
        related_ids = document.metadata.get("related_ids", [])
        citations = document.metadata.get("citations", [])
        candidates = [self.get(str(document_id)) for document_id in [*related_ids, *citations]]
        return [candidate for candidate in candidates if candidate is not None]

    def __len__(self) -> int:
        return len(self.documents)

