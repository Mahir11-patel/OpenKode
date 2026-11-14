"""Create or revoke an Open-Kode key for the local model prototype."""
from __future__ import annotations

import argparse
import sys

from api_server import ADMIN_EMAIL, create_api_key, revoke_api_key


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    create = actions.add_parser("create", help="Issue a key; the raw value is shown once.")
    create.add_argument("--email", required=True)
    create.add_argument("--label", default="Open-Kode API key")
    create.add_argument("--paid-until", help="Required for subscribers until checkout is connected (YYYY-MM-DD).")
    revoke = actions.add_parser("revoke", help="Revoke a key by its id.")
    revoke.add_argument("--id", required=True)
    args = parser.parse_args()

    try:
        if args.action == "create":
            key_id, raw_key = create_api_key(args.email, args.label, args.paid_until)
            print("API key created. Copy it now; only its hash is stored.")
            print(f"Key id: {key_id}")
            print(f"Account: {args.email.strip().lower()}")
            print(f"API key: {raw_key}")
            if args.email.strip().lower() == ADMIN_EMAIL:
                print("This owner key has permanent access.")
            else:
                print(f"This subscriber key expires after {args.paid_until}.")
        elif revoke_api_key(args.id):
            print("API key revoked.")
        else:
            print("No active API key matched that id.")
            sys.exit(1)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
