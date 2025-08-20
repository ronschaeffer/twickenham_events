Twickenham Events systemd units

This folder contains a systemd unit for running the service via Poetry.

## User service (recommended)

1) Install the unit and reload:

   mkdir -p ~/.config/systemd/user
   cp systemd/twickenham-events.service ~/.config/systemd/user/
   systemctl --user daemon-reload

2) Enable and start:

   systemctl --user enable --now twickenham-events.service

3) Logs:

   journalctl --user -u twickenham-events.service -f

Notes:
- The unit uses `poetry run python -m twickenham_events service` with the project working directory.
- Provide environment variables via `~/.config/environment.d/*.conf` or an exported `.env` loader if needed.

## System service (optional)

If you prefer a system-wide service:

1) Copy the unit to `/etc/systemd/system/` (requires sudo) and edit to set an explicit `User=`:

   sudo cp systemd/twickenham-events.service /etc/systemd/system/
   sudoedit /etc/systemd/system/twickenham-events.service

2) Reload, enable, and start:

   sudo systemctl daemon-reload
   sudo systemctl enable --now twickenham-events.service

3) Logs:

   journalctl -u twickenham-events.service -f

Environment management:
- Consider a drop-in file to provide environment vars: `sudo systemctl edit twickenham-events.service` → add `Environment=` lines or `EnvironmentFile=`.
- Ensure the unit `WorkingDirectory` matches your clone path.
