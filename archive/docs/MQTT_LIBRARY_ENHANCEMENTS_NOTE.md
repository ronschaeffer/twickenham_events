# MQTT Library Enhancement Note

Purpose: Track proposed upstream improvements to `ha-mqtt-publisher` (and/or a unified mqtt library) needed by _Twickenham Events_ and document interim local patterns chosen so we can later replace them with first‑class library features with minimal churn.

---

## 1. Current Gaps Identified

| Capability                                                              | Current Local Implementation                                       | Library Status                                                               | Risk / Pain                                                   | Priority |
| ----------------------------------------------------------------------- | ------------------------------------------------------------------ | ---------------------------------------------------------------------------- | ------------------------------------------------------------- | -------- |
| Button entities (MQTT Discovery)                                        | Hand-built discovery JSON for two command buttons in `cmd_service` | No button helper; only generic Entity base via local project, not in library | Manual duplication; inconsistent naming if many buttons added | High     |
| Command topic subscription lifecycle                                    | Direct paho client in `cmd_service`                                | Publisher focuses on publish only; no subscribe wrapper                      | Duplicate connection logic; no reconnection semantics reused  | High     |
| Service/daemon helper (interval + on-demand trigger)                    | Custom loop with SIGTERM + command topics                          | Not present                                                                  | Re-implementation by each consumer                            | Medium   |
| Status / health metrics standardization                                 | Status payload + debug log; no availability topic yet              | Library has no standardized status reporter                                  | Hard to build dashboards / cross-app consistency              | Medium   |
| Availability (online/offline) management                                | Not implemented (planned)                                          | Not built-in                                                                 | HA may show stale entities after restart                      | Medium   |
| Structured discovery bundle with mixed entity types (sensors + buttons) | Ad hoc inside service connect handler                              | Partial in local deleted `ha_integration.py` (unused)                        | Hard to maintain; multi-place definitions                     | High     |
| Retry/backoff for command listener                                      | Single initial connect, no reconnect loop                          | Not available                                                                | Buttons dead after broker hiccup                              | High     |
| Graceful shutdown hook abstraction                                      | Manual SIGTERM handler                                             | Not available                                                                | Duplicate across services                                     | Low      |
| Typed entity builder API (fluent)                                       | Manual dict assembly                                               | Not available                                                                | Verbose & error prone                                         | Medium   |
| Dynamic discovery update (e.g. feature toggles)                         | Not supported                                                      | Not available                                                                | Requires manual retained message management                   | Low      |

---

## 2. Proposed Library Additions

### 2.1 Button Entity Class

Add `Button(Entity)` specialization mirroring HA requirements:

- Component: `button`
- Attributes: `command_topic` mandatory, optional: `icon`, `entity_category`, `payload_press` (default empty string) if library wants to auto-publish a command upon press simulation.
- Validation: Ensure `command_topic` present.
- Config payload fields: `name`, `unique_id`, `command_topic`, `device`, plus optional common attributes.

### 2.2 Unified Discovery Manager Enhancements

Extend existing discovery manager to accept heterogeneous entity lists (sensors, binary_sensors, buttons) and publish them in one call:

```
publish_device_bundle(publisher, device, entities, device_id, remove_stale=True)
```

- `remove_stale`: optional prune previously published entity configs for this device not in current list (publish empty retained config to delete).
- Add idempotency: Skip publish if computed payload hash unchanged since last publish.

### 2.3 Subscription / Command Layer

Introduce `MQTTServiceClient` (name TBD) wrapping paho for both publish and subscribe:

- Methods:
  - `connect()` / context manager
  - `publish(topic, payload, qos=0, retain=False)` (delegates to existing publisher or composes it)
  - `subscribe(topic, callback, qos=0)`
  - `loop_start()`/`loop_stop()` with internal auto-reconnect & exponential backoff.
- Optional `on_connect`, `on_disconnect` events.
- Reuse configuration validation from publisher.

### 2.4 Command Button Helper

`register_button(name, unique_id, command_topic, callback)` to both:

1. Create & publish discovery config for the button.
2. Subscribe to `command_topic`; on message invocation, call callback.

### 2.5 Service Runner Utility

A generic helper to run periodic tasks with:

```
ServiceRunner(
  interval: int,
  run: Callable[[TriggerContext], None],
  register_commands: Callable[[CommandRegistrar], None] | None,
  graceful_signals: tuple[int,...] = (SIGTERM, SIGINT),
  jitter: int = 30,
  min_interval: int = 60,
)
```

- Maintains `last_run_ts`, `last_trigger`.
- Provides `request_run(trigger="command")` for on-demand invocation.
- Handles overlapping run prevention (mutex + skip or queue policy).

### 2.6 Standard Status Publisher

Encapsulate status metrics publication:

```
StatusPublisher.publish(
  component="twickenham_events",
  state={...},
  extra_metrics={...},
)
```

Automatically adds `sw_version`, `timestamp`, `uptime_seconds`, `last_run_iso`.

### 2.7 Availability Manager

Provide simple API:

```
avail = Availability(publisher, topic="twickenham_events/availability")
avail.online()
...
avail.offline()
```

Automatic offline on context manager exit or SIGTERM.

### 2.8 Typed Entity Factory DSL

Chainable style:

```
EntityFactory(device)
  .sensor("event_count", state_topic="...", state_class="measurement")
  .button("refresh", command_topic="...", icon="mdi:refresh")
  .build()
```

Returns list for bundle publication.

### 2.9 Discovery Cache & Diffing

Store a small JSON of last published configs + hashes keyed by `<component>/<unique_id>`; only republish changed ones.

### 2.10 Error Classification

Differentiate `ai_error_count`, `publish_error_count`, `scrape_error_count` in a standard schema.

---

## 3. Backwards Compatibility Strategy

1. Introduce new classes while keeping existing `MQTTPublisher` stable.
2. Offer adapter: `LegacyPublisherAdapter` implementing combined interface.
3. Deprecation path documented in CHANGELOG with at least one minor version notice.

---

## 4. Local (Current) Implementation & Migration Hooks

| Aspect                  | Current Local Code                       | Migration Hook Needed                                   |
| ----------------------- | ---------------------------------------- | ------------------------------------------------------- |
| Button discovery        | Inline JSON in `cmd_service:on_connect`  | Replace with `Button` + `register_button` calls         |
| Command subscribe       | Raw paho client in `cmd_service`         | Replace with `MQTTServiceClient` subscribe API          |
| Periodic loop           | Custom while True + time diff            | Replace with `ServiceRunner`                            |
| Status payload          | `publish_events(extra_status=...)` merge | Replace with `StatusPublisher.publish()` + core metrics |
| last_run metadata       | Provided via `extra_status`              | Supplied by ServiceRunner automatically                 |
| Shutdown handling       | SIGTERM -> stop_flag                     | Provided by ServiceRunner + Availability.offline        |
| Manual discovery prefix | `config.service_discovery_prefix`        | Should rely on library discovery config key             |

### 4.1 Abstraction Layer Proposal

Create a local thin abstraction now so that only one module changes later:

- `twickenham_events.mqtt_commands` (to be implemented) exposing:
  - `start_service(config)` -> launches loop
  - `stop_service()`
  - `register_buttons([...])` (no-op placeholder now)

### 4.2 Naming & Unique IDs

Adopt stable `unique_id` scheme aligning with future library expectation: `tw_events_<feature>`.

### 4.3 Topic Conventions

- Command Topics: `twickenham_events/cmd/<action>` (already established) – keep.
- Availability Topic (planned): `twickenham_events/availability`.
- Status Topic: `twickenham_events/status` (existing).

---

## 5. Incremental Migration Plan

1. Introduce local abstraction module (interface + adapter to current procedural code).
2. Refactor `cmd_service` to call abstraction instead of raw paho code.
3. Add availability topic (online/offline) locally.
4. Upstream: implement Button + ServiceRunner + StatusPublisher.
5. Replace local abstraction implementation with library import.
6. Remove legacy direct paho usage & inline discovery code.

---

## 6. Data Model / Schemas (Draft)

### Status (Standardized)

```
{
  "status": "active|no_events|error",
  "event_count": int,
  "ai_error_count": int,
  "publish_error_count": int,
  "scrape_error_count": int,
  "ai_enabled": bool,
  "sw_version": "x.y.z",
  "last_updated": ISO8601,
  "last_run_ts": epoch,
  "last_run_iso": ISO8601,
  "last_run_trigger": "startup|interval|command",
  "interval_seconds": int,
  "uptime_seconds": int
}
```

### Button Discovery Payload (Target)

```
{
  "name": "Twickenham Refresh",
  "unique_id": "tw_events_refresh",
  "command_topic": "twickenham_events/cmd/refresh",
  "device": { ... device info ... }
}
```

---

## 7. Edge Cases & Considerations

- Broker disconnect mid-command: ServiceClient should queue reconnection & resubscribe automatically.
- Race conditions when command arrives during active cycle: Decide policy (queue vs skip). Current code spawns new thread; better to debounce (ignore if running, or set a flag to re-run immediately after).
- Button removal: Need stale discovery cleanup (publish empty retained config) if a button is disabled.
- Strict validation: Button config missing `command_topic` should raise early.
- Multi-instance deployment: Ensure `client_id` uniqueness (append hash or host).

---

## 8. Testing Strategy (Future Library)

- Unit tests for Button entity payload generation.
- Integration test spinning ephemeral MQTT broker (e.g., using `pytest-mqtt`) verifying discovery & command handling.
- ServiceRunner timing tests with accelerated interval (monkeypatch time).
- Reconnect simulation (force disconnect) verifying resubscription of command topics.

---

## 9. Performance / Resource Notes

- Idle service mode uses low CPU (sleep loop). Moving to ServiceRunner with `select`/`loop_forever` may reduce wakeups.
- Hash-based diffing prevents redundant retained config publishes.
- Single MQTT connection preferred over separate publisher + subscriber sockets.

---

## 10. Open Questions

1. Should StatusPublisher also manage availability automatically? (likely yes)
2. Provide built-in exponential backoff policy configuration? (min_backoff, max_backoff)
3. Support delayed command execution queue vs immediate spawn threads? (determinism & resource constraints)
4. Offer metrics export (Prometheus) as optional plugin?

---

## 11. Action Items

- [ ] Implement local abstraction module (see section 4.1)
- [ ] Refactor `cmd_service` to abstraction (optional next PR)
- [ ] Add availability topic publish on startup/shutdown
- [ ] Upstream: Draft PR adding Button entity + tests
- [ ] Design ServiceRunner public API
- [ ] Add standardized status schema to README of library

---

## 12. Summary

This note catalogs required enhancements to graduate ad hoc service + button handling logic into a reusable, testable, and consistent library layer. Following the migration plan will isolate change to a single abstraction module in this project, minimizing future refactors when upstream features exist.
