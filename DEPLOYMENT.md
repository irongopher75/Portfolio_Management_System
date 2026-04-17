# Axiom Terminal | Collaborative Submission Protocol

This document outlines the procedure for shared evaluation of the Axiom Terminal. Per faculty requirements, the system operates in **Offline Mode** with no external API dependencies and uses **SQLite** as the unified data source.

## 🚀 Shared Evaluation Model

To ensure "reflect to another user" functionality without cloud services, the database state is synchronized directly via the repository.

### Step 1: Clone and Synchronize
1.  **Clone the Repo**: Faculty or peers should clone the repository.
2.  **Existing Data**: The `portfolio.db` file is included in the repo. You will see all current holdings and users immediately upon startup.

### Step 2: Making Changes (Sync Protocol)
Since there is no cloud database, you must manually commit the data state:
1.  **Interact**: Log in as `admin` or a `user` and perform trades or approvals.
2.  **Save State**:
    ```bash
    git add portfolio.db
    git commit -m "Updated portfolio state (Handshake approved)"
    git push origin main
    ```
3.  **Reflect**: The other user simply runs `git pull` to see your latest database changes.

## 🔐 Local Environment Setup
1. **Runtime**: Python 3.12+
2. **Installation**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Run Node**:
   ```bash
   python3 app.py
   ```

## 🛠️ Data Infrastructure
*   **Static Assets**: Market prices are "frozen" at their last official fetch to comply with the "No-API" requirement.
*   **SQL Console**: Admins can still use the built-in Console to manually adjust asset prices or schema directly in the browser.
