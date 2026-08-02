from __future__ import annotations

import argparse
import concurrent.futures
import statistics
import time
import urllib.error
import urllib.request


def request_once(url: str, timeout: float) -> tuple[bool, float, int]:
    started = time.perf_counter()
    status = 0
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            status = response.status
            response.read()
            ok = 200 <= status < 400
    except urllib.error.HTTPError as error:
        status = error.code
        ok = False
    except Exception:
        ok = False
    return ok, (time.perf_counter() - started) * 1000, status


def percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * quantile))))
    return ordered[index]


def main() -> int:
    parser = argparse.ArgumentParser(description="Small dependency-free Yoru HTTP load probe")
    parser.add_argument("--url", default="http://127.0.0.1:8000/health/live")
    parser.add_argument("--requests", type=int, default=500)
    parser.add_argument("--concurrency", type=int, default=20)
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--max-error-rate", type=float, default=0.01)
    parser.add_argument("--max-p95-ms", type=float, default=500.0)
    args = parser.parse_args()

    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        results = list(
            executor.map(
                lambda _: request_once(args.url, args.timeout),
                range(args.requests),
            )
        )
    elapsed = time.perf_counter() - started
    latencies = [latency for _, latency, _ in results]
    failures = sum(1 for ok, _, _ in results if not ok)
    error_rate = failures / max(1, len(results))
    p95 = percentile(latencies, 0.95)
    print(f"requests={len(results)} failures={failures} error_rate={error_rate:.4f}")
    print(f"rps={len(results) / max(elapsed, 0.001):.2f} mean_ms={statistics.mean(latencies):.2f} p95_ms={p95:.2f}")
    return 1 if error_rate > args.max_error_rate or p95 > args.max_p95_ms else 0


if __name__ == "__main__":
    raise SystemExit(main())
