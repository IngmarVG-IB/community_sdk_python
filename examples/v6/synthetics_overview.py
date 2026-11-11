"""List synthetic tests and agents (read-only).

export KTAPI_AUTH_EMAIL=... KTAPI_AUTH_TOKEN=...
python examples/v6/synthetics_overview.py            # US
python examples/v6/synthetics_overview.py --region eu
"""

from __future__ import annotations

import argparse
from collections import Counter

from kentik_api import KentikClient


def main(client: KentikClient) -> None:
    tests = client.synthetics.list_tests().tests or []
    print(f"{len(tests)} synthetic tests")
    for test in tests:
        print(f"  {test.id:>8}  {test.status or '-':<24} {test.type or '-':<14} {test.name}")

    agents = client.synthetics.list_agents().agents or []
    by_status = Counter(str(a.status) for a in agents)
    print(f"{len(agents)} agents: " + ", ".join(f"{s}={n}" for s, n in sorted(by_status.items())))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--region", default="us", choices=["us", "eu"])
    args = parser.parse_args()
    with KentikClient(region=args.region) as kentik:  # credentials from KTAPI_AUTH_EMAIL / KTAPI_AUTH_TOKEN
        main(kentik)
