"""Fetch sites, labels and users concurrently with the async client (read-only).

export KTAPI_AUTH_EMAIL=... KTAPI_AUTH_TOKEN=...
python examples/v6/async_inventory.py
"""

from __future__ import annotations

import asyncio

from kentik_api import AsyncKentikClient


async def main(client: AsyncKentikClient) -> None:
    sites, labels, users = await asyncio.gather(
        client.site.list_sites(),
        client.label.list_labels(),
        client.user.list_users(),
    )
    print(f"sites:  {len(sites.sites or [])}")
    for site in sites.sites or []:
        print(f"  {site.id:>8}  {site.title}")
    print(f"labels: {', '.join(sorted(lbl.name or '' for lbl in labels.labels or []))}")
    print(f"users:  {len(users.users or [])}")


async def run() -> None:
    async with AsyncKentikClient() as kentik:
        await main(kentik)


if __name__ == "__main__":
    asyncio.run(run())
