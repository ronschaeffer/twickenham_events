# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.7] - 2026-04-08

### Fixed
- Lint cleanup: ruff format on `src/twickenham_events/__main__.py` and
  `src/twickenham_events/web/twickenham_server.py`. The 0.3.6 health-tracker
  commit didn't run `make ci-check` before pushing — same lint slip as the
  flights v0.5.0 commit.

## [0.3.6] - 2026-04-07

### Added
- MQTT-aware healthcheck via `ha_mqtt_publisher` v0.4.0's shared `HealthTracker`.
  The container now exposes `GET /health/mqtt` and the Docker HEALTHCHECK
  probes that endpoint instead of the old `/health`. Returns 503 when the
  publisher is disconnected from the broker or when no successful publish has
  happened within the staleness window.
- New `TwickenhamWebServer.attach_health_router(tracker)` method that strips
  any `/health*` routes inherited from `BaseFileServer` and splices the shared
  router routes in at the front of the inner FastAPI app.
- `cmd_service` now creates a `HealthTracker(max_publish_age_seconds=max(900, interval*1.5))`
  and populates it from the existing `on_connect` callback (with a new
  `on_disconnect` callback) and from `run_cycle` after each successful
  `publish_events()`. The publisher uses raw `paho.mqtt.Client` directly,
  which is why we don't use `HealthTracker.attach()`.

### Changed
- Bumped `ha-mqtt-publisher` to `>=0.4.0`.
- Dockerfile `HEALTHCHECK` switched from `/health` (with a `os.kill(1, 0)`
  fallback) to `/health/mqtt` with explicit 200 status assertion.

### Why
Addresses the failure mode observed on 2026-04-07 where the EMQX broker
crash-looped for hours and `twickenham_events` kept restarting silently
because the only watchdog (`automation.twickenham_events_health_alert`)
depended on `sensor.twickenham_events_status` — which was itself
`unavailable` when the publisher could not reach the broker, so the
trigger could never fire.

## [0.3.0] - 2026-03-31

### Changed
- Version bump to 0.3.0
