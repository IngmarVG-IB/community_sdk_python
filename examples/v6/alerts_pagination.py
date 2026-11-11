"""Iterate over all active alerts with automatic offset/limit pagination (read-only).

export KTAPI_AUTH_EMAIL=... KTAPI_AUTH_TOKEN=...
python examples/v6/alerts_pagination.py
"""

from __future__ import annotations

from kentik_api import KentikClient
from kentik_api.v6.services.alerting_public_v202505 import models


def main(client: KentikClient) -> None:
    request = models.AlertServiceListRequest(filters=models.AlertFilters(states=[models.AlertState.ALERT_STATE_ACTIVE]))
    count = 0
    # iter_list issues as many List calls as needed; page_size is the server-side limit per call.
    for alert in client.alerting_public.alert.iter_list(request, page_size=200):
        count += 1
        print(f"  {alert.id}  {alert.severity}  started {alert.start_time_at}")
    print(f"{count} active alerts")


if __name__ == "__main__":
    with KentikClient() as kentik:
        main(kentik)
