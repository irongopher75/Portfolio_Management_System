# Axiom Technical Guide: Local MySQL Architecture

This project now runs on a local MySQL database. There is no cloud-database dependency or Aiven certificate requirement in the current architecture.

## Core explanation

During the viva, you can describe the project like this:

1. The Flask application and the MySQL database run together on the same machine.
2. The application connects directly to a local MySQL server running on the same machine.
3. This keeps the system simpler, easier to demo, and less likely to fail because of network or cloud issues.

## Suggested talking points

| Topic | Explanation |
| :--- | :--- |
| **Architecture** | "The system now uses a local MySQL database, so the app and database run together on the same machine." |
| **Reliability** | "Removing the remote database path reduced failures caused by network latency, unreachable hosts, and certificate issues." |
| **Data Access** | "Flask connects directly to the local MySQL instance using `mysql-connector-python`." |
| **Deployment** | "For production-style hosting, the app runs behind Gunicorn instead of the Flask development server." |
| **Monitoring** | "The app includes a `/healthz` route to verify that the service and database are both available." |

## Demo setup

1. Ensure local MySQL is running.
2. Initialize the local database:
   ```bash
   python3 db_init.py
   ```
3. Start the application:
   ```bash
   python3 app.py
   ```
4. Open the app in the browser:
   ```text
   http://127.0.0.1:5001
   ```

## Notes for evaluation

- The database is local, so changes are stored in the local MySQL instance on the same machine.
- There is no dependency on remote database services, tunnels, or certificate files anymore.
- This architecture is intentionally simpler and better suited for a stable local demonstration.
