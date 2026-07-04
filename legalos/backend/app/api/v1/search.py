"""Direct hybrid-search endpoint (Enterprise RAG without LLM generation)."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.base import get_db
from app.models import User
from app.schemas import SearchRequest
from app.services.rag.pipeline import retrieve

router = APIRouter(prefix="/search", tags=["search"])


@router.post("")
async def hybrid_search(body: SearchRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await retrieve(db, user.tenant_id, body.query, top_k=body.top_k, use_reranker=False)
    return {"query": body.query, "sources": result.sources}
