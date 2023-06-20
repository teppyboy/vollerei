import requests
import concurrent
from vollerei.utils import write_hosts
from vollerei.constants import TELEMETRY_HOSTS


def _check_telemetry(host: str) -> str | None:
    try:
        requests.get(f"https://{host}/", timeout=15)
    except (requests.ConnectionError, requests.Timeout, requests.HTTPError):
        return
    return host


def check_telemetry() -> list[str]:
    futures = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        for host in TELEMETRY_HOSTS:
            futures.append(executor.submit(_check_telemetry, host))
    hosts = []
    for future in concurrent.futures.as_completed(futures):
        host = future.result()
        if host:
            hosts.append(host)
    return hosts


def block_telemetry(telemetry_list: list[str] = None):
    if not telemetry_list:
        telemetry_list = check_telemetry()
    write_hosts(telemetry_list)
