# Read-only GitHub transport

`merge_carlo.github.GitHubTransport` is a serial, GET-only Python API. It does
not collect a cohort, persist raw payloads, or provide an ingestion CLI yet.
Only use it with a repository you are authorized to read. It reads
`GITHUB_TOKEN` from the environment; never put a token in a URL or command line.
An absent token permits unauthenticated public reads.

```python
from merge_carlo.github import GitHubTransport, TransportLimits

with GitHubTransport(limits=TransportLimits(max_pages=10)) as github:
    collection = github.collect("/repos/OWNER/REPO/pulls?state=all&per_page=100")
```

The approved origin is fixed to `https://api.github.com`; enterprise and custom
origins are outside v0.1.0. Initial URLs, redirects, and Link `rel=next` targets
must have that exact scheme, host, and port, without user information or
fragments. All requests use the GitHub JSON
Accept header, `merge-carlo` User-Agent, and configurable `api_version`
(default `2022-11-28`). The version is attached to every `Collection`, including
failures; extraction writers must carry it into every extraction manifest.
No cookie jar, environment proxies, automatic redirects, or write methods exist.

`Collection.status` is `complete`, `partial`, or `unavailable`. Earlier pages
are retained after a later failure. Limits yield `partial`, never a falsely
complete empty history. `reason` contains a fixed diagnostic code, not server
text. Raw record lists are transient and excluded from representations; callers
must project them before persistence. Validators are available only for a
single-page completed collection. Pass `etag` and/or `last_modified` to recheck
that resource; these conditional headers are removed on pagination/redirects.
A `304` yields `unavailable` with `not_modified`, requiring the caller's cached
representation, rather than silently fabricating an empty complete result.

## Bounds and retries

`TransportLimits` rejects unknown settings and invalid bounds:

| Setting | Default | Scope |
|---|---:|---|
| `max_requests` | 1000 | Each collection, including redirects/retries |
| `max_pages` | 100 | Successful pages per collection |
| `max_payload_bytes` | 8,000,000 | Each response read, streamed before JSON parsing |
| `max_records` | 100,000 | Each collection |
| `max_retries` | 3 | Each page (shared with redirects) |
| `timeout` | 30 seconds | Each connect/read/write/pool operation |
| `max_wait` | 3600 seconds | Maximum permitted rate-limit wait |

Compressed responses are refused (requests advertise `Accept-Encoding:
identity`) to avoid decompression before the byte budget can be checked.
Timeouts bound individual I/O operations, not total extraction wall time.

Authentication (`401`), permission (`403` without rate-limit evidence), and
inaccessibility (`404`) are not retried. `429`, rate-limited `403`, and
500/502/503/504 are retried, as are connection-level transport failures.
`Retry-After` seconds or HTTP dates and primary `x-ratelimit-reset` epoch seconds
are honored; where both apply, the later deadline wins. Secondary limits without
a deadline wait at least 60 seconds. Exponential fallback plus random jitter
prevents synchronized retries. A primary limit exhausted on success delays the
next request, including the next collection. Excessive waits stop with
`wait_limit`, never retry early. Missing/malformed deadlines fall back
conservatively; non-finite deadlines stop. Injected clock, sleep, jitter and
`httpx.MockTransport` support deterministic offline tests.

The adapter emits no remote diagnostics. It also suppresses the current thread's
httpcore HTTP/1.1 and connection traces during transport work, because DEBUG
traces can contain reflected credentials in response headers and errors. Other
threads and application logging are unchanged. Injected transports are trusted
test infrastructure, not an untrusted extension API.

See GitHub's [REST best practices](https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api).
