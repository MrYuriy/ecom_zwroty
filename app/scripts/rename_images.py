"""Rename every stored line photo to {BO/WMS or brak}_{reference}_{N}: python -m app.scripts.rename_images

Needed once for photos uploaded before this naming existed; safe to run again (it only renames what differs).
"""

import asyncio

from app.database.postgres import async_session
from app.repositories.return_order import LineImageRepository
from app.services.image_naming import ImageNamer
from app.services.image_storage import ImageStorage


async def _rename_all() -> None:
    async with async_session() as session:
        keys = await LineImageRepository(session).all_keys()
        renamed = await ImageNamer(session, ImageStorage()).renumber(keys)
    print(f"Checked {len(keys)} BO/WMS + reference pairs, renamed {renamed} files.")


def main() -> None:
    asyncio.run(_rename_all())


if __name__ == "__main__":
    main()
