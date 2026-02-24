# Documentation

- [Linode API Scopes](linode-scopes.md) — How to set the right permissions on your "main" token so it can manage your other tokens.
- [How It Works](how-it-works.md) — What happens when you run `docker compose up`, how to access Vault, data persistence, and picking up config changes.
- [Observability](observability.md) — The optional OTel Collector, Prometheus, Loki, Tempo, and Grafana stack, including architecture and Grafana setup.
- [revoke-tokens.py](revoke-tokens.md) — Utility script for revoking managed tokens to trigger re-creation, useful for testing and generating observability data.
- [Troubleshooting](troubleshooting.md) - Common issues (that I've hit so far at least) and steps on how to resolve them!