# CLAUDE.md — twickenham_events

## What this is

Containerised Python app that scrapes Twickenham Stadium event listings from the
Richmond Council website, publishes to MQTT (Home Assistant), and generates ICS files.

## Type: App (not a library)

- Not published to PyPI
- Runs as a Docker container on Unraid
- Entry point: `src/twickenham_events/__main__.py` via `twick-events` script

## Dependencies

- `ha-mqtt-publisher` (ronschaeffer/ha_mqtt_publisher)
- `ronschaeffer-ics-calendar-utils` (ronschaeffer/ics_calendar_utils)

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
.dev-scripts/            dev helper scripts
```

## CI

`ci.yml`: lint + test on Python 3.11 and 3.12.
Version bumps: `version-bump.yml`.

## Docker / Unraid

See `docs/DOCKER_DEPLOYMENT_EXAMPLES.md` and `docs/UNRAID_TEMPLATE_EXAMPLE.md`.

## Coding conventions

- Line length: 88, quote style: double
- ruff isort with `force-sort-within-sections`
- No f-strings in logging calls (G004 enforced)
- Follow HA coding standards where applicable
