import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from lib.security_matrix import classify_paths, evaluate


POLICY = {
    "sensitive_paths": {
        "authority": ["**/reht/**", "**/policy/**"],
        "execution": ["**/runtime/**"],
    },
    "required_evidence": {
        "default": ["targeted_tests"],
        "authority": ["authority_non_broadening"],
        "execution": ["deny_and_halt_tests"],
    },
    "manifest": {"allowed_statuses": ["PASS", "NOT_APPLICABLE"]},
}


def proof(*items):
    return {
        "evidence": {
            item: {"status": "PASS", "proof": f"tests::{item}"} for item in items
        }
    }


class SecurityMatrixTest(unittest.TestCase):
    def test_non_sensitive_change_passes_without_manifest(self):
        result = evaluate(["docs/readme.md"], None, POLICY)
        self.assertEqual(result.status, "PASS")
        self.assertEqual(result.categories, ())

    def test_sensitive_change_fails_closed_without_manifest(self):
        result = evaluate(["src/reht/clearance.py"], None, POLICY)
        self.assertEqual(result.status, "FAIL")
        self.assertIn("authority_non_broadening", result.missing_evidence)

    def test_all_required_evidence_passes(self):
        result = evaluate(
            ["src/reht/clearance.py", "src/runtime/executor.py"],
            proof(
                "targeted_tests",
                "authority_non_broadening",
                "deny_and_halt_tests",
            ),
            POLICY,
        )
        self.assertEqual(result.status, "PASS")
        self.assertEqual(result.missing_evidence, ())

    def test_evidence_requires_proof_reference(self):
        manifest = proof("targeted_tests", "authority_non_broadening")
        manifest["evidence"]["authority_non_broadening"]["proof"] = ""
        result = evaluate(["src/reht/clearance.py"], manifest, POLICY)
        self.assertEqual(result.status, "FAIL")
        self.assertEqual(result.missing_evidence, ("authority_non_broadening",))

    def test_path_classification_is_deterministic(self):
        self.assertEqual(
            classify_paths(
                ["src/runtime/executor.py", "src/reht/gate.py"], POLICY
            ),
            ("authority", "execution"),
        )

    def test_installed_security_gate_runs_without_repo_lib(self):
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            installed_bin = temp / ".valo" / "bin"
            installed_bin.mkdir(parents=True)
            installed_gate = installed_bin / "valo-security-matrix"
            installed_gate.write_text(
                (repo_root / "bin" / "valo-security-matrix").read_text(
                    encoding="utf-8"
                ),
                encoding="utf-8",
            )

            target = temp / "target"
            target.mkdir()

            def git(*args: str) -> str:
                result = subprocess.run(
                    ["git", *args],
                    cwd=target,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                return result.stdout.strip()

            git("init", "-q")
            git("config", "user.email", "factory-test@example.invalid")
            git("config", "user.name", "VALO Factory Test")
            docs = target / "docs"
            docs.mkdir()
            readme = docs / "readme.md"
            readme.write_text("base\n", encoding="utf-8")
            git("add", "docs/readme.md")
            git("commit", "-q", "-m", "base")
            base_sha = git("rev-parse", "HEAD")

            readme.write_text("base\nhead\n", encoding="utf-8")
            git("add", "docs/readme.md")
            git("commit", "-q", "-m", "head")
            head_sha = git("rev-parse", "HEAD")

            policy = temp / "security_matrix.yaml"
            policy.write_text(
                "sensitive_paths:\n"
                "  authority:\n"
                "    - '**/reht/**'\n"
                "required_evidence:\n"
                "  default:\n"
                "    - targeted_tests\n"
                "manifest:\n"
                "  allowed_statuses:\n"
                "    - PASS\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(installed_gate),
                    "--base-sha",
                    base_sha,
                    "--head-sha",
                    head_sha,
                    "--policy",
                    str(policy),
                ],
                cwd=target,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["status"], "PASS")
            self.assertNotIn("ModuleNotFoundError", result.stderr)


if __name__ == "__main__":
    unittest.main()
