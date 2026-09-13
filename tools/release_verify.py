#!/usr/bin/env python3
"""local, fail-closed release verifier for the heimel public packages."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tarfile
import tempfile
import time
import tomllib
import venv
import zipfile


root = Path(__file__).resolve().parents[1]
release_file = root / "release.yaml"
receipt_file = root / "release-receipt.json"
dist_dir = root / "dist"


class verification_error(RuntimeError):
    pass


def run(command: list[str], *, cwd: Path = root, env: dict[str, str] | None = None) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if completed.returncode:
        rendered = " ".join(command)
        raise verification_error(f"command failed ({completed.returncode}): {rendered}\n{completed.stdout}")
    return completed.stdout


def scalar(value: str) -> str | int | bool:
    value = value.strip()
    if value in {"true", "false"}:
        return value == "true"
    if value.isdigit():
        return int(value)
    return value


def parse_release(path: Path = release_file) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    release_match = re.search(r"(?ms)^release:\n(?P<body>.*?)(?=^packages:)", text)
    packages_match = re.search(
        r"(?ms)^packages:\n(?P<body>.*?)(?=^required_local_gates:)", text
    )
    if not release_match or not packages_match:
        raise verification_error("release.yaml is missing required release or packages sections")

    release: dict[str, object] = {}
    for key, value in re.findall(r"^  ([a-z_]+): (.+)$", release_match.group("body"), re.MULTILINE):
        release[key] = scalar(value)

    packages: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    for line in packages_match.group("body").splitlines():
        item = re.match(r"^  - ([a-z_]+): (.+)$", line)
        field = re.match(r"^    ([a-z_]+): (.+)$", line)
        if item:
            current = {item.group(1): scalar(item.group(2))}
            packages.append(current)
        elif field and current is not None:
            current[field.group(1)] = scalar(field.group(2))
        elif line.strip():
            raise verification_error(f"unsupported packages syntax: {line}")

    if not packages:
        raise verification_error("release.yaml contains no packages")
    return {"release": release, "packages": packages}


def verify_policy(manifest: dict[str, object]) -> None:
    release = manifest["release"]
    assert isinstance(release, dict)
    required = {
        "registry": "pypi",
        "registry_organization": "heimel",
        "publication_mode": "manual-local",
        "github_actions": "forbidden",
        "tags_are_immutable": True,
    }
    for key, expected in required.items():
        if release.get(key) != expected:
            raise verification_error(f"release policy mismatch for {key}: expected {expected!r}")

    workflows = root / ".github" / "workflows"
    if workflows.exists() and any(workflows.iterdir()):
        raise verification_error("github actions workflows are forbidden")


def normalized_distribution(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def read_repo_manifest(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^(name|version):\s*(\S+)\s*$", line)
        if match:
            values[match.group(1)] = match.group(2)
    return values


def verify_package_metadata(package: dict[str, object]) -> dict[str, str]:
    required = {"distribution", "import", "version", "path", "tag", "publish_order"}
    missing = required.difference(package)
    if missing:
        raise verification_error(f"package entry missing fields: {sorted(missing)}")

    distribution = str(package["distribution"])
    import_name = str(package["import"])
    version = str(package["version"])
    package_path = root / str(package["path"])
    tag = str(package["tag"])

    if distribution != distribution.lower() or import_name != import_name.lower() or tag != tag.lower():
        raise verification_error(f"identifiers must be lowercase: {distribution}")
    if tag != f"{distribution}-v{version}":
        raise verification_error(f"tag does not bind distribution and version: {tag}")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", distribution):
        raise verification_error(f"invalid distribution identifier: {distribution}")
    if not re.fullmatch(r"[a-z][a-z0-9_]*", import_name):
        raise verification_error(f"invalid import identifier: {import_name}")
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise verification_error(f"version is not strict three-part semver: {version}")
    if not package_path.is_dir():
        raise verification_error(f"package path does not exist: {package_path}")

    with (package_path / "pyproject.toml").open("rb") as handle:
        project = tomllib.load(handle)["project"]
    if project.get("name") != distribution or project.get("version") != version:
        raise verification_error(f"pyproject mismatch for {distribution}")

    wheel = tomllib.loads((package_path / "pyproject.toml").read_text(encoding="utf-8"))
    wheel_packages = wheel.get("tool", {}).get("hatch", {}).get("build", {}).get("targets", {}).get("wheel", {}).get("packages", [])
    if f"src/{import_name}" not in wheel_packages:
        raise verification_error(f"wheel package does not expose {import_name}")

    repo_manifest = read_repo_manifest(package_path / "repo-manifest.yaml")
    if repo_manifest.get("name") != distribution or repo_manifest.get("version") != version:
        raise verification_error(f"repo-manifest mismatch for {distribution}")

    return {
        "distribution": distribution,
        "import": import_name,
        "version": version,
        "path": str(package["path"]),
        "tag": tag,
    }


blocked_path_parts = {
    ".env",
    ".git",
    "credentials",
    "private",
    "secrets",
}
blocked_suffixes = {".key", ".p12", ".pem"}


def verify_archive_paths(paths: list[str], artifact: Path) -> None:
    for raw in paths:
        path = PurePosixPath(raw)
        lowered = {part.lower() for part in path.parts}
        if lowered.intersection(blocked_path_parts) or path.suffix.lower() in blocked_suffixes:
            raise verification_error(f"blocked path in {artifact.name}: {raw}")
        if path.is_absolute() or ".." in path.parts:
            raise verification_error(f"unsafe path in {artifact.name}: {raw}")


def artifact_metadata(artifact: Path) -> tuple[str, str]:
    if artifact.suffix == ".whl":
        with zipfile.ZipFile(artifact) as archive:
            names = archive.namelist()
            verify_archive_paths(names, artifact)
            metadata_name = next((name for name in names if name.endswith(".dist-info/METADATA")), None)
            if metadata_name is None:
                raise verification_error(f"wheel metadata missing: {artifact.name}")
            metadata = archive.read(metadata_name).decode("utf-8")
    elif artifact.name.endswith(".tar.gz"):
        with tarfile.open(artifact, "r:gz") as archive:
            names = archive.getnames()
            verify_archive_paths(names, artifact)
            member = next((item for item in archive.getmembers() if item.name.endswith("/PKG-INFO")), None)
            if member is None:
                raise verification_error(f"sdist metadata missing: {artifact.name}")
            extracted = archive.extractfile(member)
            if extracted is None:
                raise verification_error(f"cannot read sdist metadata: {artifact.name}")
            metadata = extracted.read().decode("utf-8")
    else:
        raise verification_error(f"unexpected artifact type: {artifact.name}")

    name = re.search(r"(?m)^Name: (.+)$", metadata)
    version = re.search(r"(?m)^Version: (.+)$", metadata)
    if not name or not version:
        raise verification_error(f"name or version missing from {artifact.name}")
    return name.group(1).strip(), version.group(1).strip()


def create_venv(path: Path) -> Path:
    venv.EnvBuilder(with_pip=True, clear=True).create(path)
    return path / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def verify_git_state() -> tuple[str, int]:
    status = run(["git", "status", "--porcelain"])
    if status.strip():
        raise verification_error("tracked or unignored files are dirty; commit or remove them before release verification")
    sha = run(["git", "rev-parse", "HEAD"]).strip()
    timestamp = int(run(["git", "show", "-s", "--format=%ct", "HEAD"]).strip())
    return sha, timestamp


def verify_tag_targets(packages: list[dict[str, str]], commit: str) -> None:
    for package in packages:
        tag = package["tag"]
        target = run(["git", "rev-list", "-1", f"{tag}^{{commit}}"] ).strip()
        if not target:
            raise verification_error(
                f"tag {tag} is missing"
            )
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", target, commit],
            cwd=root,
            check=False,
        )
        if ancestor.returncode:
            raise verification_error(f"tag {tag} is not an ancestor of reviewed commit {commit}")
        package_path = package["path"]
        unchanged = subprocess.run(
            ["git", "diff", "--quiet", f"{tag}^{{commit}}", commit, "--", package_path],
            cwd=root,
            check=False,
        )
        if unchanged.returncode:
            raise verification_error(f"package path changed after immutable tag {tag}: {package_path}")


def build_and_test(packages: list[dict[str, str]], timestamp: int) -> list[dict[str, object]]:
    if dist_dir.exists():
        raise verification_error("dist already exists; move it aside before verification")
    dist_dir.mkdir()
    environment = os.environ.copy()
    environment["SOURCE_DATE_EPOCH"] = str(timestamp)
    environment["PYTHONHASHSEED"] = "0"

    with tempfile.TemporaryDirectory(prefix="heimel-release-") as temporary:
        temporary_path = Path(temporary)
        build_python = create_venv(temporary_path / "build-venv")
        run([str(build_python), "-m", "pip", "install", "--disable-pip-version-check", "build==1.3.0", "pytest>=8,<9"])

        # Test the source tree before building it.  Installing the packages as
        # editable projects here is deliberately avoided: Function Fabric has
        # internal package dependencies which are not expected to be available
        # from PyPI until the publish-order test below installs our artifacts.
        run(
            [
                str(build_python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "pydantic>=2.6,<3",
                "rfc8785>=0.1.4",
                "hypothesis>=6.100",
            ]
        )
        source_path = os.pathsep.join(
            str(root / package["path"] / "src") for package in packages
        )
        test_environment = environment | {"PYTHONPATH": source_path}
        for package in packages:
            package_path = root / package["path"]
            run(
                [str(build_python), "-m", "pytest", "-q", str(package_path / "tests")],
                env=test_environment,
            )
            run([str(build_python), "-m", "build", "--outdir", str(dist_dir), str(package_path)], env=environment)

        artifacts = sorted(path for path in dist_dir.iterdir() if path.is_file())
        if len(artifacts) != len(packages) * 2:
            raise verification_error(f"expected {len(packages) * 2} artifacts, found {len(artifacts)}")

        expected = {(item["distribution"], item["version"]) for item in packages}
        observed: dict[tuple[str, str], int] = {}
        records: list[dict[str, object]] = []
        for artifact in artifacts:
            name, version = artifact_metadata(artifact)
            key = (normalized_distribution(name), version)
            if key not in expected:
                raise verification_error(f"unexpected artifact metadata: {name} {version}")
            observed[key] = observed.get(key, 0) + 1
            records.append(
                {
                    "file": artifact.name,
                    "distribution": key[0],
                    "version": version,
                    "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                    "bytes": artifact.stat().st_size,
                }
            )
        if observed != {key: 2 for key in expected}:
            raise verification_error(f"artifact set mismatch: {observed}")

        install_python = create_venv(temporary_path / "install-venv")
        run(
            [
                str(install_python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "pydantic>=2.6,<3",
                "rfc8785>=0.1.4",
            ]
        )
        wheels_by_package = {
            package["distribution"]: next(
                path
                for path in artifacts
                if path.suffix == ".whl"
                and normalized_distribution(artifact_metadata(path)[0])
                == normalized_distribution(package["distribution"])
            )
            for package in packages
        }
        for package in packages:
            # --no-index makes this a real proof that the exact locally-built
            # artifacts, in manifest publish order, satisfy dependencies.
            run(
                [
                    str(install_python),
                    "-m",
                    "pip",
                    "install",
                    "--disable-pip-version-check",
                    "--no-index",
                    str(wheels_by_package[package["distribution"]]),
                ]
            )
        imports = ";".join(f"import {item['import']}" for item in packages)
        run([str(install_python), "-c", imports])

    return records


def verify(*, metadata_only: bool = False) -> dict[str, object]:
    manifest = parse_release()
    verify_policy(manifest)
    raw_packages = manifest["packages"]
    assert isinstance(raw_packages, list)
    packages = [verify_package_metadata(item) for item in raw_packages]
    orders = [int(item["publish_order"]) for item in raw_packages]
    if orders != list(range(1, len(packages) + 1)):
        raise verification_error("publish_order must be contiguous and match manifest order")

    sha = run(["git", "rev-parse", "HEAD"]).strip()
    verify_tag_targets(packages, sha)
    artifacts: list[dict[str, object]] = []
    if not metadata_only:
        sha, timestamp = verify_git_state()
        artifacts = build_and_test(packages, timestamp)

    return {
        "schema_version": 1,
        "verdict": "pass",
        "evidence": "measured" if not metadata_only else "claimed",
        "repository": "heimel-open/heimel",
        "commit": sha,
        "generated_at": int(time.time()),
        "github_actions": "absent",
        "publication_authority": False,
        "tag_targets": {
            item["tag"]: run(["git", "rev-list", "-1", f"{item['tag']}^{{commit}}"] ).strip()
            for item in packages
        },
        "packages": packages,
        "artifacts": artifacts,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata-only", action="store_true")
    arguments = parser.parse_args()
    try:
        receipt = verify(metadata_only=arguments.metadata_only)
    except verification_error as error:
        print(f"verdict: fail\nreason: {error}", file=sys.stderr)
        return 1
    if not arguments.metadata_only:
        receipt_file.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
