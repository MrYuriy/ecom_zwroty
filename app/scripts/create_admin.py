"""Bootstrap the first admin: python -m app.scripts.create_admin --login admin --full-name "Admin"."""

import argparse
import asyncio
import getpass

from app.database.postgres import async_session
from app.enums.user import RoleEnum
from app.schemas.user import UserCreate
from app.services.user import UserService


async def _create(wms_login: str, full_name: str, password: str) -> None:
    async with async_session() as session:
        user = await UserService(session).create_user(
            UserCreate(wms_login=wms_login, full_name=full_name, password=password, role=RoleEnum.ADMIN)
        )
    print(f"Admin created: {user.wms_login} (id={user.id})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an ADMIN user.")
    parser.add_argument("--login", required=True, help="WMS login")
    parser.add_argument("--full-name", required=True)
    args = parser.parse_args()
    password = getpass.getpass("Password: ")
    asyncio.run(_create(args.login, args.full_name, password))


if __name__ == "__main__":
    main()
