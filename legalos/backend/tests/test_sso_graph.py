"""Tests for SSO state tokens and knowledge-graph boosting."""

from app.services.rag.graph import GRAPH_BOOST, boost_by_articles, get_default_graph_expander
from app.services.rag.retrieval import RetrievedChunk
from app.services.sso.oidc import make_state, verify_state

SECRET = "test-secret"


def test_state_roundtrip():
    state = make_state(secret=SECRET)
    assert verify_state(state, secret=SECRET)


def test_state_rejects_tampering():
    state = make_state(secret=SECRET)
    tampered = state[:-4] + ("aaaa" if not state.endswith("aaaa") else "bbbb")
    assert not verify_state(tampered, secret=SECRET)
    assert not verify_state(state, secret="other-secret")
    assert not verify_state("not.a.state", secret=SECRET)
    assert not verify_state("garbage", secret=SECRET)


def test_state_expires():
    old = make_state(secret=SECRET, now=1_000_000)
    assert not verify_state(old, secret=SECRET, now=1_000_000 + 601)
    assert verify_state(old, secret=SECRET, now=1_000_000 + 599)


def _chunk(chunk_id: str, score: float, article: str = "") -> RetrievedChunk:
    return RetrievedChunk(chunk_id=chunk_id, text="t", score=score, meta={"article": article}, origin="fused")


def test_boost_by_articles_reorders_matches():
    chunks = [_chunk("a", 0.030, article="100"), _chunk("b", 0.029, article="115")]
    boosted = boost_by_articles(chunks, {"115"})
    assert boosted[0].chunk_id == "b"
    assert abs(boosted[0].score - (0.029 + GRAPH_BOOST)) < 1e-9


def test_boost_noop_without_articles():
    chunks = [_chunk("a", 0.03), _chunk("b", 0.02)]
    assert boost_by_articles(chunks, set()) is chunks


def test_graph_expander_disabled_by_default():
    # neo4j_uri is empty in test settings → graph expansion off
    assert get_default_graph_expander() is None
