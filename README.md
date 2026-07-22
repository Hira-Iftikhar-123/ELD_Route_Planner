# ELD Route Planner

A full-stack web application built with Django, Django REST Framework, and React that helps commercial truck drivers plan trips, visualize routes, and generate Electronic Logging Device (ELD) daily log sheets based on Hours of Service (HOS) regulations.

## Features

- Enter trip details:
  - Current Location
  - Pickup Location
  - Drop-off Location
  - Current Cycle Used (Hours)

- Interactive route visualization
  - Route from current location to pickup and drop-off
  - Distance and estimated travel time
  - Rest stop recommendations
  - Fuel stop recommendations (every 1,000 miles)

- Automatic ELD daily log generation
  - Driving
  - On Duty
  - Off Duty
  - Sleeper Berth
  - Multi-day log generation for long trips

- Hours of Service (HOS) calculations
  - 70 hours / 8-day cycle
  - Mandatory rest breaks
  - Pickup and drop-off time allocation

## Tech Stack

### Frontend

- React
- Vite
- Tailwind CSS
- Axios
- Leaflet or Mapbox

### Backend

- Django
- Django REST Framework

### APIs

- OpenRouteService or OSRM
- OpenStreetMap

## Project Structure

```text
eld-route-planner/
│
├── backend/
│   ├── Django Project
│   ├── REST API
│   └── HOS & ELD Logic
│
├── frontend/
│   ├── React Application
│   ├── Components
│   ├── Pages
│   └── Services
│
└── README.md
```

## Getting Started

### Clone the Repository

```bash
git clone https://github.com/your-username/eld-route-planner.git

cd eld-route-planner
```

## Backend Setup

Create and activate a virtual environment.

```bash
cd backend

python -m venv venv
```

Linux/macOS

```bash
source venv/bin/activate
```

Windows

```bash
venv\Scripts\activate
```

Install dependencies.

```bash
pip install -r requirements.txt
```

Apply database migrations.

```bash
python manage.py migrate
```

Start the development server.

```bash
python manage.py runserver
```

## Frontend Setup

```bash
cd frontend

npm install

npm run dev
```

## Environment Variables

Create a `.env` file in the backend directory.

```env
SECRET_KEY=your_secret_key
DEBUG=True
OPENROUTESERVICE_API_KEY=your_api_key
```

## Assumptions

The application follows the assessment assumptions:

- Property-carrying driver
- 70-hour / 8-day cycle
- No adverse driving conditions
- Fuel stop every 1,000 miles
- One hour allocated for pickup
- One hour allocated for drop-off

## Future Improvements

- PDF export for ELD logs
- User authentication
- Trip history
- Driver dashboard
- Fleet management
- Real-time traffic integration
- Weather integration

## Demo

**Live Application:** Coming Soon

**Loom Walkthrough:** Coming Soon
## License

This project was developed as part of a technical assessment and is intended for educational and demonstration purposes.
