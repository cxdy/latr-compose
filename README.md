# latr + Vault Docker Compose Stack

This is a Docker Compose **development/testing** environment for [latr](https://github.com/wbh1/latr)

By default, it configures `latr` in daemon mode with a Vault backend to store your Linode API tokens.

You can optionally run an [Observability stack](docs/observability.md) alongside it to view logs, traces and metrics via Grafana.

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

Config files for the optional observability stack. See [docs/observability.md](docs/observability.md).

| File | Description |
|------|-------------|
| `otel-collector.yaml` | OpenTelemetry Collector pipeline — receives OTLP from latr, tails Docker container logs, and fans out to Prometheus, Loki, and Tempo |
| `prometheus.yaml` | Prometheus scrape config (scrapes the OTel Collector metrics endpoint) |
| `loki.yaml` | Loki storage and schema config |
| `tempo.yaml` | Tempo trace storage config |
| `grafana/provisioning/` | Datasource provisioning (Prometheus, Loki, Tempo with stable UIDs) |
| `grafana/dashboards/latr.json` | Seed dashboard JSON — imported once by grafana-init on first run |

## Quick Start

> **Note**: Your Linode API tokens need the right scopes. See [docs/linode-scopes.md](docs/linode-scopes.md) for details.

```bash
# 1. Create required directories
➜ mkdir -p vault-creds

# 2. Create your config(s) in latr-configs/ (OPTIONAL)
#    Each file gets its own Vault AppRole and Linode token.
#    Use latr-configs/primary.yaml as a starting point.
➜ cp latr-configs/primary.yaml latr-configs/myaccount.yaml
# Edit myaccount.yaml with your token definitions

# 3. Create .env with a LINODE_TOKEN_<NAME> for each config
#    <NAME> = filename without .yaml, UPPERCASED, hyphens → underscores
➜ cp .env.example .env
# Edit .env with your actual Linode API tokens

# 4. Bring everything up
➜ docker compose up -d

# 5. (Optional) Include the observability stack
➜ docker compose --profile observability up -d

# 6. Check that vault-init completed successfully
➜ docker compose logs vault-init

# 7. Verify latr is running (one process per config)
➜ docker compose logs -f latr
```
For more on what happens under the hood, see [docs/how-it-works.md](docs/how-it-works.md).

## Multiple Linode Accounts

Each config file in `latr-configs/` represents a separate Linode account. The naming convention ties everything together:

| Config file | Token env var in `.env` | Vault AppRole | Vault Mount | Vault Path |
|---|---|---|---|---|
| `latr-configs/primary.yaml` | `LINODE_TOKEN_PRIMARY` | `latr-primary` | `infra` | `latr/primary/` |
| `latr-configs/secondary.yaml` | `LINODE_TOKEN_SECONDARY` | `latr-secondary` | `infra` | `latr/secondary/` |

To add a new account:
1. Copy an existing config: `cp latr-configs/primary.yaml latr-configs/newaccount.yaml`
2. Edit the new config with your token definitions
3. Add `LINODE_TOKEN_NEWACCOUNT=your-token` to `.env`
4. `docker compose up -d` (vault-init will create the new AppRole and render the config)

To remove an account: delete the config file, remove the token from `.env`, and redeploy.

## Security Notes

- `.env` contains your Linode API tokens and `vault-creds/` contains your unseal keys, root token, and AppRole secrets. Both are in `.gitignore`.
- TLS is disabled on Vault. If you're crazy enough to run this in production, enable TLS.
- The init uses a single unseal key (key-shares=1, key-threshold=1) for simplicity. For production, increase these values.
- Do not run this as-is in production. You're an idiot if you trust me.

## Further Reading

- [Linode API Scopes](docs/linode-scopes.md) — token permission requirements
- [How It Works](docs/how-it-works.md) — startup sequence, Vault access, persistence, config changes
- [Observability](docs/observability.md) — OTel Collector, Prometheus, Loki, Tempo, Grafana
- [revoke-tokens.py](docs/revoke-tokens.md) — utility script for testing token rotation
- [Troubleshooting](docs/troubleshooting.md) - Common issues and how to resolve them
