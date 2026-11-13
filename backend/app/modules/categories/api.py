"""HTTP routes for categories: they only translate HTTP into commands and queries."""

from fastapi import APIRouter

from app.core.dependencies import BusDep
from app.modules.categories.contracts import CategoryRead, ListCategories

router = APIRouter(tags=["categories"])


@router.get("/categories")
def list_categories(bus: BusDep) -> list[CategoryRead]:
    return bus.ask(ListCategories())
