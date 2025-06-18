from __future__ import annotations
import redis, asyncio
from codestory.graphdb.neo4j_connector import create_connector
from codestory_service.settings import get_settings

class HostServiceHealth:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def check_neo4j(self) -> bool:
        try:
            connector = create_connector()
            await connector.verify_connectivity()
            return True
        except Exception:
            return False

    async def check_redis(self) -> bool:
        try:
            redis.from_url(self.settings.redis.uri).ping()
            return True
        except Exception:
            return False

    async def summary(self) -> dict[str, bool]:
        return {
            "neo4j": await self.check_neo4j(),
            "redis": await self.check_redis(),
            "service": True,
        }