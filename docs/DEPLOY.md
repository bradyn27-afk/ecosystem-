# Deploy Driveline HQ on Render

This creates a paid Python web service and 1 GB persistent disk. Confirm the prices Render displays before creating it. Nothing in this repository provisions hosting by itself.

1. Push this application, including `render.yaml`, `server.py`, and `requirements.txt`, to your GitHub repository.
2. In your Render account, create a **Blueprint** and connect that GitHub repository. Select the branch containing this application. Render reads `render.yaml`.
3. Set `DRIVELINE_PASSWORD` securely in Render when prompted. Use a unique password of at least 20 characters. The app refuses to start in public mode without it. The username defaults to `owner`. Do not put the password in Git, chat, or a URL.
4. Review the service and persistent-disk cost, then create the service. Render terminates HTTPS and gives the service a public URL. Open that URL and use the browser sign-in prompt.
5. Verify a private browser window gets a login prompt; `/api/workspace` must return 401 without credentials. `/healthz` is intentionally public and exposes only a basic process check. After signing in, confirm the sidebar says **Saved to database**.
6. Add a temporary client, refresh, and verify it remains. Redeploy and confirm it remains again. Delete the temporary record afterward. This validates the actual persistent disk; local tests do not prove hosted durability.

## Existing records

A new hosted database starts empty. Export the current local workspace using **Export backup**, then import it in the hosted workspace after login. No automatic transfer from this cloud environment occurs. Export the destination workspace first if it already has records. The import replaces its full contents after confirmation.

## Access and backups

The first release has one shared owner login using HTTP Basic authentication over HTTPS. It has no separate staff accounts, password reset, roles, or audit trail. Use the HTTPS Render URL. Close private browser windows to end their saved browser authentication. Change the password in Render to rotate access.

The SQLite database must remain on the configured paid disk at `/var/data/driveline/workspace.sqlite3`. Do not switch this app to a free/ephemeral filesystem for business records. Keep exported backups outside the host and test restoring them. A disk is persistence, not an independent backup.

Auto deploy is disabled: review changes before manually deploying. Email integration is not required. This deployment does not change the existing Driveline marketing website or its DNS.
