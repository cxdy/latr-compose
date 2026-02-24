# How It Works

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
