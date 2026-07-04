"""Knowledge Graph expansion for Hybrid Search (optional Neo4j backend).

When LEGALOS_NEO4J_URI is set, the expander asks the graph which law articles
are related to the query (fulltext over entity names → connected MODDA nodes)
and boosts fused chunks that reference those articles. Every failure mode —
driver not installed, server down, no index — degrades to a no-op so RAG never
depends on the graph being available.

`boost_by_articles` is pure and unit-testable.
"""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.services.rag.retrieval import RetrievedChunk

log = logging.getLogger("legalos.rag.graph")

GRAPH_BOOST = 0.05  # additive bonus on the RRF score scale (top RRF ≈ 0.03)

_RELATED_ARTICLES_CYPHER = """
CALL db.index.fulltext.queryNodes('entity_names', $query) YIELD node, score
MATCH (node)--(m)
WHERE m.modda_number IS NOT NULL
RETURN DISTINCT m.modda_number AS article
LIMIT 20
"""


def boost_by_articles(chunks: list[RetrievedChunk], articles: set[str]) -> list[RetrievedChunk]:
    """Reorder chunks so those citing graph-related articles rank higher."""
    if not articles:
        return chunks
    boosted = [
        RetrievedChunk(
            chunk_id=c.chunk_id,
            text=c.text,
            score=c.score + (GRAPH_BOOST if str(c.meta.get("article", "")) in articles else 0.0),
            meta=c.meta,
            origin=c.origin,
        )
        for c in chunks
    ]
    boosted.sort(key=lambda c: c.score, reverse=True)
    return boosted


async def _related_articles(query: str) -> set[str]:
    s = get_settings()
    try:
        from neo4j import AsyncGraphDatabase  # optional dependency
    except ImportError:
        log.debug("neo4j driver not installed; graph expansion skipped")
        return set()
    driver = AsyncGraphDatabase.driver(s.neo4j_uri, auth=(s.neo4j_username, s.neo4j_password))
    try:
        async with driver.session(database=s.neo4j_database) as session:
            result = await session.run(_RELATED_ARTICLES_CYPHER, query=query)
            return {str(record["article"]) async for record in result}
    except Exception as e:
        log.warning("graph expansion failed: %r", e)
        return set()
    finally:
        await driver.close()


async def neo4j_graph_expander(
    db: AsyncSession, tenant_id: uuid.UUID, query: str, fused: list[RetrievedChunk]
) -> list[RetrievedChunk]:
    articles = await _related_articles(query)
    return boost_by_articles(fused, articles)


def get_default_graph_expander():
    """Returns the configured expander callable, or None when the graph is disabled."""
    return neo4j_graph_expander if get_settings().neo4j_uri else None
