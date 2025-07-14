from pathlib import Path
from typing import List

__all__ = ["IngestionPipeline"]


class IngestionPipeline:
    def __init__(self, *, incremental: bool = False):
        self.incremental: bool = incremental
        self.steps: List = []

    async def run(self, path: str | Path) -> None:
        raise NotImplementedError("Pipeline steps not wired yet")
