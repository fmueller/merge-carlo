import os
import subprocess
import sys

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from merge_carlo.simulation.randomness import random_stream


@pytest.mark.unit
def test_keyed_streams_ignore_order_and_other_consumption() -> None:
    keys = [("pr-α", 2, "effort"), ("pr-β", 1, "verification"), ("pr-α", 2, "response")]
    expected = {key: random_stream(42, 3, *key).random(20) for key in keys}
    for key in reversed(keys):
        random_stream(42, 3, "unrelated").random(1000)
        np.testing.assert_array_equal(random_stream(42, 3, *key).random(20), expected[key])
    first = random_stream(42, 3, *keys[0])
    other = random_stream(42, 3, *keys[1])
    first.random(1000)
    np.testing.assert_array_equal(other.random(20), expected[keys[1]])
    assert isinstance(first.bit_generator, np.random.PCG64)


@pytest.mark.unit
def test_every_identity_dimension_and_component_boundary_matters() -> None:
    identities = [
        (42, 3, ("ab", "c")),
        (43, 3, ("ab", "c")),
        (42, 4, ("ab", "c")),
        (42, 3, ("a", "bc")),
        (42, 3, ("c", "ab")),
        (42, 3, ("ab", "c", "")),
    ]
    draws = [random_stream(seed, replication, *key).bytes(64) for seed, replication, key in identities]
    assert len(set(draws)) == len(draws)


@pytest.mark.property
@given(
    seed=st.integers(min_value=0, max_value=2**128),
    replication=st.integers(min_value=0, max_value=2**64),
    component=st.integers(),
)
def test_numeric_keys_are_canonical_strings(seed: int, replication: int, component: int) -> None:
    assert random_stream(seed, replication, "effort", component).bytes(64) == random_stream(
        seed, replication, "effort", str(component)
    ).bytes(64)


@pytest.mark.unit
@pytest.mark.parametrize(("seed", "replication"), [(-1, 0), (0, -1), (-1, -1)])
def test_negative_identity_is_rejected(seed: int, replication: int) -> None:
    with pytest.raises(ValueError, match="non-negative"):
        random_stream(seed, replication, "effort")


@pytest.mark.unit
def test_streams_are_stable_across_python_hash_seeds() -> None:
    code = (
        "from merge_carlo.simulation.randomness import random_stream; "
        "print(random_stream(42, 3, 'α', 2).bytes(64).hex())"
    )
    results = [
        subprocess.check_output([sys.executable, "-c", code], env={**os.environ, "PYTHONHASHSEED": seed}, text=True)
        for seed in ("1", "917")
    ]
    assert results[0] == results[1] == random_stream(42, 3, "α", 2).bytes(64).hex() + "\n"
