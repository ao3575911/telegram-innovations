# Debian Linux service

Use one bot process and one database. Python 3.12 or newer is required; Debian
13 provides a suitable Python. Debian 12's default Python 3.11 is too old: install
an independently maintained Python 3.12+ or let `uv` provision its managed Python.
The service requires outbound HTTPS to `api.telegram.org`, DNS, and a correct
system clock. It requires no inbound ports, Docker, Redis, or bot administrator
permissions. Keep Telegram privacy mode enabled in @BotFather.

Install `uv` from its official distribution and verify the published installer or
package before running it. The project lockfile pins application dependencies;
CI uses uv 0.13.4. On the server:

```bash
sudo useradd --system --home-dir /var/lib/rallypoint --shell /usr/sbin/nologin rallypoint
sudo install -d -m 0755 /opt/rallypoint
tar --exclude='./.env' --exclude='./.venv' --exclude='./data' -C telegram-innovation -cf - . | sudo tar -C /opt/rallypoint -xf -
sudo chown -R root:root /opt/rallypoint
sudo chmod -R a+rX /opt/rallypoint
cd /opt/rallypoint
sudo uv sync --frozen --no-dev --python /usr/bin/python3
sudo install -o root -g rallypoint -m 0640 .env.example /etc/rallypoint.env
sudoedit /etc/rallypoint.env
```

`sudo uv` assumes uv is available on the administrator's PATH. Use its verified
absolute path if necessary. Provision Python before building the venv. In
particular, a venv pointing into `/root/.local/share/uv/python` cannot be used by
this hardened service. Use the system Python 3.12+ or install managed Python in a
shared read-only location before `uv sync`.

In `/etc/rallypoint.env`, set `BOT_TOKEN` and `IDENTITY_SECRET`, and set
`DATABASE_PATH=/var/lib/rallypoint/rallypoint.sqlite3`. Leave `LOG_FILE` empty to
use journald, or set it to `/var/lib/rallypoint/rallypoint.log`. Set `ADMIN_IDS`
only for trusted operators. Environment files must contain literal `KEY=value`
assignments; do not put shell command substitutions in them. Generate the identity
key separately with `python3 -c 'import secrets; print(secrets.token_hex(32))'`.

```bash
sudo install -o root -g root -m 0644 deploy/rallypoint.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now rallypoint
sudo systemctl status rallypoint --no-pager
sudo journalctl -u rallypoint --since '10 minutes ago'
```

For an offline configuration check before startup, use an administrator shell
that loads the trusted environment file and runs
`/opt/rallypoint/.venv/bin/python -m telegram_innovation check-config`.
Never paste the file or token into logs or support tickets. The `health` CLI checks
the database; operator `/diagnostics` checks a running bot from a private chat.
Database health alone does not prove successful Telegram delivery.

## Log retention

With `LOG_FILE` configured, the application keeps the current 1 MiB file and five
rotated backups. These limits are per file, not time based. Console logs are JSON
and journald owns their retention. Apply an explicit host policy, for example a
drop-in `/etc/systemd/journald.conf.d/retention.conf` containing:

```ini
[Journal]
SystemMaxUse=100M
MaxRetentionSec=7day
```

This changes journald retention for the host, so review existing operational needs
before applying it and restarting `systemd-journald`.

## Backup, upgrade, and recovery

Stop the service before copying the database, or use SQLite's online backup API.
Copying only the main file while WAL writes are active can lose committed data.
Keep the identity secret with encrypted, access-controlled backups and expire
backups according to your retention policy. Changing or losing the secret breaks
matching of existing participants and owners and prevents complete `/forget`.

Before an upgrade, stop the service, back up the database and matching environment
file, replace application files, run `uv sync --frozen --no-dev`, run the offline
configuration check, then restart. Migrations apply at database open. Review schema
changes before upgrading; rollback may require restoring the matching backup.
Verify `/help`, a test group card, and diagnostics after every deployment.

Do not run polling workers in parallel or configure a webhook for the same bot.
Restore a deleted card's display only through supported bot commands; Telegram
message delivery cannot be made atomic with SQLite commits. An ambiguous network
failure can produce a duplicate initial card. Keep the private database and key
out of source control and support bundles.
