#!/bin/bash

# HealthBridge - Quick Setup Script
# Run this to set up the development environment

set -e

echo "🏥 HealthBridge - Development Setup"
echo "===================================="

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.11+"
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+"
    exit 1
fi

echo "✅ Prerequisites checked"

# Setup Backend
echo ""
echo "📦 Setting up Backend..."
cd backend

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "  Created virtual environment"
fi

# Activate virtual environment and install dependencies
source venv/bin/activate
pip install -r requirements.txt -q
echo "  Installed Python dependencies"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "  Created .env file (please add your API keys)"
fi

# Run migrations
python manage.py migrate
echo "  Database migrations complete"

# Create superuser prompt
echo ""
read -p "Do you want to create a Django admin superuser? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    python manage.py createsuperuser
fi

cd ..

# Setup Frontend
echo ""
echo "📦 Setting up Frontend..."
cd frontend

# Install npm dependencies
npm install
echo "  Installed npm dependencies"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "  Created .env file"
fi

cd ..

echo ""
echo "🎉 Setup Complete!"
echo ""
echo "To start the development servers:"
echo ""
echo "  Backend (Terminal 1):"
echo "    cd backend && source venv/bin/activate && python manage.py runserver"
echo ""
echo "  Frontend (Terminal 2):"
echo "    cd frontend && npm run dev"
echo ""
echo "Or use Docker:"
echo "    docker-compose up --build"
echo ""
echo "Access the application:"
echo "  Frontend: http://localhost:3000"
echo "  Backend API: http://localhost:8000/api"
echo "  Django Admin: http://localhost:8000/admin"
echo ""
echo "Don't forget to add your API keys to backend/.env:"
echo "  - EKA_API_KEY (from https://developer.eka.care)"
echo "  - OPENAI_API_KEY (from https://platform.openai.com)"
