# Frontend Development Specification: Sprite Service

## 1. Project Overview
This document outlines the architecture and implementation plan for the frontend interface of the Sprite Service. The goal is to provide a user-friendly web interface for uploading images, monitoring processing status, and downloading results, while strictly enforcing security so that the backend API is only accessible via this frontend.

## 2. Technology Stack

*   **Framework:** **Nuxt 3** (Vue 3 based meta-framework)
    *   Selected for its strong server-side rendering (SSR) capabilities and built-in server engine (Nitro), which is crucial for the security requirements.
*   **UI Library:** **Nuxt UI** (based on Tailwind CSS and Headless UI)
    *   Provides modern, accessible components (Buttons, Progress bars, Cards) out of the box.
*   **State Management:** **Pinia** (if complex state is needed, though simple `useState` might suffice for this scope).
*   **Containerization:** **Podman / Docker** (Node.js 18+ Alpine image).

## 3. Security Architecture (The "BFF" Pattern)

To satisfy the requirement that **"only this frontend can call the API"**, we will implement the **Backend for Frontend (BFF)** pattern using Nuxt's server capability (Nitro).

### Current Architecture (Insecure for public exposure)
`Browser -> [Python API (Port 8000)]`
*   *Risk:* Anyone with network access can hit port 8000 directly.

### Proposed Architecture (Secure)
`Browser -> [Nuxt Frontend (Port 3000)] -> [Nuxt Server Proxy (Internal)] -> [Python API (Internal Port 8000)]`

1.  **Network Isolation:**
    *   The Python API service in `docker-compose.yml` will **stop exposing port 8000 to the host machine**.
    *   It will only listen on the internal Docker network.
2.  **Server-Side Proxy:**
    *   The browser will *never* know the address of the Python API.
    *   The Browser sends requests to Nuxt Server Routes (e.g., `/api/upload`).
    *   Nuxt (running inside the Docker network) forwards the request to the Python API container (e.g., `http://api:8000`).
    *   This ensures that only the code running on the Nuxt server can communicate with the Python backend.

## 4. Feature Requirements

1.  **Image Upload:**
    *   Drag and drop interface.
    *   Support for PNG/JPG.
    *   Client-side validation (file size/type).
2.  **Processing Status:**
    *   Real-time (polling) progress bar or status indicator (Pending -> Processing -> Success/Failure).
    *   Visual feedback for errors.
3.  **Result Display:**
    *   Preview of the generated sprites (if feasible via zip stream or temp URL).
    *   "Download Zip" button.

## 5. API Interface (Nuxt Server Routes)

Nuxt will expose the following endpoints to its own frontend:

*   `POST /api/proxy/process`: Receives `multipart/form-data`, forwards to Python `POST /process`.
*   `GET /api/proxy/status/:id`: Forwards to Python `GET /status/{task_id}`.
*   `GET /api/proxy/download/:id`: Forwards to Python `GET /download/{task_id}` and streams the response to the client.

## 6. Implementation Plan

### Phase 1: Project Initialization
1.  Initialize Nuxt 3 project in `./frontend`.
2.  Install `tomcat`, `@nuxt/ui`.
3.  Create `frontend/Dockerfile`.
4.  Update root `docker-compose.yml` to include the frontend service and configure internal networking.

### Phase 2: Backend Network Reconfiguration
1.  Modify `docker-compose.yml` to remove `ports: - "8000:8000"` from the `api` service.
2.  Ensure `api` and `frontend` share a network `backend_network`.

### Phase 3: Nuxt Server Implementation (The Proxy)
1.  Create `server/api/upload.post.ts`: Handle file parsing and upstream forwarding.
2.  Create `server/api/status.get.ts`: Handle status polling proxy.
3.  Create `server/api/download.get.ts`: Handle stream proxying.

### Phase 4: UI Implementation
1.  **Layout:** Basic dashboard layout using Nuxt UI.
2.  **Components:**
    *   `FileUploader.vue`: UI for selecting files.
    *   `StatusCard.vue`: Shows task state and progress.
    *   `ResultPreview.vue`: Shows download button.
3.  **Page:** `index.vue` orchestrating the flow.

## 7. Configuration Details

**frontend/nuxt.config.ts**
```typescript
export default defineNuxtConfig({
  modules: ['@nuxt/ui'],
  runtimeConfig: {
    // Private keys (server-side only)
    apiUrl: 'http://api:8000', // Internal Docker URL
    // Public keys (exposed to client)
    public: {}
  }
})
```
