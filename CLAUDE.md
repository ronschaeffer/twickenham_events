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
