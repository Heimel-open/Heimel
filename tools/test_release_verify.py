from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import release_verify


class release_verify_tests(unittest.TestCase):
    def parse(self, text: str) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "release.yaml"
            path.write_text(text, encoding="utf-8")
            return release_verify.parse_release(path)

    def test_current_release_metadata_passes(self) -> None:
        manifest = release_verify.parse_release()
        release_verify.verify_policy(manifest)
        packages = manifest["packages"]
        self.assertIsInstance(packages, list)
        for package in packages:
            release_verify.verify_package_metadata(package)

    def test_parser_rejects_missing_sections(self) -> None:
        with self.assertRaises(release_verify.verification_error):
            self.parse("schema_version: 1\n")

    def test_policy_rejects_actions(self) -> None:
        manifest = release_verify.parse_release()
        release = manifest["release"]
        self.assertIsInstance(release, dict)
        release["github_actions"] = "allowed"
        with self.assertRaises(release_verify.verification_error):
            release_verify.verify_policy(manifest)

    def test_package_tag_must_bind_name_and_version(self) -> None:
        manifest = release_verify.parse_release()
        packages = manifest["packages"]
        self.assertIsInstance(packages, list)
        package = dict(packages[0])
        package["tag"] = "v0.1.0"
        with self.assertRaises(release_verify.verification_error):
            release_verify.verify_package_metadata(package)

    def test_archive_paths_reject_secret_material(self) -> None:
        with self.assertRaises(release_verify.verification_error):
            release_verify.verify_archive_paths(["package/credentials/token.pem"], Path("bad.whl"))

    def test_release_tags_bind_to_reviewed_commit(self) -> None:
        manifest = release_verify.parse_release()
        packages = manifest["packages"]
        self.assertIsInstance(packages, list)
        with self.assertRaises(release_verify.verification_error):
            release_verify.verify_tag_targets(packages, "0" * 40)

    def test_immutable_package_tags_may_precede_review_commit(self) -> None:
        manifest = release_verify.parse_release()
        packages = manifest["packages"]
        self.assertIsInstance(packages, list)
        commit = release_verify.run(["git", "rev-parse", "HEAD"])
        release_verify.verify_tag_targets(packages, commit.strip())


if __name__ == "__main__":
    unittest.main()
