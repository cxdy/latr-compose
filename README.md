# latr + Vault Docker Compose Stack

This is a Docker Compose **development/testing** environment for [latr](https://github.com/wbh1/latr)

By default, it configures `latr` in daemon mode with a Vault backend to store your Linode API tokens. 

You can optionally run an Observability stack alongside it to view logs, traces and metrics via Grafana.

## Table of Contents

- [Files](#files)
- [Note about Linode API Scopes](#note-about-linode-api-scopes)
- [Multiple Linode Accounts](#multiple-linode-accounts)
- [Quick Start](#quick-start)
- [What Happens on `docker compose up`](#what-happens-on-docker-compose-up)
- [Vault Access](#vault-access)
- [Observability (Optional)](#observability-optional)
- [Persistence](#persistence)
- [Picking up changes to `latr-configs/*`](#picking-up-changes-to-latr-configs)
- [`revoke-tokens.py`](#revoke-tokenspy)
- [Security Notes](#security-notes)

## Files

| File | Description |
|------|-------------|
| `docker-compose.yaml` | Core stack (Vault, vault-init, latr) plus the optional observability profile (OTel Collector, Prometheus, Loki, Tempo, Grafana, grafana-init) |
| `Dockerfile.latr` | Lightweight Alpine wrapper around the official latr image (adds a shell so env vars can be sourced at runtime) |
| `vault-config.hcl` | Vault server configuration with file storage backend |
| `latr-configs/` | latr config templates — one YAML file per Linode account (see [Multiple Accounts](#multiple-linode-accounts)) |
| `.env` | Linode API tokens, one `LINODE_TOKEN_<NAME>=...` per config (git-ignored) |
| `.env.example` | Reference showing the token naming convention |

### `vault-creds/`

Created on first run. **Keep this directory in `.gitignore`.**

| File | Description |
|------|-------------|
| `vault-init.json` | Unseal keys and root token |
| `<name>.env` | Per-config AppRole credentials (for reference) |
| `<name>.linode.env` | Per-config `LINODE_TOKEN` sourced by latr at startup |

### `observability/`

Config files for the optional observability stack.

| File | Description |
|------|-------------|
| `otel-collector.yaml` | OpenTelemetry Collector pipeline — receives OTLP from latr, tails Docker container logs, and fans out to Prometheus, Loki, and Tempo |
| `prometheus.yaml` | Prometheus scrape config (scrapes the OTel Collector metrics endpoint) |
| `loki.yaml` | Loki storage and schema config |
| `tempo.yaml` | Tempo trace storage config |
| `grafana/provisioning/` | Datasource provisioning (Prometheus, Loki, Tempo with stable UIDs) |
| `grafana/dashboards/latr.json` | Seed dashboard JSON — imported once by grafana-init on first run |

## Note about Linode API Scopes

In the [Quick Start](#quick-start) section, you'll need to set the Linode API token that will be used to manage your other tokens on Linode.

To make it a little less confusing, I'll refer to the token used to manage other tokens as your **"main token"**, and any other tokens will be **"managed token(s)"**

Your **main token** needs to have higher permissions than the **managed token(s)** you're trying to manage with `latr`. 

For example, if you want a **managed token** that has the scope `monitor:read_only`, your **main token** needs `account:read_write,monitor:read_write`. 

All **main tokens** need `account:read_write` at a minimum, and any other permissions you'll need to assign to your **managed token(s)**.

Take a look at the Linode API documentation for [a full list of OAuth scopes](https://techdocs.akamai.com/linode-api/reference/get-started#oauth-reference).

If you see a log like this in your `latr` logs, you'll know that you have incorrect permissions on your **main token**:
```json
{"time":"2026-02-24T02:55:53.532721342Z","level":"ERROR","source":{"function":"github.com/wbh1/latr/internal/scheduler.(*Scheduler).executeCycle","file":"/home/runner/work/latr/latr/internal/scheduler/scheduler.go","line":124},"msg":"Failed to process token","token_label":"token-one","error":"failed to create token token-one in Linode: failed to create token: [400] [scopes] You may not create a token with scopes greater than those of the token you are using for the request (maximum scopes: account:read_write)"}
```

## Multiple Linode Accounts

Each config file in `latr-configs/` represents a separate Linode account. The naming convention ties everything together:

| Config file | Token env var in `.env` | Vault AppRole |
|---|---|---|
| `latr-configs/primary.yaml` | `LINODE_TOKEN_PRIMARY` | `latr-primary` |
| `latr-configs/secondary.yaml` | `LINODE_TOKEN_SECONDARY` | `latr-secondary` |

To add a new account:
1. Copy an existing config: `cp latr-configs/primary.yaml latr-configs/newaccount.yaml`
2. Edit the new config with your token definitions
3. Add `LINODE_TOKEN_NEWACCOUNT=your-token` to `.env`
4. `docker compose up -d` (vault-init will create the new AppRole and render the config)

To remove an account: delete the config file, remove the token from `.env`, and redeploy.

## Quick Start

```bash
# 1. Create required directories
mkdir -p vault-creds

# 2. Create your config(s) in latr-configs/ (OPTIONAL)
#    Each file gets its own Vault AppRole and Linode token.
#    Use latr-configs/primary.yaml as a starting point.
cp latr-configs/primary.yaml latr-configs/myaccount.yaml
# Edit myaccount.yaml with your token definitions

# 3. Create .env with a LINODE_TOKEN_<NAME> for each config
#    <NAME> = filename without .yaml, UPPERCASED, hyphens → underscores
cp .env.example .env
# Edit .env with your actual Linode API tokens

# 4. Bring everything up
docker compose up -d

# 5. Check that vault-init completed successfully
docker compose logs vault-init

# 6. Verify latr is running (one process per config)
docker compose logs -f latr
```

## What Happens on `docker compose up`

1. **Vault** starts with file-backed persistent storage in a Docker volume (`vault-data`)
2. **vault-init** waits for Vault to be reachable, then:
   - **First run**: Initializes Vault (1 unseal key, threshold 1) and saves keys to `vault-creds/vault-init.json`
   - **Every run**: Unseals Vault if sealed, then idempotently configures:
     - KV v2 secrets engine at `infra/`
     - A policy granting full CRUD access to `infra/*`
     - AppRole auth method
   - **For each config** in `latr-configs/`:
     - Creates a per-config AppRole (`latr-<name>`)
     - Writes `vault-creds/<name>.env` with AppRole credentials (for reference)
     - Reads `LINODE_TOKEN_<NAME>` from `.env` and writes it to `vault-creds/<name>.linode.env`
     - Renders the config template with AppRole credentials baked in
3. **latr** starts after vault-init completes, launches one process per rendered config — each with its own `LINODE_TOKEN` and a `config` OTEL resource attribute (e.g. `config="primary.yaml"`) — and runs in daemon mode

## Vault Access

- **UI**: http://localhost:8200 (sign in with the root token from `vault-creds/vault-init.json`)
- **CLI**: `export VAULT_ADDR=http://localhost:8200 VAULT_TOKEN=$(cat vault-creds/vault-init.json | jq -r .root_token)`

## Observability (Optional)

A full observability stack is available via Docker Compose profiles. This adds an OpenTelemetry Collector, Prometheus, Loki, Tempo, and Grafana — all pre-wired.

```bash
# Start everything including observability
docker compose --profile observability up -d

# Or start just the core stack (no observability)
docker compose up -d
```

### What's Included

| Service | Port | Purpose |
|---------|------|---------|
| OTel Collector | 4317 (gRPC) | Receives OTLP from latr and tails Docker container logs, fans out to backends |
| Prometheus | 9090 | Metrics storage (scrapes OTel Collector) |
| Loki | 3100 | Log aggregation (receives OTLP logs) |
| Tempo | 3200 | Distributed tracing (receives OTLP traces) |
| Grafana | 3000 | Latr dashboard and datasources |

### Grafana

- **URL**: http://localhost:3000
- **Login**: `admin` / `password`
- Datasources (Prometheus, Loki, Tempo) are pre-provisioned
- A **latr - Token Rotator** dashboard is pre-loaded under the `latr` folder with panels for all metrics, logs, and traces

**NOTE**: The dashboard is only imported _once_, and any changes made in the Grafana UI will not be
reflected in `latr.json` unless you export the JSON model and update the file yourself. 

To reset the Grafana container:
```bash
# Remove the containers
docker compose --profile observability rm -sf grafana grafana-init

# Remove the grafana-data volume
docker volume rm latr-docker_grafana-data

# Rebuild it with a fresh volume 
# datasources and dashboard still included
docker compose --profile observability up -d
```

### Architecture

```
latr ──OTLP──▶ OTel Collector ──▶ Prometheus (metrics)
                     │          ──▶ Loki (logs)
                     │          ──▶ Tempo (traces)
                     │                   │
Docker logs ─filelog─┘        Grafana ◀──┘
```

The `otel_endpoint` in each config is set to `otel-collector:4317`. If the observability stack isn't running, latr will log connection errors but continue to function normally.

## Persistence

Vault data is stored in the `vault-data` Docker volume. Your secrets survive `docker compose down` and `docker compose up`. Observability data is stored in `prometheus-data`, `loki-data`, `tempo-data`, and `grafana-data` volumes. To fully reset:

```bash
docker compose down -v   # -v removes the vault-data and latr-config volumes
rm -rf vault-creds       # remove saved unseal keys and creds
```

## Picking up changes to `latr-configs/*`

The configs need to be rendered by `vault-init`, so after modifying/creating/deleting anything in `latr-configs/*`, you'll need re-run `vault-init` and start `latr` with the updated configs.
```bash
docker compose rm -sf vault-init latr && docker compose up -d
```

## `revoke-tokens.py`

Quick and dirty utility script to revoke tokens for testing purposes. Rotating/revoking tokens quickly is a good way to generate observability data in a short period of time.

This script reads your `.env` for your `LINODE_TOKEN`(s) and your `latr-configs/*.yaml` files for tokens associated with each `LINODE_TOKEN` from `.env`, then revokes those tokens.

Obviously be careful with this.. Don't run this with production credentials (unless you know what you're doing). 

### Usage
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

### Speed-run

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

## Security Notes

- `.env` contains your Linode API tokens and `vault-creds/` contains your unseal keys, root token, and AppRole secrets. Both are in `.gitignore`.
- TLS is disabled on Vault. If you're crazy enough to run this in production, enable TLS.
- The init uses a single unseal key (key-shares=1, key-threshold=1) for simplicity. For production, increase these values.
- Do not run this as-is in production. You're an idiot if you trust me.