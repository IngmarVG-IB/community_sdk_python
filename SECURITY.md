# Security policy

## Reporting a vulnerability

Please report vulnerabilities privately through GitHub's
[private vulnerability reporting](https://github.com/kentik/community_sdk_python/security/advisories/new)
on the upstream repository (`kentik/community_sdk_python`). Do not open a public issue for security problems.

Include the affected version, a description of the issue, and steps to reproduce if possible.

## Supported versions

| version | supported |
|---------|-----------|
| 2.x (unreleased, `main`) | yes |
| 1.0.x | security fixes only until 2.0.0 is released, then no |
| < 1.0 | no |

## Dependency scanning

`make vuln` runs `pip-audit` against every package pinned in `uv.lock` (runtime, extras and dev groups).
CI runs it on every push and pull request. There are no known, unresolved advisories; any exception
must be listed here with a justification.
