Documentation for the **SwiftAid Ambulance Tracking System**:

```markdown
# SwiftAid Ambulance Tracking System

## Overview
SwiftAid is a comprehensive ambulance tracking and management system designed to streamline emergency medical services. The system allows for real-time tracking of ambulances, efficient dispatch management, and 
provides a user-friendly interface for both administrators and patients.

## Some ScreenShots

![Screenshot_21-11-2024_213523_192 168 18 2](https://github.com/user-attachments/assets/3c4b4bb4-87d5-4b13-b61d-3302664c787e)
![Screenshot_21-11-2024_213630_192 168 18 2](https://github.com/user-attachments/assets/9e9b5ddb-a5f4-4dd5-a263-404a6558992d)
![Screenshot_21-11-2024_213659_192 168 18 2](https://github.com/user-attachments/assets/b99c8263-d127-41b5-acf2-9a651123c63b)

## Main Admin (Can add/remove/reset secondary admin)
![Screenshot_21-11-2024_21384_192 168 18 2](https://github.com/user-attachments/assets/c5ac0950-4b48-4d7f-aba6-2e87f7d40b84)

---

## Features
- **Real-time Ambulance Tracking**
- **Ambulance Booking System**
- **Nearest Hospital Finder**
- **Admin Dashboard**
- **User Tracking Interface**
- **PDF Report Generation**
- **Real-time Speed Calculation**
- **Estimated Time of Arrival (ETA) Prediction**

---

## Technology Stack
- **Backend:** Python with Flask framework  
- **Database:** SQLite  
- **Frontend:** HTML, CSS, JavaScript  
- **APIs:** Google Maps, OpenCage Geocoding  
- **Real-time Communication:** Flask-SocketIO  
- **PDF Generation:** ReportLab  

---

## System Architecture
The system follows a client-server architecture with the following components:
- **Web Server:** Flask application serving HTTP requests  
- **Database:** SQLite for data persistence  
- **WebSocket Server:** For real-time updates  
- **External APIs:** For geocoding and mapping services  

---

## Key Modules
### 1. **User Management**
- User registration and authentication  
- Admin login and dashboard access  

### 2. **Ambulance Booking**
- Patient information input  
- Location selection (pickup and destination)  
- Ambulance type selection  

### 3. **Tracking System**
- Real-time location updates  
- Speed calculation  
- ETA prediction  

### 4. **Hospital Finder**
- Locates nearest hospitals based on user's location  
- Provides hospital information and distance  

### 5. **Admin Dashboard**
- Overview of all ambulance requests  
- Status management of requests  
- Real-time tracking of all ambulances  

### 6. **Reporting**
- PDF generation of ambulance request details  
- Includes patient information, locations, and timestamps  

---

## Database Schema
### Tables
1. **`ambulance_requests`**  
   Stores details of each ambulance request.  

2. **`ambulance_locations`**  
   Tracks real-time locations of ambulances.  

3. **`admins`**  
   Stores admin user credentials.  

---

## API Endpoints
- **`/booking`** - `GET`, `POST`: Ambulance booking interface and form submission  
- **`/tracking`** - `GET`, `POST`: Ambulance tracking interface  
- **`/admin_dashboard`** - `GET`: Admin dashboard  
- **`/update_status/<req_id>`** - `POST`: Update request status  
- **`/download_pdf/<req_id>`** - `GET`: Generate and download PDF report  
- **`/find_nearest_hospitals`** - `GET`: AJAX endpoint for finding nearby hospitals  

---

## Real-time Features
- WebSocket connections for live updates of ambulance locations  
- Real-time calculation and display of ambulance speed  
- Live updates of request statuses on the admin dashboard  

---

## Security Measures
- **Password Hashing:** Using Werkzeug security for password protection  
- **Session Management:** Secure admin sessions  
- **HTTPS:** SSL context for encrypted communication  
- **Input Validation:** Sanitization of user inputs to prevent SQL injection  

---

## Algorithms
- **Haversine Formula:** For distance calculation between coordinates  
- **Geocoding:** Converting addresses to coordinates and vice versa  
- **Nearest Neighbor Search:** For finding nearby hospitals  
- **ETA Calculation:** Based on distance and average speed  

---

## External Service Integration
- **Google Maps API:** For mapping and geocoding services  
- **OpenCage Geocoding API:** Alternative geocoding service  

---

## Deployment
The application is configured to run on port `5001` with SSL encryption. It uses self-signed certificates for HTTPS in the development environment.

### Cloning the Repository
To clone the SwiftAid repository, use the following commands:
```bash
git clone https://github.com/Lusan-sapkota/Ambulance-tracking-system.git
cd swiftaid
```

---

## Setup Instructions
### 1. **Install Dependencies**
Ensure Python and pip are installed. Then, run:
```bash
pip install -r requirements.txt
```

### 2. **Create a `.env` File**
In the root directory of the project, create a file named `.env` and include your API keys:
```plaintext
GOOGLE_MAPS_API_KEY=your_google_maps_api_key
OPENCAGE_API_KEY=your_opencage_api_key
```

### 3. **Update HTML Files**
Add your Google Maps API key in `tracking_result.html` to ensure the maps feature works correctly.

### 4. **Run the Application**
Start the Flask server with:
```bash
python app.py
```
Access the application at [http://localhost:5001](http://localhost:5001).

---

## Future Enhancements
- **Mobile Application Integration**  
- **Machine Learning for More Accurate ETA Prediction**  
- **Integration with Hospital Management Systems**  
- **Multi-language Support**  
- **Advanced Analytics Dashboard**  

---

## Conclusion
SwiftAid provides a robust solution for ambulance tracking and management, enhancing the efficiency of emergency medical services. Its real-time capabilities, user-friendly interfaces, and comprehensive admin tools make it a valuable asset for healthcare providers and patients alike.
```
