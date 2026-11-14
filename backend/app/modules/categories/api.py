"""HTTP routes for categories: they only translate HTTP into commands and queries.

The categories module's REST adapter. The composition root mounts `router` under /api/v1. There's no
route to create a category yet: seed.py does that through the bus.
"""

from fastapi import APIRouter

from app.modules.categories.models import CategoryRead
from app.modules.categories.queries.list_categories import ListCategories
from app.web.dependencies import BusDep

router = APIRouter(tags=["categories"])


# GET /api/v1/categories: every category, in creation order. The web app uses it for its category
# pickers and to show names next to expenses. (A route's docstring would become its OpenAPI text, so
# notes go here.)
@router.get("/categories")
def list_categories(bus: BusDep) -> list[CategoryRead]:
    return bus.ask(ListCategories())
