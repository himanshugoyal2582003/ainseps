# Antigravity Predict - Frontend (Next.js)

This directory contains the highly interactive, responsive web dashboard for the **AI-Based Stock Price Trend Prediction System**. It serves as the Presentation Layer of the application.

## 🎨 Design & Architecture

The frontend is built on **Next.js 15 (App Router)** utilizing **TypeScript**. It is designed with a premium, financial-terminal aesthetic (Dark Mode, Glassmorphism).

### Core Technologies

*   **Next.js 15 & React**: For server-side rendering and component-based UI construction.
*   **Tailwind CSS**: Utility-first CSS framework used for rapid UI styling, ensuring a fully responsive grid/flex layout across all devices.
*   **Recharts**: A composable charting library built on React components, used to render the dynamic, interactive SVG stock price graphs.
*   **Framer Motion**: For smooth micro-animations and component transitions.
*   **WebSockets**: Used to maintain a persistent, real-time connection with the FastAPI backend, allowing the UI to stream live agent collaboration logs as they happen.

## 📁 Directory Structure

*   **`app/`**: Contains the Next.js App Router structure.
    *   **`page.tsx`**: The primary dashboard view. Contains the layout, state management, Recharts integration, and WebSocket event handlers.
    *   **`globals.css`**: Defines global CSS tokens, including the dark theme variables, custom scrollbars, and neon accent colors.
    *   **`layout.tsx`**: The root layout wrapper for the application.
*   **`tailwind.config.ts`**: Configuration file for Tailwind CSS, defining custom colors, fonts, and theme extensions.

## 🚀 Setup & Installation

### Prerequisites
*   Node.js 18+

### Installation Steps

1.  **Navigate to the frontend directory:**
    ```bash
    cd frontend
    ```

2.  **Install dependencies:**
    ```bash
    npm install
    ```

3.  **Environment Variables:**
    Create a `.env.local` file in this `frontend/` directory to point to the backend server:
    ```env
    NEXT_PUBLIC_API_IP=<ip address of backend server>
    ```

4.  **Run the Development Server:**
    ```bash
    npm run dev
    ```

4.  **View the Application:**
    Open your browser and navigate to [http://localhost:3000](http://localhost:3000).

*Note: For the dashboard to display live data, ensure the FastAPI backend is running  on `<ip address of backend server>`.*
