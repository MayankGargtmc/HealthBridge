#!/bin/bash

# HealthBridge - Start Development Servers
# This script starts both backend and frontend servers

set -e

echo "🏥 Starting HealthBridge Development Servers..."
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Stopping servers..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start Backend
echo "Starting Backend (Django)..."
cd backend
source venv/bin/activate
python manage.py runserver &
BACKEND_PID=$!
cd ..

# Wait for backend to start
sleep 3

# Start Frontend
echo "Starting Frontend (React)..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ Servers started!"
echo ""
echo "  Frontend: http://localhost:3000"
echo "  Backend:  http://localhost:8000/api"
echo "  Admin:    http://localhost:8000/admin"
echo ""
echo "Press Ctrl+C to stop all servers"

# Wait for both processes
wait
