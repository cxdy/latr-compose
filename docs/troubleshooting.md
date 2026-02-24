# Troubleshooting

These are some things I've already run into and how to resolve them. I'm sure I'll hit more things eventually and will add them as they come up!

## 403s from Vault

```json
{
  "time": "2026-02-24T08:12:12.278177712Z",
  "level": "ERROR",
  "source": {
    "function": "github.com/wbh1/latr/internal/scheduler.(*Scheduler).executeCycle",
    "file": "/home/runner/work/latr/latr/internal/scheduler/scheduler.go",
    "line": 124
  },
  "msg": "Failed to process token",
  "token_label": "token-six",
  "error": "failed to read token state: failed to read token state from vault: Error making API request.\n\nURL: GET http://vault:8200/v1/infra/metadata/latr/secondary/token-six\nCode: 403. Errors:\n\n* 2 errors occurred:\n\t* permission denied\n\t* invalid token\n\n",
  "trace_id": "ac95ea33d6972bac8bf459b03e65dc5e",
  "span_id": "bcba37e202fd2c8e"
}
```

This usually means you've reached your `token_ttl`/`token_max_ttl` in your AppRole(s), [which is configured here](https://github.com/cxdy/latr-compose/blob/a2bb24f4862de75077a9109f66830110ff7fda2a/docker-compose.yaml#L152-L153) in `docker-compose.yaml`.

I've already fixed this (4h -> 1y), but if for some reason someone (probably me) runs into it again, might as well write it down. 

After bumping those, you'll just need to re-init & restart `Vault` and `latr`:
```bash
# defaults
➜ docker compose rm -sf vault-init latr && docker compose up -d

# with observability stack
➜ docker compose rm -sf vault-init latr && docker compose --profile observability up -d
```

## Invalid Scopes

```json
{
  "time": "2026-02-24T02:55:53.532721342Z",
  "level": "ERROR",
  "source": {
    "function": "github.com/wbh1/latr/internal/scheduler.(*Scheduler).executeCycle",
    "file": "/home/runner/work/latr/latr/internal/scheduler/scheduler.go",
    "line": 124
  },
  "msg": "Failed to process token",
  "token_label": "token-one",
  "error": "failed to create token token-one in Linode: failed to create token: [400] [scopes] You may not create a token with scopes greater than those of the token you are using for the request (maximum scopes: account:read_write)"
}
```

If you see a message like this, that means your `LINODE_TOKEN` doesn't have enough permissions to generate new tokens with the requested scopes. 

See [Linode API Scopes](linode-scopes.md) for more information. 

## Reset your environment

**WARNING**: This will wipe all of your Vault data, as well as any Observability data (if you had it enabled). This is starting from scratch.

Sometimes you do weird stuff and get yourself into an absolute mess, it happens. 

```bash
# 1. Stop and remove all containers (including the Observability stack)
➜ docker compose --profile observability down -v

# 2. Remove the locally built latr image
➜ docker rmi latr-docker-latr 2>/dev/null

# 3. Remove generated credentials
➜ rm -rf vault-creds && mkdir -p vault-creds

# 4. Reset local repo to upstream main (optional, but recommended)
➜ git fetch origin && git reset --hard origin/main

# 5. Re-build the image + containers
# Base install (Vault, vault-init, latr)
➜ docker compose up -d --build
# Base + Observability (OTel, Prometheus, Loki, Tempo, Grafana)
➜ docker compose --profile observability up -d --build
```
