"""Property-based tests for contributor identity normalisation (Plan 020 Component 1).

Tests the invariants of ``get_or_create_contributor`` in
``src/database/storage.py`` using Hypothesis-generated inputs rather than
hand-picked fixtures.  This surfaces "unknown-unknown" edge cases that a fixed
adversarial corpus cannot cover.

Six invariants are tested:
    C1  Idempotency
    C2  Normalisation is a fixpoint
    C3  Case variants collapse to the same contributor
    C4  Whitespace variants collapse to the same contributor
    C5  Semantically-distinct emails produce distinct contributors
    C6  Unicode display names round-trip faithfully
"""

import hashlib

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from src.database.models.contributor import Contributor
from src.database.storage import get_or_create_contributor
from tests.unit.strategies import case_variants, email_strategy, unicode_name_strategy


@pytest.mark.unit
class TestContributorIdentityProperties:
    """Property-based invariant tests for get_or_create_contributor."""

    # ------------------------------------------------------------------
    # C1 — Idempotency
    # ------------------------------------------------------------------

    @given(email=email_strategy(), name=unicode_name_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_idempotent(self, db_session, email, name):
        """Calling get_or_create_contributor twice with identical inputs returns the same id."""
        c1 = get_or_create_contributor(db_session, email, name)
        c2 = get_or_create_contributor(db_session, email, name)
        assert c1.id == c2.id

    # ------------------------------------------------------------------
    # C2 — Normalisation fixpoint (pure-function, no DB needed)
    # ------------------------------------------------------------------

    @given(email=email_strategy())
    @settings(max_examples=100)
    def test_normalisation_stable(self, email):
        """Normalisation is a fixpoint: strip().lower() applied twice == once."""
        once = email.strip().lower()
        twice = once.strip().lower()
        assert once == twice

    # ------------------------------------------------------------------
    # C3 — Case variants collapse
    # ------------------------------------------------------------------

    @given(email=email_strategy(), data=st.data())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_case_variants_collapse(self, db_session, email, data):
        """Any case-perturbation of a valid email returns the same contributor id."""
        variant = data.draw(case_variants(email))
        c1 = get_or_create_contributor(db_session, email, "Alice")
        c2 = get_or_create_contributor(db_session, variant, "Alice")
        assert c1.id == c2.id

    # ------------------------------------------------------------------
    # C4 — Whitespace variants collapse
    # ------------------------------------------------------------------

    @given(email=email_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_whitespace_variants_collapse(self, db_session, email):
        """Leading/trailing/tab whitespace variants return the same contributor id."""
        stripped = email.strip()
        c1 = get_or_create_contributor(db_session, email, "Alice")
        c2 = get_or_create_contributor(db_session, f"  {stripped}  ", "Alice")
        c3 = get_or_create_contributor(db_session, f"\t{stripped}\t", "Alice")
        assert c1.id == c2.id == c3.id

    # ------------------------------------------------------------------
    # C5 — Distinct emails do not collide
    # ------------------------------------------------------------------

    @given(e1=email_strategy(), e2=email_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_distinct_emails_do_not_collide(self, db_session, e1, e2):
        """Semantically-distinct emails (different after normalisation) produce different ids."""
        assume(e1.strip().lower() != e2.strip().lower())
        c1 = get_or_create_contributor(db_session, e1, "A")
        c2 = get_or_create_contributor(db_session, e2, "B")
        assert c1.id != c2.id

    # ------------------------------------------------------------------
    # C6 — Unicode display names round-trip faithfully
    # ------------------------------------------------------------------

    @given(name=unicode_name_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_unicode_names_round_trip(self, db_session, name):
        """Display names are stored and retrieved without modification.

        A unique email derived from the name ensures that each Hypothesis
        example gets its own fresh contributor row so that name values do not
        bleed across examples within the same test run.
        """
        # Derive a stable, unique, URL-safe email from the name bytes so that
        # each example creates its own contributor (avoids state accumulation).
        digest = hashlib.sha256(name.encode("utf-8")).hexdigest()[:16]
        email = f"{digest}@example.com"

        c = get_or_create_contributor(db_session, email, name)
        db_session.flush()
        reloaded = db_session.get(Contributor, c.id)
        assert reloaded.name == name
