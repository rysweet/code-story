import pytest
import asyncio
from codestory.cli.client.service_client import ServiceClient

@pytest.mark.asyncio
async def test_service_client_closes():
    async with ServiceClient("http://localhost") as c:
        pass
    # exits without ResourceWarning