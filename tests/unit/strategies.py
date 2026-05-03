"""Hypothesis strategies for property-based contributor identity tests.

Provides re-usable strategies that generate realistic (but synthetic) email
addresses, case-perturbed variants of those emails, and unicode display names.
"""

from hypothesis import strategies as st

# Characters allowed in the local part of an email (RFC 5322 subset, ASCII only).
# Restricting to the ASCII range (0x21–0x7E) ensures that case-folding is
# bijective — no Unicode character like ß expands to two characters when
# uppercased, which would break the case-variant collapse invariant.
_local_char = st.characters(
    min_codepoint=0x21,
    max_codepoint=0x7E,
    whitelist_categories=("Ll", "Lu", "Nd"),
    whitelist_characters="._+-",
)


def email_strategy() -> st.SearchStrategy[str]:
    """Plausible emails with mixed case and optional surrounding whitespace.

    The generated strings include optional leading/trailing whitespace so that
    normalisation (``email.strip().lower()``) is meaningful and testable.
    """
    local = st.text(_local_char, min_size=1, max_size=20)
    domain = st.sampled_from(
        ["example.com", "users.noreply.github.com", "corp.local"]
    )
    leading_ws = st.sampled_from(["", " ", "  ", "\t"])
    trailing_ws = st.sampled_from(["", " ", "  ", "\t"])
    return st.builds(
        lambda l, d, lw, tw: f"{lw}{l}@{d}{tw}",
        local,
        domain,
        leading_ws,
        trailing_ws,
    )


@st.composite
def case_variants(draw, email: str) -> str:
    """Generate a case-perturbed variant of *email*.

    Each alphabetic character in *email* is independently flipped to upper- or
    lower-case.  Non-alphabetic characters (digits, ``@``, ``.``, etc.) are
    preserved verbatim so the result is still a syntactically valid email.
    """
    choices = draw(
        st.lists(st.booleans(), min_size=len(email), max_size=len(email))
    )
    return "".join(
        c.upper() if (flip and c.isalpha()) else c.lower() if (not flip and c.isalpha()) else c
        for c, flip in zip(email, choices)
    )


def unicode_name_strategy() -> st.SearchStrategy[str]:
    """Display names that include a wide range of Unicode code points.

    Surrogate characters (``Cs``) and control characters (``Cc``) are excluded
    because they cannot be stored as valid text or are invisible and confusing.
    """
    return st.text(
        st.characters(
            min_codepoint=0x20,
            max_codepoint=0x10FFFF,
            blacklist_categories=("Cs", "Cc"),
        ),
        min_size=1,
        max_size=50,
    )
