from typing import Annotated

from fastapi import Query
from pydantic import BaseModel


class Pagination(BaseModel):
    """Модель для пагинации."""

    limit: Annotated[int, Query(ge=1, le=200)] = 50
    offset: Annotated[int, Query(ge=0)] = 0


PaginationDep = Annotated[Pagination, Query()]
