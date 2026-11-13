from fastapi import APIRouter

from app.core.db import SessionDep
from app.modules.categories import service
from app.modules.categories.schemas import CategoryRead

router = APIRouter(tags=["categories"])


@router.get("/categories")
def list_categories(session: SessionDep) -> list[CategoryRead]:
    return service.list_categories(session)
