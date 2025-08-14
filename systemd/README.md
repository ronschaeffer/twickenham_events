Twickenham Events systemd unit

Install (user service):

1) Copy unit into user systemd dir and reload:

   mkdir -p ~/.config/systemd/user
   cp systemd/twickenham-events.service ~/.config/systemd/user/
   systemctl --user daemon-reload

2) Enable and start:

   systemctl --user enable --now twickenham-events.service

3) Logs:

   journalctl --user -u twickenham-events.service -f

If you prefer a system-wide service, change `User=` to an explicit user and place
in `/etc/systemd/system/` (requires sudo), then `systemctl daemon-reload` and
`systemctl enable --now twickenham-events`.
