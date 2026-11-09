from __future__ import annotations
import argparse
import os
from dotenv import load_dotenv
from .demo import demo_snapshot
from .pipeline import Credentials, SNAPSHOT, atomic_json, build_live_snapshot


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Refresh KOSPI screener market + financial data")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--live", action="store_true", help="Use KRX + OpenDART credentials")
    group.add_argument("--demo", action="store_true", help="Write explicitly fictional demo rows")
    parser.add_argument("--max-companies", type=int, default=0, help="Limit live issuers to test API access (partial universe)")
    args = parser.parse_args()
    if args.demo:
        atomic_json(SNAPSHOT, demo_snapshot())
        print("Saved ILLUSTRATIVE demo data to", SNAPSHOT)
        return
    keys = Credentials(os.getenv("KRX_API_KEY", "").strip(), os.getenv("DART_API_KEY", "").strip())
    if not keys.krx or not keys.dart:
        parser.error("Set KRX_API_KEY and DART_API_KEY in .env before using --live")
    build_live_snapshot(keys, max_companies=args.max_companies or None)


if __name__ == "__main__":
    main()
