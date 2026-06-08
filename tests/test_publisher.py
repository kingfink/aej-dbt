import unittest
from datetime import UTC, datetime
from pathlib import Path

import publisher


class FakeStore:
    def __init__(self, *, fail_key: str = ""):
        self.fail_key = fail_key
        self.calls = []

    def upload_file(
        self,
        path: Path,
        key: str,
        *,
        metadata: publisher.ObjectMetadata,
    ) -> None:
        self.calls.append(
            ("upload_file", key, metadata.content_type, metadata.cache_control)
        )
        if key == self.fail_key:
            raise RuntimeError(f"failed to upload {key}")

    def put_json(
        self,
        key: str,
        payload: dict[str, object],
        *,
        metadata: publisher.ObjectMetadata,
    ) -> None:
        self.calls.append(
            ("put_json", key, metadata.content_type, metadata.cache_control, payload)
        )
        if key == self.fail_key:
            raise RuntimeError(f"failed to upload {key}")


class ReleaseContractTest(unittest.TestCase):
    def test_release_id_uses_utc_timestamp(self):
        generated_at = datetime(2026, 6, 8, 14, 5, 6, tzinfo=UTC)

        self.assertEqual(publisher.release_id_for(generated_at), "2026-06-08T140506Z")

    def test_manifest_describes_exported_artifacts(self):
        generated_at = datetime(2026, 6, 8, 14, 5, 6, tzinfo=UTC)
        artifacts = [
            publisher.Artifact(
                model="jobs",
                key="releases/2026-06-08T140506Z/jobs.parquet",
                path=Path("jobs.parquet"),
                rows=42,
                size=1024,
                sha256="abc123",
            ),
        ]

        manifest = publisher.build_manifest(
            release_id="2026-06-08T140506Z",
            generated_at=generated_at,
            artifacts=artifacts,
        )

        self.assertEqual(
            manifest,
            {
                "schema_version": 1,
                "release_id": "2026-06-08T140506Z",
                "generated_at": "2026-06-08T14:05:06Z",
                "artifacts": [
                    {
                        "model": "jobs",
                        "key": "releases/2026-06-08T140506Z/jobs.parquet",
                        "rows": 42,
                        "size": 1024,
                        "sha256": "abc123",
                    }
                ],
            },
        )

    def test_publish_release_uploads_latest_last(self):
        generated_at = datetime(2026, 6, 8, 14, 5, 6, tzinfo=UTC)
        release_id = "2026-06-08T140506Z"
        store = FakeStore()
        artifacts = [
            publisher.Artifact(
                model="jobs",
                key=f"releases/{release_id}/jobs.parquet",
                path=Path("jobs.parquet"),
                rows=42,
                size=1024,
                sha256="abc123",
            ),
            publisher.Artifact(
                model="organizations",
                key=f"releases/{release_id}/organizations.parquet",
                path=Path("organizations.parquet"),
                rows=7,
                size=512,
                sha256="def456",
            ),
        ]

        publisher.publish_release(
            store=store,
            release_id=release_id,
            generated_at=generated_at,
            artifacts=artifacts,
        )

        self.assertEqual(
            [call[1] for call in store.calls],
            [
                f"releases/{release_id}/jobs.parquet",
                f"releases/{release_id}/organizations.parquet",
                f"releases/{release_id}/manifest.json",
                "latest.json",
            ],
        )
        self.assertEqual(
            store.calls[0][2:4],
            (
                "application/vnd.apache.parquet",
                "public, max-age=31536000, immutable",
            ),
        )
        self.assertEqual(
            store.calls[-1][2:4],
            ("application/json", "no-cache"),
        )
        self.assertEqual(
            store.calls[-1][4],
            {
                "schema_version": 1,
                "release_id": release_id,
                "manifest_key": f"releases/{release_id}/manifest.json",
            },
        )

    def test_publish_release_does_not_update_latest_after_artifact_failure(self):
        generated_at = datetime(2026, 6, 8, 14, 5, 6, tzinfo=UTC)
        release_id = "2026-06-08T140506Z"
        store = FakeStore(fail_key=f"releases/{release_id}/organizations.parquet")
        artifacts = [
            publisher.Artifact(
                model="jobs",
                key=f"releases/{release_id}/jobs.parquet",
                path=Path("jobs.parquet"),
                rows=42,
                size=1024,
                sha256="abc123",
            ),
            publisher.Artifact(
                model="organizations",
                key=f"releases/{release_id}/organizations.parquet",
                path=Path("organizations.parquet"),
                rows=7,
                size=512,
                sha256="def456",
            ),
        ]

        with self.assertRaisesRegex(RuntimeError, "organizations.parquet"):
            publisher.publish_release(
                store=store,
                release_id=release_id,
                generated_at=generated_at,
                artifacts=artifacts,
            )

        self.assertNotIn("latest.json", [call[1] for call in store.calls])


if __name__ == "__main__":
    unittest.main()
