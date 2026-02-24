#!/usr/bin/env python3
"""Revoke Linode API tokens by label.

Reads LINODE_TOKEN_<NAME> values from .env and token labels from
the corresponding latr-configs/<name>.yaml files.
"""

import argparse
from pathlib import Path

import requests
import yaml

API = "https://api.linode.com/v4/profile/tokens"
BASE = Path(__file__).parent


def load_env():
    """Parse .env into a dict, skipping comments and blank lines."""
    env = {}
    for line in (BASE / ".env").read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip()
    return env


def load_labels(config_path):
    """Extract token labels from a latr config YAML."""
    with open(config_path) as f:
        cfg = yaml.safe_load(f)
    return [t["label"] for t in cfg.get("tokens", [])]


def main():
    parser = argparse.ArgumentParser(description="Revoke Linode API tokens by label.")
    parser.add_argument(
        "--do-it", action="store_true",
        help="Actually revoke the tokens (default is dry-run)",
    )
    args = parser.parse_args()

    env = load_env()

    for config_file in sorted((BASE / "latr-configs").glob("*.yaml")):
        name = config_file.stem
        name_upper = name.upper().replace("-", "_")
        env_var = f"LINODE_TOKEN_{name_upper}"

        linode_token = env.get(env_var)
        if not linode_token:
            print(f"\n--- {config_file.name}: no {env_var} in .env, skipping")
            continue

        labels = load_labels(config_file)
        print(f"\n--- {config_file.name} (token: ...{linode_token[-8:]})")

        headers = {"Authorization": f"Bearer {linode_token}"}
        resp = requests.get(API, headers=headers)
        resp.raise_for_status()
        all_tokens = resp.json()["data"]

        for label in labels:
            match = next((t for t in all_tokens if t["label"] == label), None)
            if not match:
                print(f"  {label}: not found, skipping")
                continue

            created = match.get("created", "unknown")
            expiry = match.get("expiry") or "never"
            info = f"created {created}, expires {expiry}"

            if args.do_it:
                del_resp = requests.delete(f"{API}/{match['id']}", headers=headers)
                del_resp.raise_for_status()
                print(f"  {label}: revoked (id {match['id']}, {info})")
            else:
                print(f"  {label}: would revoke (id {match['id']}, {info})")
    if not args.do_it:
        print(f"\nRun again with a --do-it flag to revoke the tokens for real.")

if __name__ == "__main__":
    main()
