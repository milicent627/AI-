@echo off
echo ============================================
echo   BookWright - AI小说写作与续写器
echo ============================================
echo.

cd /d "%~dp0\.."

echo [1/2] Starting backend server...
start "BookWright Backend" /MIN cmd /c "cd backend && uvicorn app.main:app --host 127.0.0.1 --port 8001"

echo [2/2] Starting frontend dev server...
echo.
echo The application will open at http://localhost:5173
echo Close this window to stop both servers.
echo.

cd frontend
npx vite --host
