# Releasing

## Current candidate and authorization boundary

Version `0.1.0` is an unpublished candidate. T-029 implemented the workflows;
T-063 refreshes documentation and local evidence, not publication. No authorized
live GitHub dataset, real-team calibration, or real-data validation is verified.
See [implementation status](implementation-status.md) for the candidate evidence.

T-064 owns publication and post-upload verification and requires separate
maintainer authorization. Preparation does not authorize creating tags or
releases, dispatching either publisher, or changing shared environments or
trusted-publisher configuration. The setup below remains unverified until the
maintainer confirms it; package installation from an index is pending publication
verification. Keep the changelog under Unreleased during preparation.

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

Run the full local gate and package checks first. Use a fresh disposable output
directory rather than deleting any existing distribution evidence:

```bash
mise run check
dist_dir="$(mktemp -d)"
uv build --out-dir "$dist_dir"
uv run twine check "$dist_dir"/*
```

After preparation is reviewed and landed, fetch `origin/main` and verify the
exact candidate commit and its passing Build and mutation CI evidence. During
the authorized release, finalize and land the dated changelog and release-note
wording before tagging, using the actual publication date and reviewed tag/link
targets, never a preparation date. Keep installation claims unverified until
the index checks succeed. If publication slips to another date, reconcile the
changelog and candidate before proceeding; do not rewrite a published tag.
Both publish workflows require the release tag to point at current `origin/main`;
do not advance main between rehearsal and publication. With explicit release
authorization, create and push `v0.1.0` at that reviewed commit. Do not create a
published GitHub release yet: that event starts the PyPI workflow.

Once the tag exists and the trusted TestPyPI publisher is configured, dispatch
and watch the test-index workflow under the same publication authorization:

```bash
gh workflow run test-index.yml --repo fmueller/merge-carlo -f tag=v0.1.0
gh run list --repo fmueller/merge-carlo --workflow test-index.yml --limit 1
gh run watch <run-id> --repo fmueller/merge-carlo --exit-status
python -m pip index versions merge-carlo --index-url https://test.pypi.org/simple
```

Verify TestPyPI metadata and install the exact version in an isolated
environment; exercise `--version`, `--help`, and the offline demo. Index
visibility alone is not installation evidence. Only after that rehearsal
succeeds should a maintainer create the published GitHub release using the
existing tag. Base the release body on
[`release-notes-v0.1.0.md`](release-notes-v0.1.0.md), including the explicit
statement that live GitHub integration was not run. Use the release wording
finalized before tagging, without upgrading the model evidence claims:

```bash
gh release create v0.1.0 --repo fmueller/merge-carlo --verify-tag \
  --title "v0.1.0" --notes-file docs/release-notes-v0.1.0.md
```

`release.yml` then requires the release tag to match the package version, point
at the current `main` commit, be stable rather than a prerelease, and contain
the release evidence text before PyPI trusted publishing can start.

After the PyPI workflow succeeds, verify both published distributions and their
metadata, install `merge-carlo==0.1.0` from PyPI in a clean environment, and run
`merge-carlo --version`, `merge-carlo --help`, and the documented offline demo.
Record the release/tag target, workflow runs, index URLs, and installation/demo
outcomes in T-064. Only then describe the package install instructions as
verified and confirm that the dated changelog's release/tag links resolve.

## Failure and rollback behavior

Build, metadata, tag/version, evidence, checksum, environment-approval, or
trusted-publisher failures stop before a package upload. PyPI versions are
immutable once uploaded: deleting a GitHub release or tag does not retract a
published distribution. Treat an upload as permanent, investigate the failed
release, and publish a corrected higher version rather than reusing `0.1.0`.
TestPyPI is a rehearsal, not evidence that live GitHub integration or the model
has been validated.
