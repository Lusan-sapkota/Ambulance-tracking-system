import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response, session
from werkzeug.security import check_password_hash, generate_password_hash
from flask_mail import Mail
from flask_mail import Message
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from dotenv import load_dotenv
import math
from math import radians, sin, cos, sqrt, atan2
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import requests
import googlemaps
import threading
import time
import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
from functools import wraps

app = Flask(__name__)
CORS(app)

load_dotenv()


app.secret_key = os.getenv('SECRET_KEY')
api_key = os.getenv('API_KEY')
socketio = SocketIO(app)


# Initialize Google Maps API client
gmaps = googlemaps.Client(key=api_key)

# Database initialization

def init_db():
    if not os.path.exists('users.db'):
        print("Database not found. Creating tables...")
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()

        # Create the ambulance_requests table with necessary columns
        cursor.execute(''' 
        CREATE TABLE IF NOT EXISTS ambulance_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            patient_name TEXT,
            contact TEXT,
            pickup_location TEXT,
            destination TEXT,
            ambulance_type TEXT,
            origin_lat REAL NOT NULL,
            origin_lng REAL NOT NULL,
            destination_lat REAL,
            destination_lng REAL,
            status TEXT DEFAULT 'Pending',
            estimated_arrival_time TEXT,
            estimated_completion_time TEXT,
            pickup_lat REAL,
            pickup_lng REAL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        ''')

        # Create the ambulance_locations table with ambulance_id reference
        cursor.execute(''' 
        CREATE TABLE IF NOT EXISTS ambulance_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ambulance_id INTEGER,
            latitude REAL,
            longitude REAL,
            timestamp TEXT,
            status TEXT,
            FOREIGN KEY (ambulance_id) REFERENCES ambulance_requests(id)
        );
        ''')

        cursor.execute(
            '''CREATE TABLE admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL
        );
        '''
        )

        # Indexing 'status' for faster queries
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON ambulance_requests(status)')

        conn.commit()
        conn.close()
        print("Tables created successfully.")
    else:
        print("Database already exists.")

    # If the table exists, check if the new columns are missing and add them
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    # Check if the new columns are present
    cursor.execute("PRAGMA table_info(ambulance_requests);")
    columns = [column[1] for column in cursor.fetchall()]

    # Add missing columns if they don't exist
    if 'pickup_lat' not in columns:
        cursor.execute('ALTER TABLE ambulance_requests ADD COLUMN pickup_lat REAL;')
        print("Added pickup_lat column.")

    if 'pickup_lng' not in columns:
        cursor.execute('ALTER TABLE ambulance_requests ADD COLUMN pickup_lng REAL;')
        print("Added pickup_lng column.")

    if 'request_time' not in columns:
        cursor.execute('ALTER TABLE ambulance_requests ADD COLUMN request_time TEXT;')
        print("Added request_time column.")

    if 'estimated_time_minutes' not in columns:
        cursor.execute('ALTER TABLE ambulance_requests ADD COLUMN estimated_time_minutes INTEGER;')
        print("Added estimated_time_minutes column.")

    if 'status' not in columns:
        cursor.execute('ALTER TABLE ambulance_requests ADD COLUMN status TEXT;')
        print("Added status column.")

    conn.commit()
    conn.close()
    print("Database schema updated successfully.")

# Call the function to initialize the database when the app starts
init_db()

# Register the datetime adapter for SQLite
def adapt_datetime(dt):
    return dt.isoformat()  # Convert datetime to string (ISO 8601 format)

def convert_datetime(s):
    return datetime.fromisoformat(s)  # Convert string back to datetime

sqlite3.register_adapter(datetime, adapt_datetime)  # Register the adapter
sqlite3.register_converter("datetime", convert_datetime)  # Register the converter


def reverse_geocode_for_address(address):
    open_cage_api_key  = os.getenv('OPENCAGE_API_KEY')  # Retrieve API key from environment
    if not open_cage_api_key :
        raise ValueError("API key for OpenCage is not set in environment variables.")
    
    url = f'https://api.opencagedata.com/geocode/v1/json?q={address}&key={open_cage_api_key }'
    
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        if data['results']:
            lat = data['results'][0]['geometry']['lat']
            lng = data['results'][0]['geometry']['lng']
            return lat, lng
        else:
            return None, None
    else:
        print(f"Error: {response.status_code}")
        return None, None

# Allowed file types for identity document upload
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'pdf'}
UPLOAD_FOLDER = 'uploads/'

# Function to check allowed file types
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Route to display the contact form
@app.route('/contact_admin')
def contact_admin():
    return render_template('contact_admin.html')

# Example function for inserting data into ambulance_requests
def insert_ambulance_request(user_id, patient_name, contact, pickup_location, destination, ambulance_type, origin_lat, origin_lng, destination_lat, destination_lng):
    if destination_lat is None or destination_lng is None:
        flash("Destination coordinates are missing.", "danger")
        return redirect(url_for('some_route'))  # Redirect or handle error accordingly

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO ambulance_requests (user_id, patient_name, contact, pickup_location, destination, ambulance_type, origin_lat, origin_lng, destination_lat, destination_lng)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, patient_name, contact, pickup_location, destination, ambulance_type, origin_lat, origin_lng, destination_lat, destination_lng))

    conn.commit()
    conn.close()

# Home Route
@app.route('/')
def index():
    return render_template('index.html', title="Home")

# Admin Login Route
@app.route('/admin', methods=['GET'])
def admin_login():
    return render_template('admin_login.html', title="Admin Login")

@app.route('/admin_login', methods=['POST'])
def admin_login_post():
    username = request.form['username']
    password = request.form['password']

    # Check if the user is the main admin (hardcoded credentials)
    if username == 'admin' and password == 'root@7890':
        session['logged_in'] = True
        session['is_main_admin'] = True  # Flag for main admin
        return redirect(url_for('admin_dashboard'))

    # Check if the user is a regular admin (from the 'admins' table)
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM admins WHERE username = ?', (username,))
    admin = cursor.fetchone()
    conn.close()

    if admin:
        # admin[2] is the hashed password from the database
        if check_password_hash(admin[2], password):  # Check the entered password
            session['logged_in'] = True
            session['is_main_admin'] = False  # Flag for regular admin
            return redirect(url_for('admin_dashboard'))

    # Flash an error message if login fails
    flash("Invalid login credentials. Please try again.", "error")
    return redirect(url_for('admin_login'))

def get_db_connection():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn

def is_main_admin():
    return session.get('is_main_admin', False)

# Decorator to require admin access
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_main_admin():
            flash("You do not have permission to view this page.", 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Route to Add Admin
@app.route('/add_admin', methods=['POST'])
@admin_required
def add_admin():
    username = request.form['username']
    password = request.form['password']
    hashed_password = generate_password_hash(password)

    conn = get_db_connection()
    conn.execute('INSERT INTO admins (username, password) VALUES (?, ?)', (username, hashed_password))
    conn.commit()
    conn.close()

    flash('Admin added successfully!', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/delete_admin', methods=['POST'])
@admin_required
def delete_admin():
    username = request.form['username']

    conn = get_db_connection()
    cursor = conn.cursor()

    # First, check if the admin exists
    cursor.execute('SELECT * FROM admins WHERE username = ?', (username,))
    admin = cursor.fetchone()

    if admin:
        # Proceed with deletion if the admin exists
        cursor.execute('DELETE FROM admins WHERE username = ?', (username,))
        conn.commit()
        flash('Admin deleted successfully!', 'success')
    else:
        flash(f'No admin found with username: {username}', 'error')

    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/forgot_password', methods=['GET'])
def forgot_password():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    # Get all admins for the dropdown in the modal
    cursor.execute('SELECT id, username FROM admins')
    admins = cursor.fetchall()

    conn.close()
    return render_template('forgot_password.html', admins=admins)

# Route to reset password
@app.route('/reset_password', methods=['POST'])
def reset_password():
    admin_username = request.form['username']
    new_password = request.form['new_password']
    
    # Hash the new password
    hashed_password = generate_password_hash(new_password)

    # Update the password for the selected admin
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE admins SET password = ? WHERE username = ?', (hashed_password, admin_username))
    conn.commit()
    conn.close()

    flash(f'Password for {admin_username} has been reset successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

# Admin Dashboard Route
@app.route('/admin_dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    search_query = request.args.get('search', '')  # Get search query, default to empty string

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    # If there's a search query, filter by patient_name using LIKE operator
    if search_query:
        search_query = '%' + search_query + '%'
        cursor.execute('''SELECT id, patient_name, pickup_location, destination, status, contact, estimated_arrival_time
                          FROM ambulance_requests
                          WHERE patient_name LIKE ? OR contact LIKE ?''', (search_query, search_query))
    else:
        # Get all ambulance requests without any filter
        cursor.execute('''SELECT id, patient_name, pickup_location, destination, status, contact, estimated_arrival_time
                          FROM ambulance_requests''')
    
    all_requests = cursor.fetchall()

    # Get requests by status (new, on the way, etc.)
    cursor.execute('SELECT id, patient_name, pickup_location, destination, status, contact, estimated_arrival_time FROM ambulance_requests WHERE status = "New"')
    new_requests = cursor.fetchall()

    cursor.execute('SELECT id, patient_name, pickup_location, destination, status, contact, estimated_arrival_time FROM ambulance_requests WHERE status = "Started"')
    on_the_way = cursor.fetchall()

    cursor.execute('SELECT id, patient_name, pickup_location, destination, status, contact, estimated_arrival_time FROM ambulance_requests WHERE status = "Patient Received"')
    patient_received = cursor.fetchall()

    cursor.execute('SELECT id, patient_name, pickup_location, destination, status, contact, estimated_arrival_time FROM ambulance_requests WHERE status = "Patient Reached"')
    patient_reached = cursor.fetchall()

    # Additional statuses, if needed
    cursor.execute('SELECT id, patient_name, pickup_location, destination, status, contact, estimated_arrival_time FROM ambulance_requests WHERE status = "Assigned"')
    assigned_requests = cursor.fetchall()

    cursor.execute('SELECT id, patient_name, pickup_location, destination, status, contact, estimated_arrival_time FROM ambulance_requests WHERE status = "Rejected"')
    rejected_requests = cursor.fetchall()

    # Fetch the admin usernames for the delete modal
    cursor.execute('SELECT username FROM admins')
    admins = cursor.fetchall()
    print(admins)

    conn.close()

    # Render the dashboard template with all the categories and admins passed
    return render_template('admin_dashboard.html', title="Admin Dashboard", 
                           all_requests=all_requests, new_requests=new_requests,
                           on_the_way=on_the_way, patient_received=patient_received,
                           patient_reached=patient_reached, assigned_requests=assigned_requests,
                           rejected_requests=rejected_requests, search_query=search_query,
                           admins=admins)

def auto_update_status():
    while True:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()

        # Get the current time
        current_time = datetime.now()

        # Debugging: Print the current time for comparison
        print(f"Current time: {current_time}")

        # Check for requests where the estimated completion time has passed
        cursor.execute('''SELECT id, estimated_completion_time FROM ambulance_requests 
                          WHERE status = 'Patient Received' ''')
        
        rows = cursor.fetchall()
        
        for row in rows:
            request_id, estimated_completion_time = row
            
            # Convert the estimated_completion_time to a datetime object
            try:
                estimated_time = datetime.fromisoformat(estimated_completion_time)
                print(f"Request {request_id}: Estimated time = {estimated_time}")
                
                # If the estimated time has passed, update the status
                if current_time >= estimated_time:
                    print(f"Updating status for request {request_id}")
                    cursor.execute('''UPDATE ambulance_requests
                                      SET status = 'Patient Reached'
                                      WHERE id = ?''', (request_id,))
                    conn.commit()
            except ValueError:
                print(f"Error parsing estimated completion time for request {request_id}")
        
        conn.close()

        # Sleep for a minute before checking again
        time.sleep(60)

# Start the background task
status_update_thread = threading.Thread(target=auto_update_status, daemon=True)
status_update_thread.start()

def execute_query(query, params=()):
    # Connect to the SQLite database
    conn = sqlite3.connect('users.db')  # Replace with your database path
    cursor = conn.cursor()
    
    # Execute the query with parameters
    cursor.execute(query, params)
    
    # Commit the changes
    conn.commit()
    
    # Close the connection
    conn.close()

# Fetch current location using Google Maps API
def get_coordinates(location):
    import requests
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={location}&key={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data['results']:
            lat = data['results'][0]['geometry']['location']['lat']
            lng = data['results'][0]['geometry']['location']['lng']
            return lat, lng
    return None, None

@socketio.on('update_location')
def handle_location_update(data):
    import math
    ambulance_id = data['ambulance_id']
    latitude = data['latitude']
    longitude = data['longitude']

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    # Update the current location of the ambulance
    cursor.execute('''UPDATE ambulance_locations
                      SET latitude = ?, longitude = ?, last_updated = ?
                      WHERE ambulance_id = ?''',
                   (latitude, longitude, datetime.now(), ambulance_id))
    conn.commit()

    # Fetch the destination coordinates from the request
    cursor.execute('SELECT destination_lat, destination_lng FROM ambulance_requests WHERE ambulance_id = ?', (ambulance_id,))
    destination = cursor.fetchone()

    if destination:
        dest_lat, dest_lng = destination

        # Calculate the distance using the Haversine formula
        distance_km = haversine(latitude, longitude, dest_lat, dest_lng)

        # If the ambulance is close enough (200 meters), update the status to "Patient Reached"
        if distance_km <= 0.2:
            cursor.execute('UPDATE ambulance_requests SET status = "Patient Reached" WHERE ambulance_id = ?', (ambulance_id,))
            conn.commit()
            emit('status_update', {'ambulance_id': ambulance_id, 'status': 'Patient Reached'}, broadcast=True)

        # Calculate the ETA (assuming an average speed of 80 km/h)
        speed_kmh = 80
        eta_minutes = (distance_km / speed_kmh) * 60

        # Broadcast the location update with distance and ETA
        emit('location_update', {
            'ambulance_id': ambulance_id,
            'latitude': latitude,
            'longitude': longitude,
            'distance_km': round(distance_km, 2),
            'eta_minutes': round(eta_minutes, 2)
        }, broadcast=True)

    conn.close()


# Convert degrees to radians
def radians(deg):
    return deg * (3.141592653589793 / 180)

# Sine approximation using Taylor series
def sin(x):
    # Using the first three terms of Taylor series for sin(x)
    x3 = x * x * x
    return x - (x3 / 6) + (x3 * x * x / 120)

# Cosine approximation using Taylor series
def cos(x):
    # Using the first three terms of Taylor series for cos(x)
    x2 = x * x
    return 1 - (x2 / 2) + (x2 * x2 / 24)

# Square root approximation using Newton's method
def sqrt(x):
    # Initial guess
    guess = x / 2.0
    for _ in range(10):  # Iterate to refine the guess
        guess = (guess + x / guess) / 2.0
    return guess

# Arctan approximation using Taylor series
def atan2(y, x):
    # Approximate atan2 using a simplified version of the Taylor series
    if x > 0:
        return y / x
    elif x < 0 and y >= 0:
        return (3.141592653589793 + y / x)
    elif x < 0 and y < 0:
        return (-3.141592653589793 + y / x)
    elif x == 0 and y != 0:
        return 3.141592653589793 / 2 * (1 if y > 0 else -1)
    return 0  # x and y are both 0

# Haversine distance calculation
def haversine(lat1, lon1, lat2, lon2):
    # Radius of Earth in kilometers
    R = 6371

    # Convert latitude and longitude from degrees to radians
    lat1 = radians(lat1)
    lon1 = radians(lon1)
    lat2 = radians(lat2)
    lon2 = radians(lon2)

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    # Distance in kilometers
    return R * c

@app.route('/get_eta/<int:ambulance_id>', methods=['GET'])
def get_eta(ambulance_id):
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()

        # Fetch the current location of the ambulance
        cursor.execute('SELECT latitude, longitude FROM ambulance_locations WHERE ambulance_id = ?', (ambulance_id,))
        current_location = cursor.fetchone()

        # Fetch the destination coordinates
        cursor.execute('SELECT destination_lat, destination_lng FROM ambulance_requests WHERE id = ?', (ambulance_id,))
        destination = cursor.fetchone()

        conn.close()

        # Validate fetched data
        if not current_location or not destination:
            flash("Location or destination not found.", "error")
            return redirect(url_for('admin_dashboard'))

        lat1, lon1 = current_location
        lat2, lon2 = destination

        if None in (lat1, lon1, lat2, lon2):
            flash("Invalid location data for ETA calculation.", "error")
            return redirect(url_for('admin_dashboard'))

        # Use Google Maps Distance Matrix API to get travel time with traffic
        response = gmaps.distance_matrix(
            origins=f"{lat1},{lon1}",
            destinations=f"{lat2},{lon2}",
            mode="driving",
            departure_time="now",
            traffic_model="best_guess"
        )

        # Parse the response
        if response['rows'] and response['rows'][0]['elements'][0]['status'] == 'OK':
            duration_seconds = response['rows'][0]['elements'][0]['duration_in_traffic']['value']
            distance_meters = response['rows'][0]['elements'][0]['distance']['value']

            # Convert distance to kilometers and time to minutes
            distance_km = distance_meters / 1000
            eta_minutes = duration_seconds / 60

            flash("ETA calculation successful.", "success")
            return jsonify({
                'eta_minutes': round(eta_minutes, 2),
                'distance_km': round(distance_km, 2),
                'status': 'On The Way' if distance_km > 0.2 else 'Patient Reached'
            })
        else:
            flash("Error fetching traffic data from Google Maps API.", "error")
            return redirect(url_for('admin_dashboard'))

    except Exception as e:
        flash(f"An unexpected error occurred: {str(e)}", "error")
        return redirect(url_for('admin_dashboard'))

def calculate_speed(lat1, lon1, lat2, lon2, time1, time2):
    # Calculate distance using Haversine formula
    distance_km = haversine(lat1, lon1, lat2, lon2)
    
    # Calculate time difference in hours
    time_diff_hours = (time2 - time1).total_seconds() / 3600
    
    # Speed in km/h
    if time_diff_hours > 0:
        speed_kmh = distance_km / time_diff_hours
        return speed_kmh
    return 0


# Route to update the status of a request
@app.route('/update_status/<int:req_id>', methods=['POST'])
def update_status(req_id):
    new_status = request.form.get('status')

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    # Update the status in the database
    cursor.execute("UPDATE ambulance_requests SET status = ? WHERE id = ?", (new_status, req_id))
    conn.commit()

    # If the status is set to "Patient Received," calculate the ETA
    if new_status == "Patient Received":
        cursor.execute("SELECT origin_lat, origin_lng, destination_lat, destination_lng FROM ambulance_requests WHERE id = ?", (req_id,))
        location_data = cursor.fetchone()

        if location_data:
            lat1, lon1, lat2, lon2 = location_data

            # Validate that latitude and longitude values are not None
            if None not in (lat1, lon1, lat2, lon2):
                try:
                    # Calculate distance using the Haversine formula
                    distance = haversine(lat1, lon1, lat2, lon2)
                    speed_kmh = 80  # Average speed of the ambulance in km/h
                    eta_minutes = (distance / speed_kmh) * 60

                    # Calculate the estimated completion time
                    estimated_completion_time = datetime.now() + timedelta(minutes=eta_minutes)

                    # Update the estimated completion time in the database
                    cursor.execute("UPDATE ambulance_requests SET estimated_completion_time = ? WHERE id = ?", (estimated_completion_time, req_id))
                    conn.commit()

                except Exception as e:
                    flash(f"Error calculating ETA: {str(e)}", "danger")
            else:
                flash("Error: Invalid location data for ETA calculation.", "danger")

    conn.close()
    flash("Status updated successfully!", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/download_pdf/<int:req_id>')
def download_pdf(req_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    cursor.execute('''SELECT r.patient_name, r.contact, r.pickup_location, r.destination, r.ambulance_type, 
                             r.origin_lat, r.origin_lng, r.destination_lat, r.destination_lng, r.status, 
                             r.estimated_arrival_time, r.estimated_completion_time, 
                             r.pickup_lat, r.pickup_lng
                      FROM ambulance_requests r
                      WHERE r.id = ?''', (req_id,))
    report = cursor.fetchone()
    conn.close()

    if report:
        # Unpack the report tuple
        patient_name, contact, pickup_location, destination, ambulance_type, \
        origin_lat, origin_lng, destination_lat, destination_lng, status, \
        estimated_arrival_time, estimated_completion_time, pickup_lat, pickup_lng = report

        # Format datetime fields
        for time_field in [estimated_arrival_time, estimated_completion_time]:
            if time_field and time_field != 'Not Available':
                time_field = datetime.fromisoformat(time_field).strftime('%B %d, %Y %I:%M %p')

        # Create PDF buffer
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )

        # Create styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.HexColor('#1a365d')
        )
        
        header_style = ParagraphStyle(
            'CustomHeader',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#2d3748')
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#4a5568'),
            spaceAfter=12
        )

        # Build the document content
        elements = []

        # Add logo and company info
        elements.append(Paragraph("SwiftAid", title_style))
        elements.append(Paragraph("Emergency Medical Services", header_style))
        elements.append(Spacer(1, 0.2 * inch))
        elements.append(Paragraph("Contact: +977 1 674 936 890 | support@swiftaid.com", normal_style))
        
        # Add horizontal line
        elements.append(Spacer(1, 0.3 * inch))
        elements.append(Table([['']], colWidths=[450], style=TableStyle([
            ('LINEABOVE', (0, 0), (-1, 0), 1, colors.HexColor('#e2e8f0'))
        ])))
        elements.append(Spacer(1, 0.3 * inch))

        # Create the main content table
        data = [
            ["Patient Information", ""],
            ["Patient Name:", patient_name],
            ["Contact:", contact],
            ["", ""],
            ["Transport Details", ""],
            ["Pickup Location:", pickup_location],
            ["Destination:", destination],
            ["Ambulance Type:", ambulance_type],
            ["Status:", status],
            ["", ""],
            ["Location Coordinates", ""],
            ["Origin:", f"Lat: {origin_lat}, Long: {origin_lng}"],
            ["Destination:", f"Lat: {destination_lat}, Long: {destination_lng}"],
        ]

        if estimated_completion_time != 'Not Available':
            data.extend([
                ["", ""],
                ["Timing", ""],
                ["Completion Time:", estimated_completion_time]
            ])

        # Style the table
        table_style = TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#4a5568')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            # Style section headers
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#2d3748')),
            ('FONTNAME', (0, 4), (-1, 4), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 4), (-1, 4), 12),
            ('TEXTCOLOR', (0, 4), (-1, 4), colors.HexColor('#2d3748')),
            ('FONTNAME', (0, 10), (-1, 10), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 10), (-1, 10), 12),
            ('TEXTCOLOR', (0, 10), (-1, 10), colors.HexColor('#2d3748')),
        ])

        if estimated_completion_time != 'Not Available':
            table_style.add('FONTNAME', (0, 14), (-1, 14), 'Helvetica-Bold')
            table_style.add('FONTSIZE', (0, 14), (-1, 14), 12)
            table_style.add('TEXTCOLOR', (0, 14), (-1, 14), colors.HexColor('#2d3748'))

        table = Table(data, colWidths=[2*inch, 4*inch])
        table.setStyle(table_style)
        elements.append(table)

        # Add footer
        elements.append(Spacer(1, inch))
        footer_text = """Thank you for trusting SwiftAid with your emergency care needs.
        For more information, visit: www.swiftaid.com"""
        elements.append(Paragraph(footer_text, ParagraphStyle(
            'Footer',
            parent=styles['Italic'],
            fontSize=8,
            textColor=colors.HexColor('#718096'),
            alignment=1
        )))

        # Build and return the PDF
        doc.build(elements)
        pdf_data = buffer.getvalue()
        buffer.close()

        return Response(
            pdf_data,
            mimetype='application/pdf',
            headers={"Content-Disposition": "attachment;filename=ambulance_report.pdf"}
        )
    else:
        flash("No report found for this request.", "danger")
        return redirect(url_for('admin_dashboard'))

@app.route('/view_report/<int:req_id>')
def view_report(req_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    # Updated query to fetch all necessary fields
    cursor.execute('''SELECT r.patient_name, r.contact, r.pickup_location, r.destination, r.ambulance_type, 
                             r.origin_lat, r.origin_lng, r.destination_lat, r.destination_lng, r.status, 
                             r.estimated_arrival_time, r.estimated_completion_time, 
                             r.pickup_lat, r.pickup_lng
                      FROM ambulance_requests r
                      WHERE r.id = ?''', (req_id,))
    report = cursor.fetchone()
    conn.close()

    if report:
        # Unpack the report tuple
        patient_name, contact, pickup_location, destination, ambulance_type, \
        origin_lat, origin_lng, destination_lat, destination_lng, status, \
        estimated_arrival_time, estimated_completion_time, pickup_lat, pickup_lng = report

        # Optional: Convert estimated arrival/completion time if needed
        if estimated_arrival_time and estimated_arrival_time != 'Not Available':
            estimated_arrival_time = datetime.fromisoformat(estimated_arrival_time).strftime('%Y-%m-%d %H:%M:%S')
        if estimated_completion_time and estimated_completion_time != 'Not Available':
            estimated_completion_time = datetime.fromisoformat(estimated_completion_time).strftime('%Y-%m-%d %H:%M:%S')

        # Return the data to the frontend template
        return render_template('report.html',
                               patient_name=patient_name,
                               contact=contact,
                               pickup_location=pickup_location,
                               destination_location=destination,
                               ambulance_type=ambulance_type,
                               origin_lat=origin_lat,
                               origin_lng=origin_lng,
                               destination_lat=destination_lat,
                               destination_lng=destination_lng,
                               status=status,
                               estimated_arrival_time=estimated_arrival_time,
                               estimated_completion_time=estimated_completion_time,
                               pickup_lat=pickup_lat,
                               pickup_lng=pickup_lng,
                               req_id=req_id)  # Make sure req_id is passed here
    else:
        flash("No report found for this request.", "danger")
        return redirect(url_for('admin_dashboard'))


@app.route('/delete_request/<int:req_id>', methods=['POST'])
def delete_request(req_id):
    try:
        # Connect to the database
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()

        # SQL query to delete the request by ID
        cursor.execute("DELETE FROM ambulance_requests WHERE id = ?", (req_id,))

        # Commit the changes and close the connection
        conn.commit()
        conn.close()

        # Flash a success message
        flash('Request deleted successfully!', 'success')

    except Exception as e:
        # Handle any errors and flash an error message
        flash(f'An error occurred while deleting the request: {str(e)}', 'danger')

    # Redirect back to the admin dashboard
    return redirect(url_for('admin_dashboard'))


@app.route('/update_ambulance_location', methods=['POST'])
def update_ambulance_location():
    try:
        # Get form data
        ambulance_id = request.form['ambulance_id']
        latitude = request.form['latitude']
        longitude = request.form['longitude']
        status = request.form['status']  # e.g., "On The Way", "Patient Picked", etc.

        # Validate the data
        if not ambulance_id or not latitude or not longitude or not status:
            flash("Missing required fields", "danger")
            return redirect(url_for('admin_dashboard'))

        # Convert latitude and longitude to float
        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except ValueError:
            flash("Invalid latitude or longitude values", "danger")
            return redirect(url_for('admin_dashboard'))

        # Check if the ambulance_id exists in ambulance_requests table
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM ambulance_requests WHERE id = ?', (ambulance_id,))
        if cursor.fetchone() is None:
            flash("Invalid ambulance ID", "danger")
            return redirect(url_for('admin_dashboard'))

        # Insert new location into ambulance_locations table
        cursor.execute('''INSERT INTO ambulance_locations (ambulance_id, latitude, longitude, status)
                          VALUES (?, ?, ?, ?)''', (ambulance_id, latitude, longitude, status))

        conn.commit()
        conn.close()

        flash("Ambulance location updated successfully.", "success")
        return redirect(url_for('admin_dashboard'))
    
    except Exception as e:
        flash(f"Error updating ambulance location: {str(e)}", "danger")
        return redirect(url_for('admin_dashboard'))


@app.route('/booking', methods=['GET'])
def booking():
    return render_template('booking.html')

# Route to handle the ambulance booking form submission
@app.route('/book_ambulance', methods=['POST'])
def book_ambulance():
    name = request.form['name']
    contact = request.form['contact']
    location = request.form['location']
    destination = request.form['destination']
    ambulance_type = request.form['ambulance_type']
    radius = request.form.get('radius', 10000)  # Get radius from form, default to 10000 meters if not provided

    # Extract latitude and longitude from the location field
    try:
        lat, lng = map(float, location.replace("Latitude: ", "").replace("Longitude: ", "").split(", "))
    except ValueError:
        flash("Invalid location format.", "danger")
        return redirect(url_for('booking'))

    # Reverse geocode the pickup location
    pickup_address = reverse_geocode(lat, lng)

    # Attempt to find the nearest hospitals and extract destination coordinates
    try:
        nearest_hospitals = find_nearest_hospitals(lat, lng, radius)  # Pass the radius parameter here
        if nearest_hospitals and len(nearest_hospitals) > 0:
            # Prepare the hospital information
            hospital_info = [f"{h[0]} ({h[2]} km away) - {h[1]}" for h in nearest_hospitals]
            destination = destination or hospital_info[0]
            print("Nearest hospitals found:", hospital_info)
            
            # Reverse geocode the destination address
            destination_lat, destination_lng = reverse_geocode_for_address(destination)
            if destination_lat is None or destination_lng is None:
                flash("Invalid destination format or unable to geocode destination.", "danger")
                return redirect(url_for('booking'))
        else:
            flash("No suitable hospitals found nearby. Please specify a destination manually.", "warning")
            return redirect(url_for('booking'))
    except Exception as e:
        print("Error finding nearest hospitals:", e)
        flash("An error occurred while retrieving nearby hospitals. Please try again later.", "danger")
        return redirect(url_for('booking'))

    # Calculate estimated time in minutes (based on distance and an average speed)
    distance_km = calculate_distance(lat, lng, destination_lat, destination_lng)
    estimated_time_minutes = (distance_km / 80) * 60  # ETA in minutes at 80 km/h speed

    # Save the booking request to the database
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()

        # Insert the ambulance request with the additional columns
        cursor.execute(''' 
            INSERT INTO ambulance_requests (patient_name, contact, pickup_location, destination, ambulance_type, origin_lat, origin_lng, destination_lat, destination_lng, request_time, estimated_time_minutes, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, contact, pickup_address, destination, ambulance_type, lat, lng, destination_lat, destination_lng, datetime.now().isoformat(), estimated_time_minutes, 'Pending'))

        # Get the last inserted ambulance request ID
        ambulance_id = cursor.lastrowid  # Get the last inserted ambulance request ID

        # Insert the initial ambulance location into the ambulance_locations table
        cursor.execute('''
            INSERT INTO ambulance_locations (ambulance_id, latitude, longitude, timestamp, status)
            VALUES (?, ?, ?, ?, ?)
        ''', (ambulance_id, lat, lng, datetime.now().isoformat(), 'Pending'))  # Set the status to 'Pending'

        conn.commit()
        conn.close()

        flash("Ambulance requested successfully!", "success")
    except Exception as e:
        print("Database insertion error:", e)
        flash("An error occurred while saving your request. Please try again.", "danger")
        return redirect(url_for('booking'))

    return redirect(url_for('booking'))



@app.route('/find_nearest_hospitals', methods=['GET'])
def ajax_find_nearest_hospitals():
    lat = request.args.get('lat', type=float)
    lng = request.args.get('lng', type=float)
    radius = request.args.get('radius', type=int, default=10000)  # Default to 10km if not provided

    if lat is None or lng is None:
        return jsonify({'error': 'Invalid coordinates'}), 400

    try:
        nearest_hospitals = find_nearest_hospitals(lat, lng, radius)
        if nearest_hospitals:
            response_data = {
                'hospitals': [
                    {
                        'name': h[0],
                        'address': h[1],
                        'distance_km': round(h[2], 2) if isinstance(h[2], (int, float)) else 'N/A',
                        'latitude': h[3],  # Make sure to include latitude
                        'longitude': h[4]  # Make sure to include longitude
                    }
                    for h in nearest_hospitals
                ]
            }
            return jsonify(response_data)
        else:
            return jsonify({'hospitals': []})
    except Exception as e:
        print(f"Error in backend processing: {e}")  # Log the error
        return jsonify({'error': 'Internal Server Error'}), 500



def find_nearest_hospitals(lat, lng, radius):
    hospitals = []
    try:
        places = gmaps.places_nearby(location=(lat, lng), radius=radius, type='hospital')
        
        # Process the initial set of results
        if 'results' in places:
            for place in places['results']:
                name = place['name']
                address = place.get('vicinity', 'N/A')
                hospital_lat = place['geometry']['location']['lat']
                hospital_lng = place['geometry']['location']['lng']
                distance_km = haversine(lat, lng, hospital_lat, hospital_lng)

                hospitals.append((name, address, distance_km, hospital_lat, hospital_lng))

        # Check for next page of results
        while 'next_page_token' in places:
            time.sleep(2)  # Wait for the token to become valid
            places = gmaps.places_nearby(page_token=places['next_page_token'])
            if 'results' in places:
                for place in places['results']:
                    name = place['name']
                    address = place.get('vicinity', 'N/A')
                    hospital_lat = place['geometry']['location']['lat']
                    hospital_lng = place['geometry']['location']['lng']
                    distance_km = haversine(lat, lng, hospital_lat, hospital_lng)

                    hospitals.append((name, address, distance_km, hospital_lat, hospital_lng))

    except Exception as e:
        print(f"An error occurred while finding hospitals: {e}")

    return hospitals


def has_arrived(current_lat, current_lng, destination_lat, destination_lng, arrival_threshold_km=0.1):
    # Calculate the distance from the current location to the destination
    distance_to_destination = haversine(current_lat, current_lng, destination_lat, destination_lng)
    return distance_to_destination <= arrival_threshold_km  # Check if within 100 meters (0.1 km)

def check_if_arrived_on_time(ambulance_id):
    try:
        # Connect to the database
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()

        # Fetch request time, estimated time, and current status
        cursor.execute(''' 
            SELECT request_time, estimated_time_minutes, status 
            FROM ambulance_requests 
            WHERE id = ?
        ''', (ambulance_id,))
        result = cursor.fetchone()

        if result:
            request_time_str, estimated_time_minutes, current_status = result

            # Parse request time
            request_time = datetime.strptime(request_time_str, "%Y-%m-%d %H:%M:%S")

            # Determine the reference start time for ETA calculation
            if current_status == "Patient Received":
                # Fetch the time when the status was last updated to "Patient Received"
                cursor.execute(''' 
                    SELECT timestamp 
                    FROM status_updates 
                    WHERE ambulance_id = ? AND new_status = ? 
                    ORDER BY timestamp DESC LIMIT 1
                ''', (ambulance_id, "Patient Received"))
                status_update = cursor.fetchone()

                if status_update:
                    request_time = datetime.strptime(status_update[0], "%Y-%m-%d %H:%M:%S")

            # Calculate the estimated arrival time
            estimated_arrival_time = request_time + timedelta(minutes=estimated_time_minutes)

            # Get the current real-time
            current_time = datetime.now()

            # Debugging: Print times to verify
            print(f"Current Time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Estimated Arrival Time: {estimated_arrival_time.strftime('%Y-%m-%d %H:%M:%S')}")

            # Determine the status
            if current_time >= estimated_arrival_time:
                status = "Arrived"
                print("The ambulance has arrived at the destination.")

                # Update status to 'Arrived'
                cursor.execute(''' 
                    UPDATE ambulance_requests 
                    SET status = ?, arrival_time = ? 
                    WHERE id = ? 
                ''', (status, estimated_arrival_time.strftime("%Y-%m-%d %H:%M:%S"), ambulance_id))
            else:
                status = "In Transit"
                print("The ambulance is still in transit.")

                # Ensure 'Arrived' is not prematurely set
                cursor.execute(''' 
                    UPDATE ambulance_requests 
                    SET status = ? 
                    WHERE id = ? 
                ''', (status, ambulance_id))
            conn.commit()

    except Exception as e:
        print(f"Error checking arrival time: {e}")
    finally:
        conn.close()


# Initialize geocoder
geolocator = Nominatim(user_agent="ambulance_tracker")

def geocode_address(address, retries=3):
    """Geocode the given address to get latitude and longitude."""
    for attempt in range(retries):
        try:
            print(f"Geocoding address: {address} (Attempt {attempt + 1})")
            location = geolocator.geocode(address)
            if location:
                print(f"Geocoded Address: {address} => Latitude: {location.latitude}, Longitude: {location.longitude}")
                return location.latitude, location.longitude
            else:
                print(f"Address not found: {address}")
                return None, None
        except GeocoderTimedOut:
            print("Geocoding service timed out. Retrying...")
            time.sleep(2)  # Delay before retrying
    print("Geocoding failed after retries.")
    return None, None

def calculate_distance(lat1, lon1, lat2, lon2):
    # Use geodesic from geopy to calculate the distance in kilometers
    return geodesic((lat1, lon1), (lat2, lon2)).kilometers

@app.route('/tracking', methods=['GET', 'POST'])
def tracking():
    if request.method == 'POST':
        ambulance_id = request.form.get('ambulance_id')  # Try to get ambulance_id from the form
        patient_name = request.form.get('patient_name')  # Try to get patient_name from the form
        destination_address = request.form.get('destination')  # User-provided destination address

        # Debug print to check values
        print(f"Tracking request received with ambulance_id: {ambulance_id}, patient_name: {patient_name}, destination: {destination_address}")

        # Establish database connection
        try:
            conn = sqlite3.connect('users.db')
            cursor = conn.cursor()

            # Add print statements before executing the query to check the SQL query and input values
            if ambulance_id:
                print(f"Querying for ambulance with ID: {ambulance_id}")
                query = '''
                    SELECT al.latitude, al.longitude, al.timestamp, al.status, 
                        ar.patient_name, ar.pickup_lat, ar.pickup_lng, 
                        ar.destination_lat, ar.destination_lng, ar.request_time, ar.estimated_time_minutes
                    FROM ambulance_locations al
                    JOIN ambulance_requests ar ON al.ambulance_id = ar.id
                    WHERE al.ambulance_id = ?
                    ORDER BY al.timestamp DESC LIMIT 1
                '''
                print(f"Executing query: {query} with ambulance_id={ambulance_id}")
                cursor.execute(query, (ambulance_id,))

            elif patient_name:
                print(f"Searching for ambulance with Patient Name: {patient_name}")
                # If no ambulance_id, search by patient_name
                cursor.execute(''' 
                    SELECT al.latitude, al.longitude, al.timestamp, al.status, 
                           ar.patient_name, ar.pickup_lat, ar.pickup_lng, 
                           ar.destination_lat, ar.destination_lng, ar.request_time, ar.estimated_time_minutes
                    FROM ambulance_locations al 
                    JOIN ambulance_requests ar ON al.ambulance_id = ar.id 
                    WHERE ar.patient_name = ? 
                    ORDER BY al.timestamp DESC LIMIT 1
                ''', (patient_name,))
            else:
                flash("Please provide either an Ambulance ID or Patient Name.", "error")
                return redirect(url_for('tracking'))

            data = cursor.fetchone()

            # Debugging output
            print(f"Query result: {data}")

        except Exception as e:
            flash(f"Database error: {str(e)}", "error")
            return redirect(url_for('tracking'))

        finally:
            conn.close()

        # Check if data was found
        if data:
            latitude, longitude, timestamp, status, patient_name, pickup_lat, pickup_lng, destination_lat, destination_lng, request_time_str, estimated_time_minutes = data

            # Handle timestamp parsing
            try:
                timestamp = datetime.fromisoformat(timestamp)  # Convert string to datetime object
                if request_time_str:
                    request_time = datetime.fromisoformat(request_time_str)  # Convert request_time to datetime object
                else:
                    request_time = None  # Set request_time to None if the string is empty or None
            except ValueError as e:
                print(f"Error parsing timestamp: {e}")
                timestamp = None
                request_time = None

            # Debugging outputs for fetched data
            print(f"Fetched location: lat={latitude}, lon={longitude}, timestamp={timestamp}")
            print(f"Patient Name: {patient_name}, Status: {status}")
            print(f"Pickup coordinates: lat={pickup_lat}, lng={pickup_lng}")
            print(f"Destination coordinates: lat={destination_lat}, lng={destination_lng}")
            print(f"Request Time: {request_time}, Estimated Time: {estimated_time_minutes}")

            # If destination is not provided in the request, use the database values
            if destination_address:
                # Geocode the destination address provided by the user
                destination_lat, destination_lng = geocode_address(destination_address)
                if destination_lat is None or destination_lng is None:
                    flash("Invalid destination address provided.", "error")
                    return redirect(url_for('tracking'))
                else:
                    print(f"User-provided destination: {destination_address} => lat: {destination_lat}, lng: {destination_lng}")
            else:
                # If destination is already in the database, we can use the stored lat/lng
                print(f"Using destination from the database: lat={destination_lat}, lng={destination_lng}")

            # Use reverse_geocode for the pickup location
            if pickup_lat is None or pickup_lng is None:
                pickup_lat = latitude  # Assume pickup is at the current ambulance location
                pickup_lng = longitude

            pickup_address = reverse_geocode(pickup_lat, pickup_lng) if pickup_lat and pickup_lng else "Pickup location not available"
            if destination_lat and destination_lng:
                destination_address = reverse_geocode(destination_lat, destination_lng)
            else:
                destination_address = "Destination not available"


            # Debugging the reverse geocode addresses
            print(f"Pickup Address: {pickup_address}")
            print(f"Destination Address: {destination_address}")

            # Calculate the distance between pickup and destination
            distance_km = calculate_distance(pickup_lat, pickup_lng, destination_lat, destination_lng)
            print(f"Distance between Pickup and Destination: {distance_km} km")

            # Calculate estimated arrival time at 80 km/h speed
            estimated_time_minutes = (distance_km / 80) * 60  # ETA in minutes
            print(f"Estimated Arrival Time: {estimated_time_minutes} minutes")

            # Calculate the arrival time by subtracting estimated time from request time
            if request_time:
                arrival_time = request_time + timedelta(minutes=estimated_time_minutes)
                print(f"Calculated Arrival Time: {arrival_time}")

                # Format the arrival time to match "YYYY-MM-DD HH:MM:SS"
                formatted_arrival_time = arrival_time.strftime("%Y-%m-%d %H:%M:%S")
                print(f"Formatted Arrival Time: {formatted_arrival_time}")
                has_arrived = datetime.now() >= arrival_time
            else:
                formatted_arrival_time = None
                has_arrived = False

            return render_template('tracking_result.html',
                                patient_name=patient_name, status=status,
                                latitude=latitude, longitude=longitude,
                                timestamp=timestamp, estimated_time_minutes=estimated_time_minutes,
                                pickup_lat=pickup_lat, pickup_lng=pickup_lng,
                                pickup_address=pickup_address,
                                destination_lat=destination_lat, destination_lng=destination_lng,
                                destination_address=destination_address,
                                distance_km=distance_km, has_arrived=has_arrived,
                                arrival_time=formatted_arrival_time)

        else:
            flash("No ambulance found with that ID or name.", "error")
            return redirect(url_for('tracking'))

    # Render tracking form
    return render_template('tracking.html', title="Track Ambulance")


# Function to calculate real-time average speed
def calculate_realtime_average_speed(ambulance_id):
    # Fetch all location points for the given ambulance
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT latitude, longitude, timestamp
        FROM ambulance_locations
        WHERE ambulance_id = ?
        ORDER BY timestamp
    ''', (ambulance_id,))
    locations = cursor.fetchall()
    conn.close()

    if len(locations) < 2:
        print("Not enough data to calculate average speed.")
        return None

    total_distance = 0
    total_time = 0

    # Iterate over all location points to calculate total distance and time
    for i in range(1, len(locations)):
        lat1, lon1, timestamp1 = locations[i - 1]
        lat2, lon2, timestamp2 = locations[i]

        # Calculate distance between consecutive points using Haversine formula
        distance_km = geodesic((lat1, lon1), (lat2, lon2)).kilometers

        # Parse timestamps as datetime objects
        timestamp1 = datetime.fromtimestamp(timestamp1)
        timestamp2 = datetime.fromtimestamp(timestamp2)

        # Calculate time difference in hours
        time_diff_hours = (timestamp2 - timestamp1).total_seconds() / 3600

        if time_diff_hours > 0:
            total_distance += distance_km
            total_time += time_diff_hours

    # Calculate average speed in km/h
    if total_time > 0:
        average_speed_kmh = total_distance / total_time
        return round(average_speed_kmh, 2)
    else:
        return None

# SocketIO event to send real-time average speed
@socketio.on('request_average_speed')
def handle_request(ambulance_id):
    average_speed = calculate_realtime_average_speed(ambulance_id)
    emit('average_speed_update', {'average_speed': average_speed}, broadcast=True)


def calculate_current_speed(ambulance_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    cursor.execute('''SELECT latitude, longitude, timestamp
                      FROM ambulance_locations
                      WHERE ambulance_id = ?
                      ORDER BY timestamp DESC LIMIT 2''', (ambulance_id,))
    locations = cursor.fetchall()
    conn.close()

    if len(locations) < 2:
        return None

    lat1, lon1, timestamp1 = locations[0]
    lat2, lon2, timestamp2 = locations[1]

    # Calculate distance between the last two points
    distance_km = geodesic((lat1, lon1), (lat2, lon2)).kilometers

    # Calculate time difference in hours
    timestamp1 = datetime.fromtimestamp(timestamp1)
    timestamp2 = datetime.fromtimestamp(timestamp2)
    time_diff_hours = (timestamp2 - timestamp1).total_seconds() / 3600

    if time_diff_hours > 0:
        current_speed = distance_km / time_diff_hours
        return round(current_speed, 2)
    else:
        return None

# SocketIO event to request current speed
@socketio.on('request_current_speed')
def handle_request_current_speed(ambulance_id):
    current_speed = calculate_current_speed(ambulance_id)
    emit('current_speed_update', {'current_speed': current_speed}, broadcast=True)

@app.route('/get_latest_location/<int:ambulance_id>', methods=['GET'])
def get_latest_location(ambulance_id):
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()

        # Fetch the latest location, status, and additional data (pickup, destination)
        cursor.execute('''
            SELECT al.latitude, al.longitude, al.status, 
                   ar.patient_name, ar.pickup_lat, ar.pickup_lng, 
                   ar.destination_lat, ar.destination_lng
            FROM ambulance_locations al
            JOIN ambulance_requests ar ON al.ambulance_id = ar.id
            WHERE al.ambulance_id = ?
            ORDER BY al.timestamp DESC LIMIT 1
        ''', (ambulance_id,))

        data = cursor.fetchone()

        if data:
            latitude, longitude, status, patient_name, pickup_lat, pickup_lng, destination_lat, destination_lng = data
            return jsonify({
                'latitude': latitude,
                'longitude': longitude,
                'status': status,
                'patient_name': patient_name,
                'pickup_lat': pickup_lat,
                'pickup_lng': pickup_lng,
                'destination_lat': destination_lat,
                'destination_lng': destination_lng
            })
        else:
            return jsonify({'error': 'No location or status data available'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        conn.close()


@app.route('/update_location/<int:ambulance_id>', methods=['POST'])
def update_location(ambulance_id):
    try:
        # Connect to the database
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()

        # Get latitude and longitude from the form and convert to float
        latitude = float(request.form['latitude'])
        longitude = float(request.form['longitude'])

        # Check if the ambulance already has a recorded location
        cursor.execute('SELECT * FROM ambulance_locations WHERE ambulance_id = ?', (ambulance_id,))
        existing_location = cursor.fetchone()

        # Update or insert the ambulance location
        if existing_location:
            cursor.execute('''
                UPDATE ambulance_locations
                SET latitude = ?, longitude = ?
                WHERE ambulance_id = ?
            ''', (latitude, longitude, ambulance_id))
        else:
            cursor.execute('''
                INSERT INTO ambulance_locations (ambulance_id, latitude, longitude)
                VALUES (?, ?, ?)
            ''', (ambulance_id, latitude, longitude))

        # Commit the transaction
        conn.commit()

        # Flash success message and redirect to the appropriate page
        flash("Ambulance location updated", "success")
        return redirect(url_for('home'))  # Update to the correct endpoint if necessary

    except Exception as e:
        # Flash error message in case of failure
        flash(f"Error updating ambulance location: {str(e)}", "error")
        return redirect(url_for('home'))  # Update to the correct endpoint if necessary

    finally:
        # Ensure the connection is closed
        conn.close()

def reverse_geocode(lat, lng):
    url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lng}&key={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data['results']:
            address = data['results'][0]['formatted_address']
            return address
    return "Unknown Location"


# Terms of Service
@app.route('/terms_of_service')
def terms_of_service():
    return render_template('terms_of_service.html', title="Terms of Service")

# Privacy Policy
@app.route('/privacy_policy')
def privacy_policy():
    return render_template('privacy_policy.html', title="Privacy Policy")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001, ssl_context=('ssl/server.crt', 'ssl/server.key.new'))

# http request --> https 
