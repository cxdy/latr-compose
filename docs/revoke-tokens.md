# `revoke-tokens.py`

Quick and dirty utility script to revoke tokens for testing purposes. Rotating/revoking tokens quickly is a good way to generate observability data in a short period of time.

This script reads your `.env` for your `LINODE_TOKEN`(s) and your `latr-configs/*.yaml` files for tokens associated with each `LINODE_TOKEN` from `.env`, then revokes those tokens.

Obviously be careful with this.. Don't run this with production credentials (unless you know what you're doing).

## Usage
```bash
# Install dependencies
➜ pip3 install requests pyyaml

# Dry-run
➜ python3 revoke-tokens.py

--- primary.yaml (token: ...REDACTED)
  token-one: would revoke (id REDACTED, created 2026-02-24T07:29:12, expires 2026-03-26T07:29:12)

--- secondary.yaml (token: ...REDACTED)
  token-four: would revoke (id REDACTED, created 2026-02-24T07:29:12, expires 2026-03-26T07:29:12)

Run again with a --do-it flag to revoke the tokens for real.

# Actually revoke the tokens
➜ python3 revoke-tokens.py --do-it

--- primary.yaml (token: ...REDACTED)
  token-one: revoked (id REDACTED, created 2026-02-24T07:29:12, expires 2026-03-26T07:29:12)

--- secondary.yaml (token: ...REDACTED)
  token-four: revoked (id REDACTED, created 2026-02-24T07:29:12, expires 2026-03-26T07:29:12)
```

## Speed-run

If you want to simulate lots of rotations quickly, I recommend the following settings in your `latr-configs/$config.yaml`:
```yaml
daemon:
  check_interval: "1m"
rotation:
  threshold_percent: 99
tokens:
  - label: "test-token"
    validity: "30d"
```
Then run a loop!
```bash
➜ while true; do python3 revoke-tokens.py --do-it; sleep 75; done
```

May need to tweak timing a little :shrug:
