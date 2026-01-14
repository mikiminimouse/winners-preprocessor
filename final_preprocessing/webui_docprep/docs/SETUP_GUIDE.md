# Setup Guide: DocPrep Master Control

This guide details how to set up the frontend web UI in a new development environment.

## 1. Prerequisites

*   **Node.js:** Version 18.0.0 or higher.
*   **npm:** Version 9.0.0 or higher.
*   **Gemini API Key:** Required for the "AI Analysis" features in the Settings/Log components.

## 2. Installation

1.  **Extract the Archive:**
    Ensure you are in the root Administrator directory.

2.  **Install Dependencies:**
    ```bash
    npm install
    ```

3.  **Environment Configuration:**
    Create a `.env` file in the root directory (same level as `package.json`).
    ```env
    # .env
    GEMINI_API_KEY=AIzaSy...YourKeyHere
    ```
    *Note: The application uses `process.env.GEMINI_API_KEY` via Vite's define config.*

## 3. Running the Application

### Development Mode
To start the Vite development server with hot-reload:

```bash
npm run dev
```
*   Access the app at: `http://localhost:3000`

### Production Build
To create a static production build:

```bash
npm run build
```
The artifacts will be generated in the `dist/` folder. You can serve this using Nginx, Apache, or a simple Node server.

## 4. Connecting to a Real Backend

By default, the application runs in **Mock Mode**, generating data locally in `Dashboard.tsx`, `Statistics.tsx`, etc.

To connect to a real backend:

1.  **Create an API Service:**
    Create a new file `services/api.ts` to handle Axios/Fetch requests.

2.  **Replace Mock Data:**
    In components like `Dashboard.tsx`, replace the `PROTOCOL_TREE` constant with a `useEffect` hook that calls your API.

    *Example Migration:*
    ```typescript
    // BEFORE
    const PROTOCOL_TREE = { ...mock data... };

    // AFTER
    const [treeData, setTreeData] = useState<DirectoryNode | null>(null);
    useEffect(() => {
      fetch('/api/filesystem/tree')
        .then(res => res.json())
        .then(data => setTreeData(data));
    }, []);
    ```

3.  **WebSocket Integration:**
    For `ProcessingControl.tsx`, replace the `setInterval` simulation logic in `runSimulation` with a WebSocket listener that updates the `metrics` state based on incoming server messages.

## 5. Project Structure

*   `components/`: Reusable UI widgets.
    *   `ProcessingControl.tsx`: Main pipeline visualizer (Complex Canvas/SVG logic).
    *   `Statistics.tsx`: Recursive tree and Sankey flow.
*   `services/`: External API calls (Gemini).
*   `types.ts`: TypeScript interfaces for domain objects.
