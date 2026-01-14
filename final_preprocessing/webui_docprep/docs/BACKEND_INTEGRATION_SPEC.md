# Backend Integration Specification

This document outlines the API endpoints and data structures required to connect the React Frontend to the Python/Node Backend.

**Current State:** The frontend uses `MOCK_UNITS` and local state simulation.
**Target State:** The frontend consumes JSON from the following REST/WebSocket endpoints.

---

## 1. Global Context
*   **Base URL:** `/api/v1`
*   **Authentication:** Bearer Token (header: `Authorization: Bearer <token>`)

---

## 2. Endpoints

### 2.1. Dashboard & File System
**GET /api/filesystem/tree**
*   **Purpose:** Populates the "Hierarchical Structure" in Dashboard and "Recursive Directory Explorer" in Statistics.
*   **Query Params:** `depth` (optional, default 2), `path` (optional, for lazy loading).
*   **Response Structure:**
    ```json
    {
      "name": "2025-03-04",
      "path": "root/data/2025-03-04",
      "count": 6025,
      "status": "neutral", // "success" | "warning" | "error"
      "children": [ ...recursive nodes... ]
    }
    ```

**GET /api/system/telemetry**
*   **Purpose:** Feeds the "Live System Telemetry" area chart.
*   **Frequency:** Polled every 2s or pushed via WS.
*   **Response:**
    ```json
    {
      "cpu_load": 45.2,
      "throughput_ups": 850, // Units per second
      "timestamp": "ISO-8601"
    }
    ```

### 2.2. Processing Control
**POST /api/pipeline/start**
*   **Purpose:** Triggers a processing cycle.
*   **Body:**
    ```json
    {
      "mode": "cycle" | "final_merge",
      "cycle_number": 1, // Optional if mode is final_merge
      "protocol_date": "2025-03-20"
    }
    ```

**WEBSOCKET /ws/pipeline/stream**
*   **Purpose:** Bi-directional channel for live logs and node metrics animation in `ProcessingControl.tsx`.
*   **Message Types:**
    *   `LOG`: `{"type": "log", "message": "[INFO] Extracting UNIT_123...", "timestamp": "..."}`
    *   `METRIC`: Updates the counts on the absolute-positioned nodes.
        ```json
        {
          "type": "metric_update",
          "data": {
            "source": 120,
            "proc": 45,
            "dist": 40,
            "out_merge": 10,
            "out_excep": 2
          }
        }
        ```

### 2.3. Unit Explorer
**GET /api/units**
*   **Purpose:** Populates the Unit Explorer table.
*   **Query Params:** `page`, `limit`, `search`, `filter_status`.
*   **Response:**
    ```json
    {
      "total": 6025,
      "items": [
        {
          "id": "UNIT_2025_00938",
          "category": "direct", // Maps to frontend color constants
          "state": "READY_FOR_DOCLING",
          "route": "pdf_text",
          "files_count": 4,
          "size": "2.4MB",
          "timestamp": "14:22:10"
        }
      ]
    }
    ```

**GET /api/units/:id/details**
*   **Purpose:** Populates the slide-out Inspector panel.
*   **Response:**
    ```json
    {
      "id": "UNIT_...",
      "metadata": { "hash": "...", "origin": "..." },
      "history": [
        { "state": "RAW", "op": "Ingest", "date": "...", "status": "success" }
      ],
      "artifacts": [
        { "name": "doc.pdf", "size": "2MB", "type": "pdf" }
      ]
    }
    ```

### 2.4. Statistics (Sankey Data)
**GET /api/stats/cascade**
*   **Purpose:** Populates the "Detailed Multi-Cycle Cascade".
*   **Response:**
    ```json
    {
      "total_units": 6025,
      "cycles": {
        "c1": {
          "merge": { "total": 1200, "items": [{"name": "Direct", "val": 1200}] },
          "process": { "total": 400, "items": [...] },
          "excep": { "total": 400, "items": [...] }
        },
        "c2": { ... },
        "final": { ... }
      }
    }
    ```

---

## 3. Data Mapping Notes

### 3.1. Node Coordinates
*   **Important:** The frontend (`ProcessingControl.tsx` and `Statistics.tsx`) calculates visual layout based on hardcoded coordinates (`POS` constants) and Bezier curves.
*   **Requirement:** The Backend **does not** need to send coordinates. It only needs to send the **numerical counts** for specific keys (e.g., `metrics['merge_ready']`). The frontend handles the visual representation.

### 3.2. Status Mapping
Ensure backend statuses map to these frontend keys for correct color coding:
*   `success` -> Emerald Green
*   `warning` -> Amber/Orange
*   `error` -> Rose Red
*   `processing` -> Blue
*   `neutral` -> Slate Gray
