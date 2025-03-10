# SwiftAid Ambulance Tracking System

![SwiftAid Logo](https://github.com/user-attachments/assets/417db245-0f1a-4252-8324-b098107252dd)

## Overview

SwiftAid is a comprehensive ambulance tracking and management system designed to streamline emergency medical services. The system enables real-time ambulance tracking, efficient dispatch management, and provides intuitive interfaces for both administrators and patients.

## Key Screenshots

<div align="center">
  <img src="https://github.com/user-attachments/assets/3c4b4bb4-87d5-4b13-b61d-3302664c787e" alt="Patient Interface" width="32%">
  <img src="https://github.com/user-attachments/assets/9e9b5ddb-a5f4-4dd5-a263-404a6558992d" alt="Tracking View" width="32%">
  <img src="https://github.com/user-attachments/assets/b99c8263-d127-41b5-acf2-9a651123c63b" alt="Hospital Finder" width="32%">
</div>

### Main Admin Dashboard
The main administrator can add, remove, and reset secondary admin accounts.

<div align="center">
  <img src="https://github.com/user-attachments/assets/c5ac0950-4b48-4d7f-aba6-2e87f7d40b84" alt="Admin Dashboard" width="80%">
</div>

## Features

| Category | Features |
|----------|----------|
| **Core Functionality** | • Real-time Ambulance Tracking<br>• Ambulance Booking System<br>• Nearest Hospital Finder |
| **Administration** | • Comprehensive Admin Dashboard<br>• User Tracking Interface<br>• PDF Report Generation |
| **Technical** | • Real-time Speed Calculation<br>• Estimated Time of Arrival (ETA) Prediction |

## Technology Stack

<table>
  <tr>
    <td><strong>Backend</strong></td>
    <td>Python with Flask framework</td>
  </tr>
  <tr>
    <td><strong>Database</strong></td>
    <td>SQLite</td>
  </tr>
  <tr>
    <td><strong>Frontend</strong></td>
    <td>HTML, CSS, JavaScript</td>
  </tr>
  <tr>
    <td><strong>APIs</strong></td>
    <td>Google Maps, OpenCage Geocoding</td>
  </tr>
  <tr>
    <td><strong>Real-time Communication</strong></td>
    <td>Flask-SocketIO</td>
  </tr>
  <tr>
    <td><strong>PDF Generation</strong></td>
    <td>ReportLab</td>
  </tr>
</table>

## System Architecture

The system follows a client-server architecture with the following components:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Client Browser │◄────┤  Flask Web App  │◄────┤  SQLite Database│
└────────┬────────┘     └────────┬────────┘     └─────────────────┘
         │                       │
         │                       │                ┌─────────────────┐
         └───────────────────────┼────────────────┤  External APIs  │
                                 │                └─────────────────┘
                      ┌──────────┴────────┐
                      │ WebSocket Server  │
                      └───────────────────┘
```

## Key Modules

### 1. User Management
- User registration and authentication
- Admin login and dashboard access
- Role-based access control

### 2. Ambulance Booking
- Patient information input
- Location selection (pickup and destination)
- Ambulance type selection
- Priority level assignment

### 3. Tracking System
- Real-time location updates
- Speed calculation
- ETA prediction
- Route optimization

### 4. Hospital Finder
- Locates nearest hospitals based on user's location
- Provides hospital information and distance
- Filters by available services

### 5. Admin Dashboard
- Overview of all ambulance requests
- Status management of requests
- Real-time tracking of all ambulances
- Performance analytics

### 6. Reporting
- PDF generation of ambulance request details
- Includes patient information, locations, and timestamps
- Statistical reports for management

## Database Schema

### Key Tables

#### `ambulance_requests`
Stores details of each ambulance request.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| patient_name | TEXT | Name of the patient |
| contact | TEXT | Contact number |
| pickup_location | TEXT | Address for pickup |
| destination | TEXT | Hospital or destination address |
| status | TEXT | Current status of request |
| created_at | TIMESTAMP | Request creation time |

#### `ambulance_locations`
Tracks real-time locations of ambulances.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| request_id | INTEGER | Foreign key to ambulance_requests |
| latitude | REAL | Current latitude |
| longitude | REAL | Current longitude |
| speed | REAL | Current speed in km/h |
| timestamp | TIMESTAMP | Time of location update |

#### `admins`
Stores admin user credentials.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| username | TEXT | Admin username |
| password_hash | TEXT | Hashed password |
| is_main_admin | BOOLEAN | Flag for main admin privileges |

## API Endpoints

| Endpoint | Methods | Description |
|----------|---------|-------------|
| `/booking` | `GET`, `POST` | Ambulance booking interface and form submission |
| `/tracking` | `GET`, `POST` | Ambulance tracking interface |
| `/admin_dashboard` | `GET` | Admin dashboard |
| `/update_status/<req_id>` | `POST` | Update request status |
| `/download_pdf/<req_id>` | `GET` | Generate and download PDF report |
| `/find_nearest_hospitals` | `GET` | AJAX endpoint for finding nearby hospitals |
| `/login` | `GET`, `POST` | Admin authentication |
| `/logout` | `GET` | End admin session |

## Real-time Features

- WebSocket connections for live updates of ambulance locations
- Real-time calculation and display of ambulance speed
- Live updates of request statuses on the admin dashboard
- Instant notifications for new ambulance requests

## Security Measures

<table>
  <tr>
    <th>Feature</th>
    <th>Implementation</th>
  </tr>
  <tr>
    <td>Password Hashing</td>
    <td>Using Werkzeug security for password protection</td>
  </tr>
  <tr>
    <td>Session Management</td>
    <td>Secure admin sessions with timeout</td>
  </tr>
  <tr>
    <td>HTTPS</td>
    <td>SSL context for encrypted communication</td>
  </tr>
  <tr>
    <td>Input Validation</td>
    <td>Sanitization of user inputs to prevent SQL injection</td>
  </tr>
  <tr>
    <td>Access Control</td>
    <td>Role-based permissions for different admin levels</td>
  </tr>
</table>

## Algorithms

### Haversine Formula
For distance calculation between coordinates:

```
a = sin²(Δφ/2) + cos φ1 · cos φ2 · sin²(Δλ/2)
c = 2 · atan2(√a, √(1−a))
d = R · c
```
Where:
- φ is latitude
- λ is longitude
- R is earth's radius (6,371 km)

### ETA Calculation
```
ETA = (distance / average_speed) + traffic_factor
```

### Additional Algorithms
- Geocoding: Converting addresses to coordinates and vice versa
- Nearest Neighbor Search: For finding nearby hospitals
- Route optimization for efficient ambulance dispatch

## External Service Integration

### Google Maps API
- Maps rendering
- Geocoding services
- Route calculation
- Traffic data

### OpenCage Geocoding API
- Alternative geocoding service
- Reverse geocoding for address lookup
- Address validation

## Deployment

The application is configured to run on port `5001` with SSL encryption. It uses self-signed certificates for HTTPS in the development environment.

### System Requirements
- Python 3.6+
- 2GB RAM minimum
- 1GB free disk space
- Internet connection for API access

### Cloning the Repository
```bash
git clone https://github.com/Lusan-sapkota/Ambulance-tracking-system.git
cd swiftaid
```

## Setup Instructions

### 1. Install Dependencies
Ensure Python and pip are installed. Then, run:
```bash
pip install -r requirements.txt
```

### 2. Create a `.env` File
In the root directory of the project, create a file named `.env` and include your API keys:
```plaintext
GOOGLE_MAPS_API_KEY=your_google_maps_api_key
OPENCAGE_API_KEY=your_opencage_api_key
```

### 3. Update HTML Files
Add your Google Maps API key in `tracking_result.html` to ensure the maps feature works correctly:
```html
<script src="https://maps.googleapis.com/maps/api/js?key=YOUR_API_KEY&libraries=places"></script>
```

### 4. Run the Application
Start the Flask server with:
```bash
python app.py
```
Access the application at [https://localhost:5001](https://localhost:5001).

## Future Enhancements

<div align="center">
  <table>
    <tr>
      <td align="center"><strong>Mobile App</strong></td>
      <td align="center"><strong>ML Integration</strong></td>
      <td align="center"><strong>Hospital Integration</strong></td>
    </tr>
    <tr>
      <td>Native mobile applications for Android and iOS platforms</td>
      <td>Machine learning for more accurate ETA prediction and route optimization</td>
      <td>Direct integration with hospital management systems</td>
    </tr>
    <tr>
      <td align="center"><strong>Multilingual Support</strong></td>
      <td align="center"><strong>Analytics Dashboard</strong></td>
      <td align="center"><strong>Voice Recognition</strong></td>
    </tr>
    <tr>
      <td>Support for multiple languages to serve diverse populations</td>
      <td>Advanced analytics dashboard with performance metrics and insights</td>
      <td>Voice commands for hands-free operation in emergency situations</td>
    </tr>
  </table>
</div>

## Conclusion

SwiftAid provides a robust solution for ambulance tracking and management, enhancing the efficiency of emergency medical services. Its real-time capabilities, user-friendly interfaces, and comprehensive admin tools make it a valuable asset for healthcare providers and patients alike.

By reducing response times and optimizing resource allocation, SwiftAid contributes to improved patient outcomes in emergency situations.

---

© 2024 SwiftAid Ambulance Tracking System. All rights reserved.