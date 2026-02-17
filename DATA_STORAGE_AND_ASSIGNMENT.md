# How Data Is Stored and Assigned in the Website

This document describes where data comes from, how it’s loaded, and how it’s passed into the app and frontend.

---

## 1. Overview

| Data | Stored in | Loaded when | Assigned to / Used as |
|------|-----------|-------------|------------------------|
| **Aircraft + performance profiles** | CSV file | App startup | `AIRCRAFT_DATA` (global list) |
| **Airports** | JSON file (or fallback list) | On each request | Returned by `_load_airports_data()` |
| **User listings** | SQLite DB | On each request | Queried in route, merged with aircraft data |
| **Users / sessions** | SQLite DB | On login/signup and auth checks | `get_current_user_info()` etc. |
| **Per-request scoring** | In-memory for request | Per request | `SCORING_DATASET` (global, set per request) |

---

## 2. Aircraft data (CSV → in-memory)

**Where it’s stored**

- File: **`Aircraft Data - Aircraft Data (1).csv`** (repo root or `static/data/`).
- At runtime: a **single in-memory list** of aircraft dicts.

**How it’s loaded and assigned**

1. On **app startup**, `load_aircraft_data()` runs (in `app.py`).
2. It finds the CSV (paths relative to app root), reads it with `pd.read_csv()`, and builds a list of aircraft dicts (one per row), each with a `performance_profile` dict.
3. That list is assigned to a **global**:

   ```python
   AIRCRAFT_DATA = load_aircraft_data()
   ```

4. Routes and helpers use it by:
   - Reading **`AIRCRAFT_DATA`** directly, or
   - Calling **`get_unified_aircraft_data()`**, which returns `AIRCRAFT_DATA.copy()`.

**Where it’s used**

- **Server-side (templates):** e.g. home page gets `filtered_aircraft` (filtered from `get_unified_aircraft_data()`) and passes it to `render_template('index.html', ...)`.
- **APIs:**  
  - **`/api/aircraft-data`** → `jsonify(get_unified_aircraft_data())`  
  - **`/api/performance-profiles`** → built from the same aircraft list (each aircraft → one profile dict).  
- **User listings:** `/api/user-listings` joins SQLite `user_listings` with `AIRCRAFT_DATA` (by `profile_id`) to attach aircraft/profile fields to each listing.

So: **storage = CSV file; assignment = once at startup into `AIRCRAFT_DATA`; use = that global (or a copy) everywhere.**

---

## 3. Airports (JSON → loaded per request)

**Where it’s stored**

- File: **`static/data/airports.json`** (or `airports.json` next to the app).
- If missing: a small **hardcoded fallback list** in `app.py` (`_AIRPORTS_FALLBACK`).

**How it’s loaded and assigned**

- There is **no global “airports list”** kept in memory.
- On each request that needs airports, the handler calls **`_load_airports_data()`**.
- That function:
  - Tries paths relative to the app root (and Flask `root_path`),
  - Reads the JSON file with `json.load()` if found,
  - Otherwise returns `_AIRPORTS_FALLBACK`.
- The **return value** of `_load_airports_data()` is what’s “assigned” for that request (not stored in a global).

**Where it’s used**

- **`GET /api/airports?q=...`**  
  - Calls `_load_airports_data()`, filters by query, returns JSON.
- **`/api/health`**  
  - Calls `_load_airports_data()` to get the list and reports `len(...)` as the airports count.

So: **storage = JSON file (or fallback); assignment = per request inside the route; no long-lived in-memory airports list.**

---

## 4. User listings (SQLite)

**Where it’s stored**

- **SQLite DB:** `instance/jet_finder.db`.
- Table: **`user_listings`** (and related: `users`, etc.).

**How it’s loaded and assigned**

- **Not** loaded at startup.
- On each request to **`/api/user-listings`**:
  1. Open DB: `sqlite3.connect('instance/jet_finder.db')`.
  2. Run a `SELECT` on `user_listings` (e.g. `WHERE ul.status = 'active'`).
  3. For each row, look up the matching aircraft in **`get_unified_aircraft_data()`** by `profile_id`.
  4. Build a combined dict (listing + aircraft/profile) and append to a list.
  5. Return that list as JSON.

So: **storage = SQLite; assignment = per request in the route (query + merge with aircraft data).**

---

## 5. Users and auth (SQLite)

**Where it’s stored**

- Same DB: **`instance/jet_finder.db`**.
- Tables: **`users`**, and any session-related tables used by `get_current_user_info()`.

**How it’s loaded and assigned**

- On routes that need the current user, code calls **`get_current_user_info()`** (or equivalent).
- That reads from the DB (and/or session/cookie) and returns a user object or None.
- That value is **assigned to a variable** in the route (e.g. `user = get_current_user_info()`) and passed to templates or used in logic.

So: **storage = SQLite (and session); assignment = per request in the route.**

---

## 6. Per-request scoring dataset

**Where it’s stored**

- **In memory only**, for the duration of one request.

**How it’s loaded and assigned**

- In the **home route** (e.g. `/` or `/jet-finder`), after filtering aircraft, the code does:

  ```python
  global SCORING_DATASET
  SCORING_DATASET = filtered_aircraft
  ```

- Other logic in the same request (e.g. scoring, normalization) uses **`SCORING_DATASET`** instead of the full `AIRCRAFT_DATA` so that scoring is based on the current filter set.

So: **storage = none (ephemeral); assignment = once per request into global `SCORING_DATASET`.**

---

## 7. Summary: “assign” vs “store”

- **Store** = where the data lives long-term:  
  CSV file, JSON file, SQLite file.
- **Assign** = how the app gets that data into variables it uses:
  - **Once at startup:** `AIRCRAFT_DATA = load_aircraft_data()` (from CSV).
  - **Per request:** `_load_airports_data()`, DB queries, `get_unified_aircraft_data()`, `SCORING_DATASET = filtered_aircraft`.
- **Use** = passing those variables into **`render_template(...)`** for HTML, or returning them in **`jsonify(...)`** for APIs, or using them inside route logic (e.g. merging listings with aircraft).

If you need to **change** what data the site uses (e.g. different CSV, different columns, or a new API), you’d:
- **Change storage:** replace or edit the CSV/JSON or DB.
- **Change assignment:** adjust the loader (`load_aircraft_data`, `_load_airports_data`) or the route that queries the DB and assigns variables.
