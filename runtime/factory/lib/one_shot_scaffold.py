#!/usr/bin/env python3
"""Reusable thin-app scaffold for one-shot Factory outputs.

The scaffold is intentionally boring: dependency-free static web/PWA files,
explicit commodity capability slots, a product contract, smoke test, and release
candidate binding. It is a production template, not a new runtime.

A scaffold plan is only created from a PortfolioBuildProfileV1 that already
passes the F0 compiler. The generated application contains no direct
consequence-bearing effect path. Such actions must be added through explicit
adapters and the existing governed execution boundary.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from lib.portfolio_intake import (
    AuthorityContext,
    REUSE_CATEGORIES,
    compile_profile,
    profile_digest,
)

CATALOG_PATH = Path(__file__).resolve().parents[1] / "config" / "one_shot_profiles.json"
GENERATOR_VERSION = "one-shot-scaffold.v1"
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class ScaffoldPlan:
    app_slug: str
    app_title: str
    factory_profile: str
    target_repo: str
    build_order_id: str
    profile_id: str
    profile_digest: str
    concept_version: str
    map_version: str
    portfolio_source_sha: str
    components: Mapping[str, str]
    files: Mapping[str, str]
    authority_effect: str = "none"

    def manifest(self) -> dict[str, Any]:
        return {
            "schema_version": GENERATOR_VERSION,
            "app_slug": self.app_slug,
            "app_title": self.app_title,
            "factory_profile": self.factory_profile,
            "target_repo": self.target_repo,
            "build_order_id": self.build_order_id,
            "profile_id": self.profile_id,
            "profile_digest": self.profile_digest,
            "concept_version": self.concept_version,
            "map_version": self.map_version,
            "portfolio_source_sha": self.portfolio_source_sha,
            "components": dict(self.components),
            "files": sorted(self.files),
            "authority_effect": self.authority_effect,
        }


@dataclass(frozen=True)
class ReleaseBinding:
    schema_version: str
    app_slug: str
    release_version: str
    target_repo: str
    target_source_sha: str
    portfolio_source_sha: str
    profile_digest: str
    artifact_digest: str
    build_order_id: str
    authority_effect: str = "none"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "app_slug": self.app_slug,
            "release_version": self.release_version,
            "target_repo": self.target_repo,
            "target_source_sha": self.target_source_sha,
            "portfolio_source_sha": self.portfolio_source_sha,
            "profile_digest": self.profile_digest,
            "artifact_digest": self.artifact_digest,
            "build_order_id": self.build_order_id,
            "authority_effect": self.authority_effect,
        }


def load_catalog(path: Path | None = None) -> dict[str, Any]:
    payload = json.loads((path or CATALOG_PATH).read_text(encoding="utf-8"))
    if payload.get("schema_version") != "one-shot-profile-catalog.v1":
        raise ValueError("unsupported one-shot profile catalog")
    profiles = payload.get("profiles")
    if not isinstance(profiles, dict) or not profiles:
        raise ValueError("one-shot profile catalog has no profiles")
    return payload


def _title_from_slug(slug: str) -> str:
    return " ".join(part.capitalize() for part in slug.split("-"))


def _json(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _resolved_components(
    profile: Mapping[str, Any], profile_defaults: Mapping[str, str]
) -> dict[str, str]:
    resolved: dict[str, str] = {}
    reuse_plan = profile["reuse_plan"]
    for category in REUSE_CATEGORIES:
        decision = reuse_plan[category]
        mode = decision["decision"]
        component = str(decision.get("provider_or_component") or "").strip()
        if mode == "NOT_NEEDED":
            resolved[category] = "not-needed"
        elif mode == "CUSTOM_REQUIRED":
            evidence = str(decision.get("evidence_ref") or "").strip()
            if not evidence:
                raise ValueError(f"{category}: CUSTOM_REQUIRED lacks evidence")
            resolved[category] = component or f"custom-required:{evidence}"
        else:
            default = str(profile_defaults.get(category) or "").strip()
            if not component and not default:
                raise ValueError(
                    f"{category}: REUSE requires provider/component or catalog default"
                )
            resolved[category] = component or default
    return resolved


def _artifact_digest(files: Mapping[str, str]) -> str:
    digest = hashlib.sha256()
    for path in sorted(files):
        digest.update(path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(files[path].encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def _files_for_plan(
    *,
    app_slug: str,
    app_title: str,
    factory_profile: str,
    intent: str,
    objective: str,
    acceptance_criteria: list[str],
    components: Mapping[str, str],
    profile: Mapping[str, Any],
    build_order_id: str,
) -> dict[str, str]:
    source = profile["source"]
    release_target = profile.get("release_target") or {}
    release_version = release_target.get("release_version") or "0.1.0"

    app_config = {
        "schema_version": "thin-app-config.v1",
        "app_slug": app_slug,
        "app_title": app_title,
        "factory_profile": factory_profile,
        "intent": intent,
        "objective": objective,
        "components": dict(components),
        "governance": {
            "direct_effect_path": False,
            "consequence_bearing_actions": "must-use-existing-governed-execution-boundary",
            "authority_effect": "none",
        },
    }
    product_contract = {
        "schema_version": "thin-app-product-contract.v1",
        "profile_id": profile["profile_id"],
        "idea_id": source["idea_id"],
        "concept_version": source["concept_version"],
        "map_version": source["map_version"],
        "portfolio_source_ref": source["source_ref"],
        "portfolio_source_sha": source["source_sha"],
        "objective": objective,
        "acceptance_criteria": acceptance_criteria,
        "out_of_scope": list((profile.get("scope") or {}).get("out_of_scope", [])),
        "primitive_gate": profile["primitive_gate"]["result"],
        "authority_effect": "none",
    }
    release_candidate = {
        "schema_version": "thin-app-release-candidate.v1",
        "release_version": release_version,
        "generator_version": GENERATOR_VERSION,
        "build_order_id": build_order_id,
        "profile_id": profile["profile_id"],
        "profile_digest": profile_digest(profile),
        "concept_version": source["concept_version"],
        "map_version": source["map_version"],
        "portfolio_source_sha": source["source_sha"],
        "target_source_sha": None,
        "state": "CANDIDATE_UNBOUND",
        "authority_effect": "none",
    }

    index_html = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
  <meta name=\"theme-color\" content=\"#ffffff\">
  <link rel=\"manifest\" href=\"manifest.webmanifest\">
  <link rel=\"stylesheet\" href=\"app.css\">
  <title>{app_title}</title>
</head>
<body>
  <main id=\"app\">
    <header><p class=\"eyebrow\">{factory_profile}</p><h1>{app_title}</h1></header>
    <section aria-labelledby=\"purpose\"><h2 id=\"purpose\">Purpose</h2><p>{objective}</p></section>
    <section aria-labelledby=\"status\"><h2 id=\"status\">Status</h2><p id=\"app-status\">Ready</p></section>
  </main>
  <script src=\"app.js\" defer></script>
</body>
</html>
"""
    app_js = """(() => {
  'use strict';
  const status = document.getElementById('app-status');
  if (status) status.textContent = 'Ready';
  window.dispatchEvent(new CustomEvent('thin-app-ready', {detail: {authorityEffect: 'none'}}));
})();
"""
    app_css = """*{box-sizing:border-box}body{font-family:system-ui,sans-serif;margin:0;line-height:1.5}main{max-width:48rem;margin:0 auto;padding:2rem}h1{font-size:clamp(2rem,8vw,4rem);margin:.25rem 0 2rem}.eyebrow{font-size:.8rem;text-transform:uppercase;letter-spacing:.08em}section{margin:2rem 0}button,input,select,textarea{font:inherit;min-height:44px}\n"""
    manifest = {
        "name": app_title,
        "short_name": app_title[:24],
        "start_url": "./",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#ffffff",
    }
    smoke = """#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
required = [
    'index.html', 'app.js', 'app.css', 'manifest.webmanifest',
    'app.config.json', 'product.contract.json', 'release-candidate.json'
]
missing = [name for name in required if not (ROOT / name).is_file()]
if missing:
    raise SystemExit('missing generated files: ' + ', '.join(missing))
config = json.loads((ROOT / 'app.config.json').read_text(encoding='utf-8'))
contract = json.loads((ROOT / 'product.contract.json').read_text(encoding='utf-8'))
release = json.loads((ROOT / 'release-candidate.json').read_text(encoding='utf-8'))
assert config['governance']['direct_effect_path'] is False
assert config['governance']['authority_effect'] == 'none'
assert contract['authority_effect'] == 'none'
binding_path = ROOT / 'release-binding.json'
if binding_path.is_file():
    binding = json.loads(binding_path.read_text(encoding='utf-8'))
    assert binding['schema_version'] == 'thin-app-release-binding.v1'
    assert release['state'] == 'CANDIDATE_BOUND'
    assert release['target_source_sha'] == binding['target_source_sha']
    assert release['artifact_digest'] == binding['artifact_digest']
    assert binding['target_source_sha']
else:
    assert release['state'] == 'CANDIDATE_UNBOUND'
    assert release['target_source_sha'] is None
print('thin-app smoke: OK')
"""
    readme = f"""# {app_title}

Generated from `{factory_profile}` by `{GENERATOR_VERSION}`.

## Objective

{objective}

## Product contract

`product.contract.json` is the bounded acceptance/evidence contract. `app.config.json` records replaceable commodity component slots. `release-candidate.json` remains unbound until an exact target repository SHA is supplied after build/QC.

## Run

Serve this directory with any static HTTP server, for example:

```bash
python3 -m http.server 8000
```

## Smoke

```bash
python3 smoke_test.py
```

## Governance boundary

This scaffold contains no direct consequence-bearing effect path. If the product later sends, buys, publishes, changes enterprise state, controls a device, or performs another consequential action, that adapter must traverse the existing governed execution boundary. The generated application cannot authorize itself.
"""
    return {
        "README.md": readme,
        "index.html": index_html,
        "app.js": app_js,
        "app.css": app_css,
        "manifest.webmanifest": _json(manifest),
        "app.config.json": _json(app_config),
        "product.contract.json": _json(product_contract),
        "release-candidate.json": _json(release_candidate),
        "smoke_test.py": smoke,
    }


def build_scaffold_plan(
    profile: Mapping[str, Any],
    authority_context: AuthorityContext,
    *,
    factory_profile: str,
    app_slug: str,
    app_title: str | None = None,
    catalog: Mapping[str, Any] | None = None,
) -> ScaffoldPlan:
    if not _SLUG_RE.fullmatch(app_slug):
        raise ValueError("app_slug must be lowercase kebab-case")
    compiled = compile_profile(profile, authority_context)
    if not compiled.ok:
        raise ValueError("profile is not build-ready: " + "; ".join(compiled.problems))
    if len(compiled.build_orders) != 1:
        raise ValueError("one-shot scaffold requires exactly one target repository")
    if profile.get("product_family") != "applications":
        raise ValueError("one-shot scaffold requires product_family=applications")
    if profile.get("primitive_gate", {}).get("result") == "NEW_PRIMITIVE_ESTABLISHED":
        raise ValueError("one-shot scaffold cannot introduce a new core primitive")

    catalog_payload = dict(catalog or load_catalog())
    profiles = catalog_payload["profiles"]
    if factory_profile not in profiles:
        raise ValueError(f"unknown one-shot factory profile: {factory_profile}")
    spec = profiles[factory_profile]
    components = _resolved_components(profile, spec["defaults"])
    title = app_title or _title_from_slug(app_slug)
    build_order = compiled.build_orders[0]
    files = _files_for_plan(
        app_slug=app_slug,
        app_title=title,
        factory_profile=factory_profile,
        intent=spec["intent"],
        objective=profile["objective"],
        acceptance_criteria=list(profile["acceptance_criteria"]),
        components=components,
        profile=profile,
        build_order_id=build_order.build_order_id,
    )
    return ScaffoldPlan(
        app_slug=app_slug,
        app_title=title,
        factory_profile=factory_profile,
        target_repo=build_order.target_repo,
        build_order_id=build_order.build_order_id,
        profile_id=profile["profile_id"],
        profile_digest=profile_digest(profile),
        concept_version=profile["source"]["concept_version"],
        map_version=profile["source"]["map_version"],
        portfolio_source_sha=profile["source"]["source_sha"],
        components=components,
        files=files,
    )


def materialize(plan: ScaffoldPlan, output_dir: str | Path) -> Path:
    root = Path(output_dir)
    if root.exists() and any(root.iterdir()):
        raise ValueError(f"refusing to overwrite non-empty output directory: {root}")
    root.mkdir(parents=True, exist_ok=True)
    for relative, content in plan.files.items():
        rel = Path(relative)
        if rel.is_absolute() or ".." in rel.parts:
            raise ValueError(f"unsafe generated path: {relative}")
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    (root / "scaffold-manifest.json").write_text(
        _json(plan.manifest()), encoding="utf-8"
    )
    return root


def bind_release(
    plan: ScaffoldPlan, *, target_source_sha: str, release_version: str
) -> ReleaseBinding:
    if not _SHA_RE.fullmatch(target_source_sha):
        raise ValueError("target_source_sha must be exact lowercase 40-hex SHA")
    if not re.fullmatch(
        r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?$", release_version
    ):
        raise ValueError("release_version must be semantic version")
    return ReleaseBinding(
        schema_version="thin-app-release-binding.v1",
        app_slug=plan.app_slug,
        release_version=release_version,
        target_repo=plan.target_repo,
        target_source_sha=target_source_sha,
        portfolio_source_sha=plan.portfolio_source_sha,
        profile_digest=plan.profile_digest,
        artifact_digest=_artifact_digest(plan.files),
        build_order_id=plan.build_order_id,
    )
