# Observability

A full observability stack is available via Docker Compose profiles. This adds an OpenTelemetry Collector, Prometheus, Loki, Tempo, and Grafana — all pre-wired.

```bash
# Start everything including observability
docker compose --profile observability up -d

# Or start just the core stack (no observability)
docker compose up -d
```

## What's Included

| Service | Port | Purpose |
|---------|------|---------|
| OTel Collector | 4317 (gRPC) | Receives OTLP from latr and tails Docker container logs, fans out to backends |
| Prometheus | 9090 | Metrics storage (scrapes OTel Collector) |
| Loki | 3100 | Log aggregation (receives OTLP logs) |
| Tempo | 3200 | Distributed tracing (receives OTLP traces) |
| Grafana | 3000 | Latr dashboard and datasources |

## Grafana

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

## Architecture

```
latr ──OTLP──▶ OTel Collector ──▶ Prometheus (metrics)
                     │          ──▶ Loki (logs)
                     │          ──▶ Tempo (traces)
                     │                   │
Docker logs ─filelog─┘        Grafana ◀──┘
```

The `otel_endpoint` in each config is set to `otel-collector:4317`. If the observability stack isn't running, latr will log connection errors but continue to function normally.
