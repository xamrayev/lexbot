"""Government Integration API: official service directory and lookup."""

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user
from app.models import User
from app.services.gov.catalog import GOV_SERVICES, find_services

router = APIRouter(prefix="/gov", tags=["gov"])


def _serialize(service) -> dict:
    return {
        "slug": service.slug,
        "title_ru": service.title_ru,
        "title_uz": service.title_uz,
        "url": service.url,
        "agency": service.agency,
    }


@router.get("/services")
async def list_services(
    query: str | None = Query(default=None, max_length=500),
    user: User = Depends(get_current_user),
):
    if query:
        return [_serialize(s) for s in find_services(query)]
    return [_serialize(s) for s in GOV_SERVICES]
