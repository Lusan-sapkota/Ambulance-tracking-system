const getLocationButton = document.getElementById('get-location');
const getHospitalsButton = document.getElementById('get-hospitals');
const searchRadiusElement = document.getElementById('search-radius');
const destinationSelect = document.getElementById('destination');
// Fetch user's location
getLocationButton.addEventListener('click', () => {
    if (!navigator.geolocation) {
        alert("Geolocation is not supported by your browser.");
        return;
    }

    getLocationButton.textContent = "Fetching location...";
    getLocationButton.disabled = true;

    // Set a longer timeout (30 seconds) and more detailed options for geolocation
    navigator.geolocation.getCurrentPosition(
        (position) => {
            const lat = position.coords.latitude;
            const lng = position.coords.longitude;
            document.getElementById('location').value = `Latitude: ${lat}, Longitude: ${lng}`;
            alert("Location retrieved successfully!");
            getLocationButton.textContent = "Enable Precise Location";
            getLocationButton.disabled = false;
        },
        (error) => {
            console.error("Geolocation error:", error);
            switch (error.code) {
                case error.PERMISSION_DENIED:
                    alert("Permission denied. Please allow location access.");
                    break;
                case error.POSITION_UNAVAILABLE:
                    alert("Location unavailable. Please check your GPS or internet connection.");
                    break;
                case error.TIMEOUT:
                    alert("Location request timed out. Please ensure that your device has a GPS signal and try again.");
                    break;
                case error.UNKNOWN_ERROR:
                    alert("An unknown error occurred while retrieving location. Please try again.");
                    break;
            }
            getLocationButton.textContent = "Enable Precise Location";
            getLocationButton.disabled = false;
        },
        {
            enableHighAccuracy: true,   // Ensure higher accuracy for location
            timeout: 30000,             // Increased timeout to 30 seconds
            maximumAge: 0               // Don't use cached positions
        }
    );
});

// Haversine formula to calculate the distance between two points (lat, lng) in km
function haversine(lat1, lng1, lat2, lng2) {
    const R = 6371; // Radius of the Earth in kilometers
    const dLat = (lat2 - lat1) * (Math.PI / 180);  // Convert degrees to radians
    const dLng = (lng2 - lng1) * (Math.PI / 180);  // Convert degrees to radians
    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
              Math.cos(lat1 * (Math.PI / 180)) * Math.cos(lat2 * (Math.PI / 180)) *
              Math.sin(dLng / 2) * Math.sin(dLng / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    const distance = R * c;  // Distance in kilometers
    return distance;
}


// Fetch hospitals based on location and radius
getHospitalsButton.addEventListener('click', () => {
    const location = document.getElementById('location').value;
    const radiusInKm = parseInt(searchRadiusElement.value, 10);  // Get radius in km
    const radiusInMeters = radiusInKm * 1;  // Convert km to meters

    if (!location) {
        alert("Please enable precise location first.");
        return;
    }

    const [lat, lng] = location.replace("Latitude: ", "").replace("Longitude: ", "").split(", ").map(val => parseFloat(val.trim()));

    if (isNaN(lat) || isNaN(lng)) {
        alert("Invalid location format. Please try again.");
        return;
    }

    console.log(`Fetching hospitals within a radius of ${radiusInMeters} meters...`);
    fetchHospitals(lat, lng, radiusInMeters);
});

// Fetch hospitals from the backend
function fetchHospitals(lat, lng, radius) {
    fetch(`/find_nearest_hospitals?lat=${lat}&lng=${lng}&radius=${radius}`)
        .then(response => response.json())
        .then(data => {
            console.log("Hospital data received:", data); // Log the received data

            destinationSelect.innerHTML = ''; // Clear the previous options

            const defaultOption = document.createElement('option');
            defaultOption.value = '';
            defaultOption.text = 'Choose a hospital';
            destinationSelect.appendChild(defaultOption);

            if (data.hospitals && data.hospitals.length > 0) {
                data.hospitals.forEach(hospital => {
                    const hospitalLat = hospital.latitude;
                    const hospitalLng = hospital.longitude;

                    if (isNaN(hospitalLat) || isNaN(hospitalLng)) {
                        console.error("Invalid hospital coordinates:", hospitalLat, hospitalLng);
                        return;  // Skip this hospital if coordinates are invalid or missing
                    }

                    const distance = haversine(lat, lng, hospitalLat, hospitalLng); // Calculate distance in km

                    const option = document.createElement('option');
                    option.value = hospital.name;
                    option.text = `${hospital.name} (${distance.toFixed(2)} km) - ${hospital.address}`;
                    destinationSelect.appendChild(option);

                    console.log(`Hospital: ${hospital.name}, Distance: ${distance.toFixed(2)} km`);
                });
                alert("Hospital list updated successfully!");
            } else {
                alert("No hospitals found within the selected radius.");
            }
        })
        .catch(error => {
            console.error("Error fetching hospitals:", error);
            alert("Failed to retrieve hospitals. Please try again.");
        });
}
