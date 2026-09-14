# Releasing

The v0.1.0 release uses two top-level GitHub Actions workflows:

- `test-index.yml` is manually dispatched and publishes the exact selected
  release tag to TestPyPI.
- `release.yml` runs only for a published GitHub release and publishes the
  matching tag to PyPI.

Both workflows build and metadata-check the distributions before handing the
same files to the publish job. The publish jobs verify a SHA-256 manifest and
use PyPI trusted publishing through GitHub OIDC. There is no PyPI API token or
password in repository secrets or workflow configuration. The only job with
`id-token: write` is the job that uploads the already-reviewed distributions.

## One-time trusted-publisher setup

Register the following publishers independently on PyPI and TestPyPI before
dispatching either workflow. The workflow filename and environment name are
part of the identity; they must match exactly.

| Index | Owner | Repository | Workflow | Environment |
| --- | --- | --- | --- | --- |
| PyPI | `fmueller` | `merge-carlo` | `release.yml` | `pypi` |
| TestPyPI | `fmueller` | `merge-carlo` | `test-index.yml` | `testpypi` |

Create or select the `merge-carlo` project on each index according to that
index's trusted-publisher flow. Configure the `pypi` and `testpypi` GitHub
environments with maintainer approval and deployment rules for release tags or
manual tag runs. This provides a second review boundary after the workflow's
tag/version checks. Do not replace this setup with `PYPI_TOKEN`,
`TEST_PYPI_TOKEN`, `username`, or `password` values.

## Checks and publication order

Run the local package checks first:

```bash
rm -rf dist
uv build
uv run twine check dist/*
```

After the tag `v0.1.0` exists and the trusted TestPyPI publisher is configured,
dispatch and watch the test-index workflow:

```bash
gh workflow run test-index.yml --repo fmueller/merge-carlo -f tag=v0.1.0
gh run list --repo fmueller/merge-carlo --workflow test-index.yml --limit 1
gh run watch <run-id> --repo fmueller/merge-carlo --exit-status
python -m pip index versions merge-carlo --index-url https://test.pypi.org/simple
```

Only after that run succeeds and the package is visible on TestPyPI should a
maintainer create the published GitHub release. The release body must be based
on [`release-notes-v0.1.0.md`](release-notes-v0.1.0.md), including the explicit
statement that live GitHub integration was not run:

```bash
sha="$(git rev-parse origin/main)"
gh release create v0.1.0 --repo fmueller/merge-carlo --target "$sha" \
  --title "v0.1.0" --notes-file docs/release-notes-v0.1.0.md
```

`release.yml` then requires the release tag to match the package version, point
at the current `main` commit, be stable rather than a prerelease, and contain
the release evidence text before PyPI trusted publishing can start.

## Failure and rollback behavior

Build, metadata, tag/version, evidence, checksum, environment-approval, or
trusted-publisher failures stop before a package upload. PyPI versions are
immutable once uploaded: deleting a GitHub release or tag does not retract a
published distribution. Treat an upload as permanent, investigate the failed
release, and publish a corrected higher version rather than reusing `0.1.0`.
TestPyPI is a rehearsal, not evidence that live GitHub integration or the model
has been validated.
