# Driveline Mobile · Business HQ

An operations workspace for Driveline Mobile in Celina, Texas: auto repair, power washing, and car flips.

## Run

```sh
cd /workspace/ecosystem-
python3 server.py
```

Python 3.10+ with its standard library is all that is needed. The server binds to the local machine on port 8000. `--port` selects another port. No package installation or build is required.

Records are stored in SQLite at `/workspace/driveline-data/workspace.sqlite3`, outside the checkout. Set `DRIVELINE_DATA_DIR` or pass `--db /path/to/workspace.sqlite3` to choose another location. Restart with the same database path to retain records. Live processes do not survive environment restarts.

## Workflows

1. Add a client, then create a linked job with its scope, date, labor and parts estimates.
2. Add your own service pricing: per job, per hour, or per square foot. **Create job** fills the rate and scope; quantity multiplies the rate. Review before saving.
3. Open **Planner** for overdue, today, upcoming and unscheduled work, using America/Chicago dates. Advance jobs from Quote needed to Scheduled, In progress and Completed. Advancing does not imply customer approval or record a payment.
4. Print a branded estimate, including scope, itemized subtotal and approval line. Browser print can save it as PDF. Tax is not calculated.
5. Track parts, suppliers, quantities, fitment notes and order status. Supplier requests remain drafts.
6. Enter actual income and expenses in **Money**. Monthly expenses are compared with a shared budget; totals respect the selected business. Quote estimates are not cash receipts.
7. Track car purchase, repair, fees, title/condition notes, sale target and actual sale margin. These records do not automatically post to the cash ledger.

Sample records are labeled and removable. Actual rates, transactions and customer records must be entered by the owner. No market pricing, repair procedures, parts fitment or website details are fetched automatically.

## Storage and backups

The browser loads from the database, keeps a local backup and serializes saves. Stale writes from another window are rejected rather than overwriting newer records. A visible warning appears on save failure; export your work before reloading. Reload to obtain changes from another window. There is no live collaboration.

On a new empty database, valid existing browser records are migrated automatically. When a database already exists, it is authoritative. Export any different browser workspace before migrating. Export/import JSON is available in the sidebar; imports replace the full workspace after confirmation and reject invalid amounts and orphaned links. Exported files contain customer information and must be stored privately. Keep independent backups outside the cloud task; snapshot publication alone is not a business backup policy.

The static `python3 -m http.server` command supports a browser-only fallback, but use `server.py` for database persistence. Server storage is local to this environment, not an Internet-hosted database or cross-device deployment.

## Deployment

Render deployment configuration is included in `render.yaml`; see [the deployment guide](docs/DEPLOY.md). Production runs Gunicorn with HTTPS provided by Render, an owner password, and a persistent disk. Local checks validate the production server and authentication, but actual hosted persistence must still be checked after deployment.

## Current limits

Not yet hosted. The included deployment supports one shared password-protected owner account; per-user accounts and roles are not implemented. There is no bank sync, automated pricing, payment processing, or email integration. The local server binds to loopback and serves only explicitly allowed app files, not the database or source tree. Public mode refuses startup without a password of at least 20 characters. Email is optional draft generation and device email-app handoff; nothing sends automatically.

Business website supplied by the owner: https://drivelinemobileauto.com/. Website content has not been verified here.

## Checks

```sh
python3 -m unittest discover -s tests -v
node --check game.js
```

Browser validation also exercised pricing multiplication, client/job links, overdue planning, job stages, printable totals, independent browser database persistence, rejected stale writes, invalid data, protected files and mobile overflow. Browser validation used a disposable `/tmp` database, separate from the working database.
