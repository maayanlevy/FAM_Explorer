# FAM Explorer

This project now uses a small FastAPI backend and a React frontend built with Vite and components from `shadcn-ui`.

## Development

1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Start the backend API:
   ```bash
   uvicorn server:app --reload
   ```
3. Install frontend dependencies and start the development server:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

The React app proxies API requests to the FastAPI server at `http://localhost:8000`.
