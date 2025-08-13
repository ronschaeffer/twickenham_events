"""Generic MQTT command processor for Twickenham Events service.

Portable design suitable for promotion into a shared mqtt library later.
Features:
 - Accepts JSON or plain string command payloads
 - Assigns UUID id when missing
 - Publishes immediate ACK (non-retained by default)
 - Executes command on background thread with duration tracking
 - Publishes result payload (non-retained by default)
 - Duplicate guard (LRU of recent IDs)
 - Single-flight (busy) protection

Expected executor signature: executor(context) -> (outcome, details, extra_dict)
Outcome suggestions: success | validation_failed | transient_error | fatal_error | busy | duplicate | unknown_command
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import json
import logging
import threading
import time
from typing import Any, Callable
import uuid

logger = logging.getLogger(__name__)

Executor = Callable[[dict[str, Any]], tuple[str, str, dict[str, Any]]]


@dataclass
class CommandProcessor:
    client: Any  # paho mqtt client like object with publish()
    ack_topic: str
    result_topic: str
    max_history: int = 128
    retain_ack: bool = False
    retain_result: bool = False
    qos: int = 1
    executors: dict[str, Executor] = field(default_factory=dict)
    _registry_meta: dict[str, dict[str, Any]] = field(default_factory=dict)
    _last_success_ts: dict[str, float] = field(default_factory=dict)
    _auto_registry_topic: str | None = None
    _recent_ids: deque[str] = field(default_factory=deque, repr=False)
    _recent_set: set[str] = field(default_factory=set, repr=False)
    _seq: int = 0
    _active_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def register(
        self,
        name: str,
        executor: Executor,
        description: str | None = None,
        args_schema: dict | None = None,
        outcome_codes: list[str] | None = None,
        qos_recommended: int | None = None,
        cooldown_seconds: int | None = None,
        requires_ai: bool | None = None,
    ) -> None:
        """Register a command executor with optional discovery metadata.

        Metadata is used for building a command registry payload that can be
        published to a retained discovery topic for dynamic UI generation.
        """
        self.executors[name] = executor
        meta = {
            "name": name,
            "description": description or "",
            "args_schema": args_schema or {},
            "outcome_codes": outcome_codes
            or [
                "success",
                "validation_failed",
                "fatal_error",
                "busy",
            ],
            "qos_recommended": qos_recommended
            if qos_recommended is not None
            else self.qos,
        }
        if cooldown_seconds is not None:
            meta["cooldown_seconds"] = cooldown_seconds
        if requires_ai is not None:
            meta["requires_ai"] = requires_ai
        self._registry_meta[name] = meta
        # Auto republish registry if enabled
        if self._auto_registry_topic:
            try:  # pragma: no cover - network safety
                self.publish_registry(self._auto_registry_topic)
            except Exception:  # pragma: no cover
                logger.debug("auto registry publish failed", exc_info=True)

    def enable_auto_registry_publish(self, topic: str) -> None:
        """Enable automatic registry publication on each new registration."""
        self._auto_registry_topic = topic

    # Public API -------------------------------------------------
    def handle_raw(self, payload: bytes | str) -> None:
        if isinstance(payload, bytes):
            text = payload.decode("utf-8", errors="ignore")
        else:
            # Coerce any other object to string defensively
            text = str(payload)
        stripped = text.strip()
        if not stripped:
            logger.warning("empty command payload ignored")
            return
        if stripped.startswith("{"):
            try:
                data = json.loads(stripped) or {}
            except Exception:
                data = {"command": stripped}
        else:
            data = {"command": stripped}
        self._process(data)

    # Internal ---------------------------------------------------
    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    def _publish(self, topic: str, payload: dict[str, Any], retain: bool) -> None:
        try:
            self.client.publish(topic, json.dumps(payload), qos=self.qos, retain=retain)
        except Exception as e:  # pragma: no cover
            logger.error("command publish failed topic=%s error=%s", topic, e)

    def _process(self, data: dict[str, Any]) -> None:
        cmd = (data.get("command") or "").strip().lower()
        if not cmd:
            logger.warning("command with no name ignored")
            return
        cmd_id = (data.get("id") or "").strip() or str(uuid.uuid4())
        if cmd_id in self._recent_set:
            logger.info("duplicate command ignored id=%s command=%s", cmd_id, cmd)
            return
        self._recent_ids.append(cmd_id)
        self._recent_set.add(cmd_id)
        if len(self._recent_ids) > self.max_history:
            old = self._recent_ids.popleft()
            self._recent_set.discard(old)
        seq = self._next_seq()
        received_ts = self._iso_now()
        ack = {
            "id": cmd_id,
            "command": cmd,
            "received_ts": received_ts,
            "status": "received",
            "seq": seq,
        }
        self._publish(self.ack_topic, ack, retain=self.retain_ack)
        executor = self.executors.get(cmd)
        if not executor:
            result = {
                "id": cmd_id,
                "command": cmd,
                "completed_ts": self._iso_now(),
                "outcome": "unknown_command",
                "details": "No executor registered",
                "duration_ms": 0,
                "seq": self._next_seq(),
            }
            self._publish(self.result_topic, result, retain=self.retain_result)
            return
        # Cooldown enforcement (only for commands with cooldown metadata and previous success)
        meta = self._registry_meta.get(cmd, {})
        cd = meta.get("cooldown_seconds")
        now = time.time()
        if isinstance(cd, int) and cd > 0 and cmd in self._last_success_ts:
            elapsed = now - self._last_success_ts[cmd]
            if elapsed < cd:
                remaining = int(cd - elapsed)
                result = {
                    "id": cmd_id,
                    "command": cmd,
                    "completed_ts": self._iso_now(),
                    "outcome": "cooldown",
                    "details": f"cooldown_active retry_after_s={remaining}",
                    "retry_after_s": remaining,
                    "duration_ms": 0,
                    "seq": self._next_seq(),
                }
                self._publish(self.result_topic, result, retain=self.retain_result)
                return
        threading.Thread(
            target=self._run_executor,
            args=(cmd_id, cmd, executor, data, received_ts),
            daemon=True,
        ).start()

    def _run_executor(
        self,
        cmd_id: str,
        cmd: str,
        executor: Executor,
        data: dict[str, Any],
        received_ts: str,
    ) -> None:
        start = time.time()
        if not self._active_lock.acquire(blocking=False):
            result = {
                "id": cmd_id,
                "command": cmd,
                "completed_ts": self._iso_now(),
                "outcome": "busy",
                "details": "Another command is executing",
                "duration_ms": 0,
                "seq": self._next_seq(),
            }
            self._publish(self.result_topic, result, retain=self.retain_result)
            return
        try:
            ctx = {
                "id": cmd_id,
                "command": cmd,
                "requested_ts": data.get("requested_ts"),
                "args": data.get("args") or {},
                "raw": data,
                "received_ts": received_ts,
            }
            outcome, details, extra = executor(ctx)
        except Exception as e:  # pragma: no cover
            logger.exception("executor failure id=%s command=%s", cmd_id, cmd)
            outcome = "fatal_error"
            details = str(e)
            extra = {}
        finally:
            if self._active_lock.locked():
                self._active_lock.release()
        duration_ms = int((time.time() - start) * 1000)
        result = {
            "id": cmd_id,
            "command": cmd,
            "completed_ts": self._iso_now(),
            "outcome": outcome,
            "details": details,
            "duration_ms": duration_ms,
            "seq": self._next_seq(),
        }
        if extra:
            result.update(extra)
        self._publish(self.result_topic, result, retain=self.retain_result)
        # Track last success (for analytics + cooldown)
        if outcome == "success":
            self._last_success_ts[cmd] = start  # start time close enough

    @staticmethod
    def _iso_now() -> str:
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat()

    # Registry / discovery --------------------------------------
    def build_registry_payload(self) -> dict[str, Any]:
        """Build the command registry payload describing available commands."""
        commands = []
        for name, meta in self._registry_meta.items():
            entry = dict(meta)
            if name in self._last_success_ts:
                entry["last_success_ts"] = int(self._last_success_ts[name])
            commands.append(entry)
        return {
            "service": "twickenham_events",
            "registry_version": 1,
            "generated_ts": self._iso_now(),
            "commands": commands,
        }

    def publish_registry(self, topic: str, retain: bool = True) -> None:
        payload = self.build_registry_payload()
        self._publish(topic, payload, retain=retain)


__all__ = ["CommandProcessor"]
