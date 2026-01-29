# HealthBridge 🏥

> Bridging the gap between fund providers and patient care

HealthBridge helps NGOs, Rotary clubs, and CSR agencies identify patients who need financial assistance for treatment by extracting and structuring medical data from various sources.

## 🎯 Problem Statement

NGOs and funding agencies lack structured data about patients who need financial help. Medical records exist in various formats (handwritten prescriptions, printed lab reports, unstructured hospital databases) making it difficult to identify and reach the right beneficiaries.

## 💡 Solution

HealthBridge digitizes and structures medical data from:
- 📄 Handwritten prescriptions (PDF/Images)
- 🖨️ Printed lab reports
- 🗄️ Unstructured clinical databases

And provides:
- 📊 Downloadable Excel with patient demographics
- 📈 Disease-level analytics dashboard
- 🗺️ Location-based patient distribution
- 👥 Age group analysis per disease

## 🏗️ Tech Stack

### Backend
- **Framework**: Django REST Framework
- **Database**: PostgreSQL (structured) + MongoDB (raw documents)
- **OCR/AI**: Eka Care API (primary) + OpenAI (fallback)

### Frontend
- **Framework**: React (Vite)
- **UI Library**: Tailwind CSS + shadcn/ui
- **Charts**: Recharts

### Infrastructure
- **Containerization**: Docker + Docker Compose
- **Deployment**: Railway / Render (easy hackathon deployment)

## 📁 Project Structure

```
healthbridge/
├── backend/                 # Django backend
│   ├── healthbridge/       # Main Django project
│   ├── apps/
│   │   ├── documents/      # Document upload & processing
│   │   ├── patients/       # Structured patient data
│   │   └── analytics/      # Dashboard & reports
│   ├── requirements.txt
│   └── manage.py
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── hooks/
│   └── package.json
├── docker-compose.yml
└── README.md
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose (optional)

### Option 1: Using Docker (Recommended)

```bash
# Clone and start
docker-compose up --build

# Access
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000/api
# Django Admin: http://localhost:8000/admin
```

### Option 2: Manual Setup

#### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

## 🔑 Environment Variables

Create `.env` files in respective directories:

### Backend (.env)
```env
DEBUG=True
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///db.sqlite3
MONGODB_URI=mongodb://localhost:27017/healthbridge
EKA_API_KEY=your-eka-api-key
OPENAI_API_KEY=your-openai-api-key
```

### Frontend (.env)
```env
VITE_API_URL=http://localhost:8000/api
```

## 📝 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/documents/upload/` | Upload medical documents |
| GET | `/api/documents/` | List all documents |
| GET | `/api/patients/` | List extracted patients |
| GET | `/api/patients/export/` | Export patients as CSV/Excel |
| GET | `/api/analytics/dashboard/` | Dashboard statistics |
| GET | `/api/analytics/diseases/` | Disease-wise breakdown |
| GET | `/api/analytics/locations/` | Location-wise distribution |

## 👥 Team

- Built with ❤️ at Ekathon 2026

## 📄 License

MIT License
