from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, List

from neo4j import AsyncGraphDatabase, AsyncDriver  # type: ignore[attr-defined]

class GraphService:
    """
    Async wrapper around Neo4j AsyncDriver that supports
    context-manager usage, basic Cypher execution, and graceful close.
    """

    def __init__(self, uri: str, user: str, password: str):
        self._uri = uri
        self._user = user
        self._password = password
        self.driver: AsyncDriver | None = None

    async def __aenter__(self) -> "GraphService":
        self.driver = AsyncGraphDatabase.driver(self._uri, auth=(self._user, self._password))
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        await self.close()

    async def execute(self, cypher: str, **params: Any) -> List[dict[str, Any]]:
        if self.driver is None:
            raise RuntimeError("Driver not initialized – use 'async with GraphService(...)'.")
        async with self.driver.session() as session:
            result = await session.run(cypher, params)
            return [record.data() async for record in result]

    async def close(self) -> None:
        if self.driver is not None:
            await self.driver.close()

__all__ = ["GraphService"]