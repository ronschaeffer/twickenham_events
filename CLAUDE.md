# CLAUDE.md — twickenham_events

## What this is

Containerised Python app that scrapes Twickenham Stadium event listings from the
Richmond Council website, publishes to MQTT (Home Assistant), and generates ICS files.

## Type: App (not a library)

- Public repo: `ronschaeffer/twickenham_events`
- Runs as a Docker container on Unraid (`twickevents`)
- Docker image: `ghcr.io/ronschaeffer/twickenham_events`
- Entry point: `src/twickenham_events/__main__.py` via `twick-events` script

## Dependencies

- `ha-mqtt-publisher` (ronschaeffer/ha_mqtt_publisher)
- `icalendar` (for ICS calendar generation)

## Toolchain

Python 3.11+, Poetry, ruff, pytest, pre-commit

## Key commands

```bash
poetry install --with dev   # install deps
make fix                    # lint + format
make test                   # run tests
make ci-check               # lint + test
make install-hooks          # install pre-commit hooks
```

## Structure

```
src/twickenham_events/   main package
tests/                   pytest tests
config/                  YAML config files
docs/                    documentation
ha_card/                 Home Assistant Lovelace card YAML
unraid/                  Unraid Docker template XML
.dev-scripts/            dev helper scripts
```

## CI

`ci.yml`: lint + test on Python 3.11 and 3.12.
`docker-publish.yml`: build and push to GHCR on `v*` tag.
`code-quality.yml`: pre-commit and ruff analysis.
`version-bump.yml`: automated version bumps.

## Docker / Unraid

See `docs/DOCKER_DEPLOYMENT_EXAMPLES.md` and `docs/UNRAID_TEMPLATE_EXAMPLE.md`.
The Unraid template `my-twickevents.xml` is pinned to `:0.3.7`.

## MQTT-aware healthcheck (since v0.3.6)

`cmd_service` creates a `HealthTracker(max_publish_age_seconds=max(900, interval*1.5))`
and populates it manually because the long-lived MQTT loop uses raw
`paho.mqtt.Client` directly (not the wrapped `MQTTPublisher`, which is only
used per-cycle inside `MQTTClient.publish_events`). The hooks are:

1. The existing `on_connect` callback stamps `tracker.state.connected=True` and
   `last_connect_at` on rc==0.
2. A new `on_disconnect` callback flips `connected=False` and stamps
   `last_disconnect_at`.
3. `run_cycle` wraps the `mqtt_pub.publish_events()` call in try/except and
   updates `publish_success_count` / `publish_failure_count` /
   `last_publish_success_at` / `last_failure_reason` accordingly.

`TwickenhamWebServer.attach_health_router(tracker)` strips the inherited
`/health*` routes from `BaseFileServer` and splices the shared
`make_fastapi_router` routes in at the front of the inner FastAPI app.

The Dockerfile HEALTHCHECK probes `/health/mqtt` (200=healthy, 503=stale).
**Do not remove this** — it's the mechanism that detects real broker outages.
Do not use `HealthTracker.attach()` here — it would patch the per-cycle
publisher that gets garbage collected when the `with` block exits.

## Testing

Integration harness: `/root/dev/python/mqtt_test_harness` (`mqtt_test_harness` package).
Subscribe with `MQTTHarness`, publish via `MQTTPublisher`, assert with `collect()`.

```python
from mqtt_test_harness import MQTTHarness

async with MQTTHarness() as h:
    # publish via ha_mqtt_publisher, then:
    msgs = await h.collect("topic", count=1, timeout=5.0)
```

## Coding conventions

- Line length: 88, quote style: double
- ruff isort with `force-sort-within-sections`
- No f-strings in logging calls (G004 enforced)
- Follow HA coding standards where applicable
