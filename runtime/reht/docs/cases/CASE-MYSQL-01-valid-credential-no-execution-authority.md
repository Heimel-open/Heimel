# CASE-MYSQL-01 — Valid Credential, No Execution Authority

## Purpose

Prove the invariant:

```text
VALID_CREDENTIAL != EXECUTION_AUTHORITY
```

A subject may authenticate successfully to a database and may even hold broad database-native privileges while still lacking current authority to cause the requested consequence.

## Source scenario

The source pentest lab deliberately changes a default-local MySQL server into a remotely reachable service, creates `root@'%'`, assigns a simple password, and grants `ALL PRIVILEGES` across all databases. It then demonstrates credential brute force, SQL execution, schema dumping, password-hash dumping, writable-directory discovery, file enumeration and server enumeration after credentials are obtained.

This case adopts only the defensive governance lesson from that setup. It does not reproduce attack tooling.

## System under test

Canonical consequence path:

```text
authenticated request
  -> exact requested action
  -> fresh REHT authorization
  -> deterministic RACS decision
  -> governed effect path
  -> receipt / outcome evidence
```

The database's own authentication and privilege state is input evidence. It is not the authoritative execution decision.

## Negative case

### Input

```yaml
identity: root
authentication: VALID
database_native_privilege: ALL
requested_effect:
  action: DUMP_SCHEMA
  resource: "*"
purpose: NONE
mandate: NONE
fresh_authority: NONE
governed_effect_path: REQUIRED
```

### Required result

```yaml
identity: VALID
authentication: VALID
database_native_privilege: VALID

reht:
  authority: NON_OPERATIVE
  purpose: ABSENT
  mandate: ABSENT

racs: DENY
execution: PRECLUDED
effect: NULL
receipt: EMITTED
```

### Critical assertion

```text
valid_credentials
AND database_native_privilege
AND NOT fresh_execution_authority
=> DENY
```

A database-native `GRANT ALL PRIVILEGES` MUST NOT mint REHT authority.

## Direct-path conformance

The following architecture is non-conformant:

```text
credential -> mysql -> consequence
```

because it creates a direct consequence path that bypasses fresh authorization and governed commit.

Required assertion:

```text
NO_DIRECT_EFFECT_PATH
```

Any path that lets authenticated database privilege directly produce a consequence MUST be rejected or physically unavailable.

## Null-effect assertion

A DENY decision MUST produce no consequence-bearing effect:

```text
RACS != ALLOW
=> committed_effect == false
```

Required assertion:

```text
NULL_EFFECT_ON_DENY
```

## Positive control

The same authenticated subject requests the same class of operation with a fresh, explicit mandate:

```yaml
identity: root
authentication: VALID
requested_effect:
  action: READ_SCHEMA
  resource: test_db
authority:
  status: OPERATIVE
  purpose: SECURITY_ASSESSMENT
  scope: metadata_only
  expires_at: T+15m
constraints:
  write: false
  credential_material: false
  filesystem_access: false
```

Expected path:

```text
VALID credential
-> fresh exact-action authority
-> purpose / scope / constraint check
-> RACS ALLOW
-> governed effect
-> receipt
```

The positive control is bounded to metadata read. Database-native root status does not widen the authorized scope.

## Drift / substitution checks

The authorization MUST fail closed if any of the following changes before commit:

- authority expires or is revoked;
- resource changes from `test_db`;
- action changes from `READ_SCHEMA`;
- purpose changes or disappears;
- requested operation expands to credential material, filesystem enumeration, writes or data extraction;
- the exact action presented at the effect boundary differs from the authorized action.

Expected outcome for each case:

```text
DENY
+
NULL_EFFECT
+
evidence receipt
```

## Conformance properties exercised

- `FRESH_AUTHORITY_AT_COMMIT`
- `NO_DIRECT_EFFECT_PATH`
- `NULL_EFFECT_ON_DENY`
- exact-action binding
- purpose binding
- scope binding
- constraint enforcement
- action-substitution rejection
- verifiable attempted-effect receipt

## Why the case matters

Traditional database security often collapses authentication, privilege and executable effect into one trust decision:

```text
authenticated root => may execute
```

The governed consequence model separates them:

```text
authenticated root
!=
current authority for this action, resource, purpose and consequence
```

The subject may be technically capable of an operation while remaining unauthorized to cause it.

## Pass criteria

CASE-MYSQL-01 passes only if:

1. valid credentials alone never produce an execution permit;
2. database-native `ALL PRIVILEGES` cannot create or widen REHT authority;
3. missing fresh authority returns `DENY`;
4. `DENY` produces no committed effect;
5. direct database consequence paths are unavailable or rejected;
6. the positive control succeeds only within its exact resource, purpose, scope, lifetime and constraints;
7. every attempted consequence produces correlated decision/effect evidence.
