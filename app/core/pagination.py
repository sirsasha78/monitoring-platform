from typing import Annotated

from fastapi import Depends, Query
from pydantic import BaseModel


class Pagination(BaseModel):
    """Модель для пагинации."""

    limit: int
    offset: int


async def get_pagination(
    limit: Annotated[int, Query(ge=1, le=200)] = 50, offset: Annotated[int, Query(ge=0)] = 0
) -> Pagination:
    """Зависимость пагинации: limit/offset из query-параметров."""

    return Pagination(limit=limit, offset=offset)


PaginationDep = Annotated[Pagination, Depends(get_pagination)]
