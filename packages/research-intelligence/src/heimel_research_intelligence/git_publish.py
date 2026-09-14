from __future__ import annotations

from pathlib import Path
import subprocess


class GitPublishError(RuntimeError):
    pass


def _run(repo_root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=False,
        text=True,
        capture_output=True,
    )


def publish(repo_root: Path, paths: list[Path], *, push: bool = False) -> str | None:
    if not paths:
        return None

    inside = _run(repo_root, ["rev-parse", "--is-inside-work-tree"])
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        raise GitPublishError("repo_root is not a git work tree")

    relative = []
    root = repo_root.resolve()
    for path in paths:
        resolved = path.resolve()
        try:
            relative.append(str(resolved.relative_to(root)))
        except ValueError as exc:
            raise GitPublishError("refusing to publish path outside repo_root") from exc

    add = _run(repo_root, ["add", "--", *relative])
    if add.returncode != 0:
        raise GitPublishError(add.stderr.strip() or "git add failed")

    diff = _run(repo_root, ["diff", "--cached", "--quiet"])
    if diff.returncode == 0:
        return None
    if diff.returncode != 1:
        raise GitPublishError(diff.stderr.strip() or "git diff failed")

    commit = _run(repo_root, ["commit", "-m", "research: ingest verified evidence"])
    if commit.returncode != 0:
        raise GitPublishError(commit.stderr.strip() or "git commit failed")

    sha = _run(repo_root, ["rev-parse", "HEAD"])
    if sha.returncode != 0:
        raise GitPublishError(sha.stderr.strip() or "cannot resolve commit")

    if push:
        pushed = _run(repo_root, ["push"])
        if pushed.returncode != 0:
            raise GitPublishError(pushed.stderr.strip() or "git push failed")

    return sha.stdout.strip()
