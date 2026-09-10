"""Stateless purpose-keyed random streams for paired simulation experiments."""

import hashlib
import json

from numpy.random import PCG64, Generator, SeedSequence


def random_stream(root_seed: int, replication: int, *key: str | int) -> Generator:
    """Return a fresh stream; repeated calls restart the same sequence.

    Keys are ordered strings or integer identifiers (converted with ``str``),
    typically proposal ID, revision/visit, and event purpose. Never include a
    scenario ID in keys for common latent variables: scenarios must transform
    the same draw rather than draw from different streams. Retain the returned
    generator when multiple successive draws are needed.
    """
    if root_seed < 0 or replication < 0:
        raise ValueError("root seed and replication must be non-negative")
    payload = json.dumps([str(root_seed), str(replication), *map(str, key)], ensure_ascii=True, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode("ascii")).digest()
    entropy = int.from_bytes(digest, "big")
    return Generator(PCG64(SeedSequence(entropy)))
