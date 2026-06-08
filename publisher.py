from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

IMMUTABLE_CACHE_CONTROL = "public, max-age=31536000, immutable"
LATEST_CACHE_CONTROL = "no-cache"
PARQUET_CONTENT_TYPE = "application/vnd.apache.parquet"
JSON_CONTENT_TYPE = "application/json"


@dataclass(frozen=True)
class Artifact:
    model: str
    key: str
    path: Path
    rows: int
    size: int
    sha256: str


@dataclass(frozen=True)
class ObjectMetadata:
    content_type: str
    cache_control: str


class ObjectStore(Protocol):
    def upload_file(
        self,
        path: Path,
        key: str,
        *,
        metadata: ObjectMetadata,
    ) -> None: ...

    def put_json(
        self,
        key: str,
        payload: dict[str, object],
        *,
        metadata: ObjectMetadata,
    ) -> None: ...


def release_id_for(generated_at: datetime) -> str:
    return generated_at.astimezone(UTC).strftime("%Y-%m-%dT%H%M%SZ")


def isoformat_z(generated_at: datetime) -> str:
    return generated_at.astimezone(UTC).replace(tzinfo=None).isoformat() + "Z"


def build_manifest(
    *,
    release_id: str,
    generated_at: datetime,
    artifacts: list[Artifact],
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "release_id": release_id,
        "generated_at": isoformat_z(generated_at),
        "artifacts": [
            {
                "model": artifact.model,
                "key": artifact.key,
                "rows": artifact.rows,
                "size": artifact.size,
                "sha256": artifact.sha256,
            }
            for artifact in artifacts
        ],
    }


def publish_release(
    *,
    store: ObjectStore,
    release_id: str,
    generated_at: datetime,
    artifacts: list[Artifact],
) -> dict[str, object]:
    immutable_metadata = ObjectMetadata(
        content_type=PARQUET_CONTENT_TYPE,
        cache_control=IMMUTABLE_CACHE_CONTROL,
    )
    json_metadata = ObjectMetadata(
        content_type=JSON_CONTENT_TYPE,
        cache_control=IMMUTABLE_CACHE_CONTROL,
    )
    latest_metadata = ObjectMetadata(
        content_type=JSON_CONTENT_TYPE,
        cache_control=LATEST_CACHE_CONTROL,
    )
    manifest_key = f"releases/{release_id}/manifest.json"

    for artifact in artifacts:
        store.upload_file(
            artifact.path,
            artifact.key,
            metadata=immutable_metadata,
        )

    manifest = build_manifest(
        release_id=release_id,
        generated_at=generated_at,
        artifacts=artifacts,
    )
    store.put_json(manifest_key, manifest, metadata=json_metadata)
    store.put_json(
        "latest.json",
        {
            "schema_version": 1,
            "release_id": release_id,
            "manifest_key": manifest_key,
        },
        metadata=latest_metadata,
    )
    return manifest
