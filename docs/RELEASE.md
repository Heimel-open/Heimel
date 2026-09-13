# HEIMEL public package release

The public repository is a reference distribution. Canonical runtime ownership
remains in the source repositories named by each package manifest.

## Local release gate

Run this from a clean checkout:

```bash
python3 tools/release_verify.py
```

The verifier is fail-closed. A passing measured receipt proves that:

- all package test suites pass;
- wheels and source distributions build from the reviewed commit;
- artifact metadata matches `release.yaml`;
- the wheels install in `release.yaml` publish order; and
- all public package imports work in a clean virtual environment.

It also records SHA-256 digests in `release-receipt.json`. The receipt is
measured evidence, not permission to publish.

## Publication handoff

The package tags declared in `release.yaml` are published and all point to the
reviewed commit containing the exact package sources. The remaining handoff is
registry publication and post-upload verification.

An owner with registry credentials must review the receipt, push the immutable
upload the artifacts in publish order,
and then verify the exact versions from the registry in a clean environment.
No credentials or upload authority belong in this repository.

The current package order is:

1. `heimel-kernel` `0.1.0`
2. `valo-workflow-isa` `1.0.1`
3. `valo-function-fabric` `1.1.0`
