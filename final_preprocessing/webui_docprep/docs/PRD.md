# Product Requirements Document (PRD)
## Project: DocPrep Master Control (v2.1.0)

### 1. Executive Summary
DocPrep Master Control is an advanced frontend dashboard designed to orchestrate, monitor, and debug a multi-stage document preprocessing pipeline. It visualizes the flow of documents through classification, conversion (Office to PDF), extraction (Archives), and normalization stages, providing granular visibility into success rates and exception handling.

### 2. User Personas
*   **DevOps Engineer:** Monitors system health, CPU load, and pipeline throughput.
*   **Data Steward:** Investigates specific failed units ("Exceptions"), reviews audit logs, and validates classification logic.
*   **Pipeline Operator:** Manages the execution of processing cycles and the final merge logic.

### 3. Functional Requirements

#### 3.1. Dashboard (Overview)
*   **Objective:** Provide a high-level snapshot of the current protocol execution.
*   **Features:**
    *   Display total unit counts vs. processed vs. failed.
    *   Visualize the directory structure as a recursive tree.
    *   Show real-time telemetry (CPU Load/Throughput) via charts.
    *   Highlight critical alerts (e.g., "High volume of ambiguous files").

#### 3.2. Processing Control (Orchestrator)
*   **Objective:** interactive control over the backend processing engine.
*   **Features:**
    *   **Cycle Mode:** Trigger discrete processing cycles (1, 2, 3).
    *   **Final Merge Mode:** Trigger the consolidation of staged files into the final delivery folder.
    *   **Visualization:** An animated, absolute-positioned node graph showing data flow from Source → Processors → Destination.
    *   **Live Logs:** A scrolling terminal window displaying real-time logs from the backend.

#### 3.3. Unit Explorer (Data Grid)
*   **Objective:** Deep-dive inspection of individual atomic units.
*   **Features:**
    *   Search/Filter by Unit ID, Route, or Status.
    *   **Inspector Panel:** Slide-out details showing:
        *   State Trace (History of state changes).
        *   Payload Artifacts (List of files inside the unit).
        *   Metadata (Hash, Origin).
    *   Action to download the raw unit package.

#### 3.4. Analytics & Statistics
*   **Objective:** Post-run analysis of data distribution.
*   **Features:**
    *   **Multi-Cycle Cascade:** A Sankey-style diagram showing how data moves between cycles.
    *   **Breakdowns:** Pie charts for Logic Routes and Bar charts for File Composition.
    *   **Recursive Tree:** A detailed file explorer with metric overlays.

#### 3.5. System Settings
*   **Objective:** Configuration management.
*   **Features:**
    *   Configure system paths (Input/Output volumes).
    *   Set thresholds (AI Confidence, Max File Size).
    *   Toggle debug logging.

### 4. Non-Functional Requirements
*   **Performance:** The dashboard must handle tree structures with 10,000+ nodes without UI freezing.
*   **Latency:** Status updates during a pipeline run should reflect within 500ms.
*   **Responsiveness:** The UI must adapt to desktop screens (1024px+).

### 5. AI Integration
*   **Log Analysis:** The system utilizes Google Gemini API to analyze raw log dumps and provide human-readable summaries of anomalies found during processing.
