# dependencies/pagination.py
from fastapi import Query


class PaginationParams:
    """Reusable skip/limit pagination used across all list endpoints."""

    def __init__(
        self,
        skip:  int = Query(default=0,  ge=0,         description="Records to skip"),
        limit: int = Query(default=10, ge=1, le=100, description="Max records to return"),
    ):
        self.skip  = skip
        self.limit = limit