"""Import fictional showcase records once from an explicit local directory.

Usage inside the backend container:
    uv run python showcase_import.py /tmp/platform_showcase_v1
"""

import argparse
import asyncio
from pathlib import Path

from app.core.database import AsyncSessionLocal
from app.services.showcase_seed import import_showcase


async def main(directory: Path) -> None:
    async with AsyncSessionLocal() as db:
        counts = await import_showcase(db, directory)
    print("Создано:", ", ".join(f"{kind}: {count}" for kind, count in counts.items()))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    asyncio.run(main(args.directory))
