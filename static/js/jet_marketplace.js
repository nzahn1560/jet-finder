/**
 * Jet Finder Marketplace - Combined JavaScript
 * Handles integration between Jet Finder and Marketplace
 */

// Global variables
let jetMarketplaceLeafletMap;
let jetMarketplaceRangeCircle;
let jetMarketplaceMarker;
let selectedAirport = null;
let selectedFromAirport = null;
let selectedToAirport = null;
let rangeCirlceSegments = [];
let airportMarkers = {};
let airports = [];
let selectedHomeAirport = null;

// Trip planning class
class TripPlanning {
    constructor() {
        this.routes = [];
        this.init();
    }

    init() {
        this.bindEvents();
    }

    bindEvents() {
        // Add route button
        const addRouteBtn = document.getElementById('add-route-btn');
        if (addRouteBtn) {
            addRouteBtn.addEventListener('click', () => this.addRoute());
        }

        // Clear routes button
        const clearRoutesBtn = document.getElementById('clear-routes-btn');
        if (clearRoutesBtn) {
            clearRoutesBtn.addEventListener('click', () => this.clearAllRoutes());
        }

        // Search buttons
        this.bindAirportSearchEvents();
    }

    bindAirportSearchEvents() {
        // From airport search
        this.bindAirportSearch('from-airport', 'from-airport-results', 'from-airport-list');

        // To airport search
        this.bindAirportSearch('to-airport', 'to-airport-results', 'to-airport-list');

        // Home airport search
        this.bindAirportSearch('home-airport-search', 'home-airport-results', 'home-airport-list');
    }

    bindAirportSearch(inputId, resultsId, listId) {
        const input = document.getElementById(inputId);
        const results = document.getElementById(resultsId);
        const list = document.getElementById(listId);

        if (!input || !results || !list) return;

        let searchTimeout;

        input.addEventListener('input', () => {
            clearTimeout(searchTimeout);
            const query = input.value.trim();

            if (query.length < 2) {
                results.classList.add('d-none');
                return;
            }

            searchTimeout = setTimeout(() => {
                this.searchAirports(query, list, results, (airport) => {
                    input.value = `${airport.iata} - ${airport.name}`;
                    input.dataset.selected = JSON.stringify(airport);
                    results.classList.add('d-none');

                    // If this is home airport, update the map center
                    if (inputId === 'home-airport-search') {
                        this.updateHomeAirport(airport);
                    }
                });
            }, 300);
        });

        // Hide results when clicking outside
        document.addEventListener('click', (e) => {
            if (!input.contains(e.target) && !results.contains(e.target)) {
                results.classList.add('d-none');
            }
        });
    }

    async searchAirports(query, listElement, resultsElement, onSelect) {
        try {
            const response = await fetch(`/api/airports?q=${encodeURIComponent(query)}`);
            const airports = await response.json();

            listElement.innerHTML = '';

            if (airports.length === 0) {
                listElement.innerHTML = '<div class="list-group-item bg-dark text-white border-secondary">No airports found</div>';
            } else {
                airports.slice(0, 10).forEach(airport => {
                    const item = document.createElement('div');
                    item.className = 'list-group-item list-group-item-action bg-dark text-white border-secondary airport-result-item';
                    item.innerHTML = `
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <strong>${airport.iata}</strong> - ${airport.name}
                                <br><small class="text-muted">${airport.city}, ${airport.country}</small>
                            </div>
                            <span class="badge bg-secondary">${airport.size || 'N/A'}</span>
                        </div>
                    `;

                    item.addEventListener('click', () => {
                        onSelect(airport);
                    });

                    listElement.appendChild(item);
                });
            }

            resultsElement.classList.remove('d-none');
        } catch (error) {
            console.error('Error searching airports:', error);
            listElement.innerHTML = '<div class="list-group-item bg-dark text-white border-secondary text-danger">Error loading airports</div>';
            resultsElement.classList.remove('d-none');
        }
    }

    addRoute() {
        const fromInput = document.getElementById('from-airport');
        const toInput = document.getElementById('to-airport');

        const fromAirport = this.getSelectedAirport(fromInput);
        const toAirport = this.getSelectedAirport(toInput);

        if (!fromAirport || !toAirport) {
            console.error('Please select both departure and arrival airports');
            return;
        }

        if (fromAirport.iata === toAirport.iata) {
            console.error('Departure and arrival airports cannot be the same');
            return;
        }

        // Calculate distance
        const distance = this.calculateDistance(fromAirport, toAirport);

        // Create route object
        const route = {
            id: Date.now(),
            from: fromAirport,
            to: toAirport,
            distance: distance
        };

        // Add to routes array
        this.routes.push(route);

        // Update displays
        this.updateRoutesDisplay();
        this.updateMapWithRoutes();
        this.updateTotalDistance();
        this.notifyTripPlanningUpdate();

        // Clear inputs
        fromInput.value = '';
        toInput.value = '';
        delete fromInput.dataset.selected;
        delete toInput.dataset.selected;
    }

    getSelectedAirport(input) {
        try {
            return input.dataset.selected ? JSON.parse(input.dataset.selected) : null;
        } catch (e) {
            return null;
        }
    }

    calculateDistance(airport1, airport2) {
        // Haversine formula for calculating great circle distance
        const R = 3440.065; // Earth's radius in nautical miles
        const lat1 = airport1.lat * Math.PI / 180;
        const lat2 = airport2.lat * Math.PI / 180;
        const deltaLat = (airport2.lat - airport1.lat) * Math.PI / 180;
        const deltaLon = (airport2.lon - airport1.lon) * Math.PI / 180;

        const a = Math.sin(deltaLat / 2) * Math.sin(deltaLat / 2) +
            Math.cos(lat1) * Math.cos(lat2) *
            Math.sin(deltaLon / 2) * Math.sin(deltaLon / 2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

        return Math.round(R * c);
    }

    updateRoutesDisplay() {
        const container = document.getElementById('routes-container');
        const noRoutesMsg = document.getElementById('no-routes-message');
        const routesCount = document.getElementById('routes-count');

        if (!container) return;

        if (this.routes.length === 0) {
            if (noRoutesMsg) {
                noRoutesMsg.classList.remove('d-none');
                container.innerHTML = '';
                container.appendChild(noRoutesMsg);
            }
        } else {
            if (noRoutesMsg) {
                noRoutesMsg.classList.add('d-none');
            }
            container.innerHTML = this.routes.map(route => `
                <div class="route-item bg-secondary bg-opacity-25 rounded p-2 mb-2 d-flex justify-content-between align-items-center">
                    <div class="flex-grow-1">
                        <div class="fw-bold">${route.from.iata} → ${route.to.iata}</div>
                        <div class="small text-muted">
                            ${route.from.city} → ${route.to.city}
                            <span class="badge bg-primary ms-1">${route.distance.toLocaleString()} nm</span>
                        </div>
                    </div>
                    <button class="btn btn-sm btn-outline-danger ms-2" onclick="window.tripPlanning.removeRoute(${route.id})">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            `).join('');
        }

        if (routesCount) {
            routesCount.textContent = this.routes.length;
        }
    }

    removeRoute(routeId) {
        this.routes = this.routes.filter(route => route.id !== routeId);
        this.updateRoutesDisplay();
        this.updateMapWithRoutes();
        this.updateTotalDistance();
        this.notifyTripPlanningUpdate();
    }

    clearAllRoutes() {
        this.routes = [];
        this.updateRoutesDisplay();
        this.updateMapWithRoutes();
        this.updateTotalDistance();
        this.notifyTripPlanningUpdate();
    }

    updateTotalDistance() {
        const totalDistance = this.routes.reduce((sum, route) => sum + route.distance, 0);
        const totalDistanceElement = document.getElementById('total-distance');

        if (totalDistanceElement) {
            totalDistanceElement.textContent = `${totalDistance.toLocaleString()} nm`;
        }
    }

    updateMapWithRoutes() {
        // Implementation for updating map with routes
        if (this.routes.length > 0 && jetMarketplaceLeafletMap) {
            // Draw routes on map if needed
            console.log('Updating map with routes:', this.routes);
        }
    }

    updateHomeAirport(airport) {
        selectedHomeAirport = airport;
        if (jetMarketplaceLeafletMap) {
            jetMarketplaceLeafletMap.setView([airport.lat, airport.lon], 6);
            const rangeValue = document.getElementById('range-slider')?.value || 1000;
            drawRangeCircle(parseInt(rangeValue));
        }
    }

    notifyTripPlanningUpdate() {
        // Calculate trip planning metrics
        const longestLeg = this.routes.length > 0 ? Math.max(...this.routes.map(r => r.distance)) : 0;
        const totalDistance = this.routes.reduce((sum, route) => sum + route.distance, 0);
        const averageDistance = this.routes.length > 0 ? totalDistance / this.routes.length : 0;
        const tripCount = this.routes.length;

        // Store data globally for access
        window.tripPlanningData = {
            longestLeg,
            averageDistance,
            tripCount,
            totalDistance
        };

        // Dispatch event for aircraft analysis
        const event = new CustomEvent('tripPlanningUpdate', {
            detail: {
                longestLeg,
                averageDistance,
                tripCount,
                totalDistance
            }
        });

        window.dispatchEvent(event);
    }
}

document.addEventListener('DOMContentLoaded', function () {
    console.log('DOM fully loaded, initializing Jet Marketplace components...');

    // Initialize trip planning
    window.tripPlanning = new TripPlanning();

    // Initialize map right away
    console.log('Initializing map...');
    initMap();

    // Setup airport search for all inputs
    console.log('Setting up airport search...');
    setupAirportSearch('home-airport-search', 'home-airport-list', 'home-airport-results', 'search-home-btn');
    setupAirportSearch('from-airport', 'from-airport-list', 'from-airport-results', 'search-from-btn');
    setupAirportSearch('to-airport', 'to-airport-list', 'to-airport-results', 'search-to-btn');

    // Set up range slider event handler with marketplace filter integration
    const rangeSlider = document.getElementById('range-slider');
    if (rangeSlider) {
        // Update initial value to match any URL parameter
        const urlParams = new URLSearchParams(window.location.search);
        const minRange = urlParams.get('min_range');
        if (minRange) {
            rangeSlider.value = minRange;
            const rangeValueEl = document.getElementById('range-value');
            if (rangeValueEl) {
                rangeValueEl.textContent = minRange;
            }
            // Update range circle on map
            drawRangeCircle(parseInt(minRange));
        }

        rangeSlider.addEventListener('input', function () {
            const value = this.value;
            const rangeValueEl = document.getElementById('range-value');
            const rangeValue2El = document.getElementById('range-value-2');

            if (rangeValueEl) {
                rangeValueEl.textContent = value;
            }

            if (rangeValue2El) {
                rangeValue2El.textContent = value;
            }

            // Update range circle on map
            drawRangeCircle(parseInt(value));
        });

        // When slider is released (change event), apply filter to marketplace
        rangeSlider.addEventListener('change', function () {
            const value = this.value;
            // Update the URL parameter
            const currentUrl = new URL(window.location.href);
            currentUrl.searchParams.set('min_range', value);

            // Add visual feedback
            const rangeValueEl = document.getElementById('range-value');
            if (rangeValueEl) {
                rangeValueEl.classList.add('text-success');
                setTimeout(() => {
                    rangeValueEl.classList.remove('text-success');
                }, 1000);
            }

            // Reload page with new filter
            window.location.href = currentUrl.toString();
        });
    }

    // Initialize Add Route button
    const addRouteBtn = document.getElementById('add-route-btn');
    if (addRouteBtn) {
        addRouteBtn.addEventListener('click', function () {
            console.log('Add Route button clicked');
            const fromInput = document.getElementById('from-airport');
            const toInput = document.getElementById('to-airport');

            if (!fromInput || !toInput) {
                console.error('From or To airport input not found');
                return;
            }

            const from = fromInput.value.trim();
            const to = toInput.value.trim();

            if (!from || !to) {
                alert('Please select both origin and destination airports');
                return;
            }

            console.log(`Calculating route from ${from} to ${to}`);

            // Draw the route if we have the data
            if (selectedFromAirport && selectedToAirport) {
                const distance = haversineDistance(
                    selectedFromAirport.lat,
                    selectedFromAirport.lon,
                    selectedToAirport.lat,
                    selectedToAirport.lon
                );

                console.log(`Drawing route with distance: ${distance} NM`);
                drawRoute(from, to, Math.round(distance));

                // Update the marketplace filters with the calculated distance
                const currentUrl = new URL(window.location.href);
                currentUrl.searchParams.set('min_range', Math.round(distance));

                // Add visual feedback
                showToast('Route added! Filtering aircraft with sufficient range...');

                // Short delay before redirect
                setTimeout(() => {
                    window.location.href = currentUrl.toString();
                }, 1500);
            }
        });
    }
});

/**
 * Initialize the map
 */
function initMap() {
    console.log('Initializing map...');

    // Create map centered on Pacific Ocean to show both sides of date line
    jetMarketplaceLeafletMap = L.map('map', {
        center: [30, 0], // Center on the equator
        zoom: 2,
        // Enable standard wrapping behavior
        worldCopyJump: true,
        // Allow continuous navigation
        maxBounds: null,
        // Remove bounds restrictions
        maxBoundsViscosity: 0,
        // Critical: enable continuous world wrapping
        continuousWorld: true
    });

    // Create custom panes with specific z-index values for better layer control
    jetMarketplaceLeafletMap.createPane('rangeCirclePane');
    jetMarketplaceLeafletMap.createPane('aircraftCirclePane');
    jetMarketplaceLeafletMap.getPane('rangeCirclePane').style.zIndex = 200; // Base range circle behind
    jetMarketplaceLeafletMap.getPane('aircraftCirclePane').style.zIndex = 400;

    // Add dark basemap with proper wrapping configuration
    const darkBase = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 19,
        // Enable continuous world wrapping
        continuousWorld: true,
        // Critical: This must be false to enable wrapping
        noWrap: false,
        // Extend the bounds beyond normal limits to ensure full coverage
        bounds: [[-90, -540], [90, 540]]
    }).addTo(jetMarketplaceLeafletMap);

    // Add a second tile layer offset by 360 degrees to create seamless wrapping effect
    const wrappedDarkBase = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        subdomains: 'abcd',
        maxZoom: 19,
        // Enable continuous world wrapping
        continuousWorld: true,
        noWrap: false,
        // Shift this layer by 360 degrees
        bounds: [[-90, -180 - 360], [90, 180 - 360]]
    }).addTo(jetMarketplaceLeafletMap);

    // Add another tile layer offset in the opposite direction
    const wrappedDarkBase2 = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        subdomains: 'abcd',
        maxZoom: 19,
        // Enable continuous world wrapping
        continuousWorld: true,
        noWrap: false,
        // Shift this layer by 360 degrees in the opposite direction
        bounds: [[-90, -180 + 360], [90, 180 + 360]]
    }).addTo(jetMarketplaceLeafletMap);

    // Configure the map to handle panning across the date line
    jetMarketplaceLeafletMap.on('moveend', function () {
        // Normalize the center longitude when panning
        const center = jetMarketplaceLeafletMap.getCenter();
        // No need to force center adjustments - let Leaflet handle it naturally
    });

    // Add scale control
    L.control.scale({
        imperial: false,
        position: 'bottomleft'
    }).addTo(jetMarketplaceLeafletMap);

    // Add sample airports initially
    addSampleAirports();

    // Initialize range slider connection to map
    initRangeSlider();
}

/**
 * Initialize range slider behavior
 */
function initRangeSlider() {
    const rangeSlider = document.getElementById('range-slider');
    if (!rangeSlider) return;

    rangeSlider.addEventListener('input', function () {
        const rangeValue = parseInt(this.value);

        // Update display values
        const rangeValueEl = document.getElementById('range-value');
        const rangeValue2El = document.getElementById('range-value-2');

        if (rangeValueEl) rangeValueEl.textContent = rangeValue;
        if (rangeValue2El) rangeValue2El.textContent = rangeValue;

        // Update the range circle
        drawRangeCircle(rangeValue);
    });

    // Initialize with current value
    const initialRange = parseInt(rangeSlider.value);
    drawRangeCircle(initialRange);
}

/**
 * Add sample airports on the map for testing
 */
function addSampleAirports() {
    // Sample major US airports to show on map
    const sampleAirports = [
        { iata: 'SFO', name: 'San Francisco International', lat: 37.6213, lon: -122.3790 },
        { iata: 'LAX', name: 'Los Angeles International', lat: 33.9416, lon: -118.4085 },
        { iata: 'JFK', name: 'John F. Kennedy International', lat: 40.6413, lon: -73.7781 },
        { iata: 'ORD', name: 'Chicago O\'Hare International', lat: 41.9742, lon: -87.9073 },
        { iata: 'ATL', name: 'Hartsfield-Jackson Atlanta', lat: 33.6407, lon: -84.4277 },
        { iata: 'DFW', name: 'Dallas/Fort Worth International', lat: 32.8998, lon: -97.0403 },
        { iata: 'MIA', name: 'Miami International', lat: 25.7932, lon: -80.2906 },
        { iata: 'SEA', name: 'Seattle-Tacoma International', lat: 47.4502, lon: -122.3088 }
    ];

    console.log(`Adding ${sampleAirports.length} sample airports to map`);

    // Add each airport to the map
    sampleAirports.forEach(airport => {
        const airportIcon = L.divIcon({
            className: 'airport-marker',
            html: `<span>${airport.iata}</span>`,
            iconSize: [30, 30]
        });

        L.marker([airport.lat, airport.lon], { icon: airportIcon })
            .addTo(jetMarketplaceLeafletMap)
            .bindPopup(`<strong>${airport.iata}</strong><br>${airport.name}`);
    });
}

/**
 * Draw a geodesic range circle on the map
 */
function drawRangeCircle(rangeNM) {
    console.log(`Drawing range circle with radius: ${rangeNM} NM`);

    // Clear existing range circle
    if (jetMarketplaceRangeCircle) {
        jetMarketplaceLeafletMap.removeLayer(jetMarketplaceRangeCircle);
        jetMarketplaceRangeCircle = null;
    }

    if (rangeCirlceSegments.length > 0) {
        rangeCirlceSegments.forEach(segment => {
            if (segment) jetMarketplaceLeafletMap.removeLayer(segment);
        });
        rangeCirlceSegments = [];
    }

    // If no home airport selected, try to use a sample location
    let centerPoint;
    if (selectedHomeAirport) {
        centerPoint = L.latLng(selectedHomeAirport.lat, selectedHomeAirport.lon);
    } else {
        // Default to a sample location (New York)
        centerPoint = L.latLng(40.7128, -74.0060);
    }

    // Don't draw if range is zero
    if (rangeNM <= 0) return;

    // Generate points for a geodesic circle
    const circlePoints = createGeodesicCircle(centerPoint, rangeNM);

    // Check if the circle crosses the date line
    const splitPaths = splitCircleAtDateLine(circlePoints);

    // Get appropriate fill color based on range
    const fillColor = getColorForRange(rangeNM);

    // Create a polygon for each path segment
    splitPaths.forEach(path => {
        const segment = L.polygon(path, {
            color: fillColor,
            weight: 2,
            opacity: 0.8,
            fillColor: fillColor,
            fillOpacity: 0.1,
            pane: 'rangeCirclePane'
        }).addTo(jetMarketplaceLeafletMap);

        // Add tooltip
        segment.bindTooltip(`Range: ${rangeNM} NM`, {
            permanent: false,
            direction: 'center',
            className: 'range-tooltip'
        });

        rangeCirlceSegments.push(segment);
    });

    // If we have a home airport, add a marker
    if (selectedHomeAirport) {
        // Add or update airport marker
        addAirportMarker(selectedHomeAirport);

        // Fit map to the range circle
        const zoomLevel = getZoomForRadius(rangeNM);
        jetMarketplaceLeafletMap.setView(centerPoint, zoomLevel);
    }
}

/**
 * Create a geodesic circle
 */
function createGeodesicCircle(centerLatLng, radiusNM) {
    const points = [];
    const numPoints = 72; // Number of points to create a smooth circle

    for (let i = 0; i < numPoints; i++) {
        // Calculate bearing in degrees
        const bearing = (i * 360) / numPoints;

        // Calculate destination point
        const point = calculateDestinationPoint(
            centerLatLng.lat,
            centerLatLng.lng,
            bearing,
            radiusNM
        );

        points.push([point.lat, point.lng]);
    }

    // Close the circle
    points.push(points[0]);

    return points;
}

/**
 * Calculate a destination point given starting point, bearing and distance
 */
function calculateDestinationPoint(lat, lng, bearing, distance) {
    // Earth's radius in nautical miles
    const R = 3440.07; // Nautical miles

    // Convert to radians
    const lat1 = lat * Math.PI / 180;
    const lon1 = lng * Math.PI / 180;
    const brng = bearing * Math.PI / 180;

    // Calculate distance in radians
    const d = distance / R;

    // Calculate new latitude
    let lat2 = Math.asin(
        Math.sin(lat1) * Math.cos(d) +
        Math.cos(lat1) * Math.sin(d) * Math.cos(brng)
    );

    // Calculate new longitude
    let lon2 = lon1 + Math.atan2(
        Math.sin(brng) * Math.sin(d) * Math.cos(lat1),
        Math.cos(d) - Math.sin(lat1) * Math.sin(lat2)
    );

    // Normalize longitude to -180 to +180
    lon2 = ((lon2 + 3 * Math.PI) % (2 * Math.PI)) - Math.PI;

    return {
        lat: lat2 * 180 / Math.PI,
        lng: lon2 * 180 / Math.PI
    };
}

/**
 * Split a circle path at the date line
 */
function splitCircleAtDateLine(points) {
    const segments = [];
    let currentSegment = [];

    for (let i = 0; i < points.length; i++) {
        const current = points[i];
        const next = points[i + 1];

        currentSegment.push(current);

        if (next && i < points.length - 1) {
            // Check if this line segment crosses the date line
            const crossesDateLine = Math.abs(current[1] - next[1]) > 180;

            if (crossesDateLine) {
                // End current segment
                segments.push(currentSegment);

                // Start a new segment
                currentSegment = [];
            }
        }
    }

    // Add the last segment if it has points
    if (currentSegment.length > 0) {
        segments.push(currentSegment);
    }

    return segments;
}

/**
 * Get appropriate zoom level for given radius
 */
function getZoomForRadius(radius) {
    if (radius < 500) return 6;
    if (radius < 1000) return 5;
    if (radius < 2000) return 4;
    if (radius < 4000) return 3;
    return 2;
}

/**
 * Get color based on range value
 */
function getColorForRange(range) {
    // Gradient of colors from cool to warm based on range
    if (range < 1000) return '#4a5568'; // Dark gray blue
    if (range < 2000) return '#667eea'; // Indigo
    if (range < 3000) return '#9f7aea'; // Purple
    if (range < 4000) return '#ed64a6'; // Pink
    if (range < 5000) return '#f56565'; // Red
    if (range < 6000) return '#ed8936'; // Orange
    return '#ecc94b'; // Yellow
}

/**
 * Add airport marker to the map
 */
function addAirportMarker(airport) {
    // If we already have a marker for this airport, remove it
    if (airportMarkers[airport.iata || airport.icao]) {
        jetMarketplaceLeafletMap.removeLayer(airportMarkers[airport.iata || airport.icao]);
    }

    // Create custom icon
    const airportIcon = L.divIcon({
        className: 'custom-airport-icon',
        html: `<div class="airport-icon" style="width: 32px; height: 24px; font-size: 10px;">${airport.iata || airport.icao}</div>`,
        iconSize: [32, 24],
        iconAnchor: [16, 12]
    });

    // Create marker
    const marker = L.marker([airport.lat, airport.lon], {
        icon: airportIcon,
        title: airport.name
    }).addTo(jetMarketplaceLeafletMap);

    // Add popup
    marker.bindPopup(
        `<div class="airport-popup">
            <h6>${airport.name}</h6>
            <p><strong>${airport.iata || airport.icao}</strong><br>
            ${airport.city}, ${airport.country}</p>
        </div>`,
        { className: 'dark-popup' }
    );

    // Store in markers object
    airportMarkers[airport.iata || airport.icao] = marker;

    return marker;
}

/**
 * Draw route between airports
 */
function drawRoute(from, to, distance) {
    if (!jetMarketplaceLeafletMap) {
        console.error('Map not initialized for drawing route');
        return;
    }

    if (!selectedFromAirport || !selectedToAirport) {
        console.error('Missing from or to airport coordinates');
        return;
    }

    console.log(`Drawing geodesic route from ${from} to ${to} (${distance} NM)`);

    // Remove any existing routes
    jetMarketplaceLeafletMap.eachLayer(layer => {
        if (layer.options && layer.options.className === 'route-line') {
            jetMarketplaceLeafletMap.removeLayer(layer);
        }
    });

    // Create geodesic route line
    const fromLatLng = L.latLng(selectedFromAirport.lat, selectedFromAirport.lon);
    const toLatLng = L.latLng(selectedToAirport.lat, selectedToAirport.lon);

    // Generate great circle path points
    const pathPoints = generateGreatCirclePath(fromLatLng, toLatLng, 100);

    // Check if path crosses date line and handle accordingly
    const routeSegments = splitPathAtDateLine(pathPoints);

    // Create a line for each segment
    routeSegments.forEach(segment => {
        const routeLine = L.polyline(segment, {
            color: '#F05545',
            weight: 3,
            opacity: 0.8,
            dashArray: '5, 10',
            className: 'route-line',
            animate: true
        }).addTo(jetMarketplaceLeafletMap);
    });

    // Add markers for the endpoints with custom icons
    addAirportMarker(selectedFromAirport);
    addAirportMarker(selectedToAirport);

    // Add route information popup to the middle of the route
    const midIndex = Math.floor(pathPoints.length / 2);
    if (midIndex < pathPoints.length) {
        const midPoint = pathPoints[midIndex];

        L.popup({
            className: 'route-popup',
            closeButton: false,
            autoClose: false,
            closeOnEscapeKey: false,
            closeOnClick: false
        })
            .setLatLng(midPoint)
            .setContent(`
            <div class="text-center">
                <strong>${selectedFromAirport.iata} → ${selectedToAirport.iata}</strong><br>
                <span class="text-danger">${distance} NM</span>
            </div>
        `)
            .openOn(jetMarketplaceLeafletMap);
    }

    // Fit map to show the entire route with padding
    const bounds = L.latLngBounds(
        [selectedFromAirport.lat, selectedFromAirport.lon],
        [selectedToAirport.lat, selectedToAirport.lon]
    ).pad(0.3); // Add 30% padding

    jetMarketplaceLeafletMap.fitBounds(bounds);

    console.log(`Route drawn from ${selectedFromAirport.lat},${selectedFromAirport.lon} to ${selectedToAirport.lat},${selectedToAirport.lon}`);

    // Display distance in UI elements if they exist
    const distanceDisplay = document.getElementById('route-distance');
    if (distanceDisplay) {
        distanceDisplay.textContent = `${distance} NM`;
    }

    // If range slider exists, update it with the calculated distance
    const rangeSlider = document.getElementById('range-slider');
    const rangeValue = document.getElementById('range-value');
    if (rangeSlider && rangeValue) {
        rangeSlider.value = distance;
        rangeValue.textContent = distance;

        // Update range circle to match route distance
        drawRangeCircle(distance);
    }
}

/**
 * Setup airport search functionality
 */
function setupAirportSearch(inputId, resultListId, resultsContainerId, searchBtnId) {
    const input = document.getElementById(inputId);
    const resultsList = document.getElementById(resultListId);
    const resultsContainer = document.getElementById(resultsContainerId);
    const searchBtn = document.getElementById(searchBtnId);

    if (!input || !resultsList || !resultsContainer || !searchBtn) {
        console.error(`Missing elements for airport search ${inputId}`);
        return;
    }

    console.log(`Setting up airport search for ${inputId}`);

    // Setup search functionality
    input.addEventListener('input', function () {
        const query = this.value.trim().toLowerCase();
        if (query.length < 2) {
            resultsContainer.classList.add('d-none');
            return;
        }

        // Show loading state
        resultsList.innerHTML = '<div class="list-group-item bg-dark text-white">Searching...</div>';
        resultsContainer.classList.remove('d-none');

        // Fetch airports from API
        console.log(`Searching airports with query: ${query}`);
        fetch(`/api/airports?q=${encodeURIComponent(query)}`)
            .then(response => response.json())
            .then(airports => {
                console.log(`Found ${airports.length} airports matching "${query}"`);
                resultsList.innerHTML = '';

                if (airports.length === 0) {
                    resultsList.innerHTML = '<div class="list-group-item bg-dark text-white">No airports found</div>';
                    return;
                }

                // Sort airports by relevance and size
                airports.sort((a, b) => {
                    // First sort by exact match on IATA code
                    const aMatchesIATA = a.iata && a.iata.toLowerCase() === query.toLowerCase();
                    const bMatchesIATA = b.iata && b.iata.toLowerCase() === query.toLowerCase();

                    if (aMatchesIATA && !bMatchesIATA) return -1;
                    if (!aMatchesIATA && bMatchesIATA) return 1;

                    // Then sort by size (L > M > S)
                    const aSize = a.size || 'Z';
                    const bSize = b.size || 'Z';

                    if (aSize < bSize) return -1; // 'L' comes before 'M' alphabetically
                    if (aSize > bSize) return 1;

                    // Finally sort by name
                    return (a.name || '').localeCompare(b.name || '');
                });

                // Display airports (limit to 10 for performance)
                const airportsToShow = airports.slice(0, 10);

                airportsToShow.forEach(airport => {
                    const item = document.createElement('button');
                    item.type = 'button';
                    item.className = 'list-group-item list-group-item-action bg-dark text-white border-secondary';
                    item.innerHTML = `
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                ${airport.iata ? `<strong class="me-2">${airport.iata}</strong>` : ''}
                                ${airport.icao ? `<span class="text-danger">${airport.icao}</span>` : ''}
                            </div>
                            ${airport.size ? `<span class="badge bg-danger">${airport.size}</span>` : ''}
                        </div>
                        <div class="text-truncate">${airport.name}</div>
                        <small class="text-secondary text-truncate d-block">${airport.city}, ${airport.country}</small>
                    `;

                    item.addEventListener('click', function () {
                        input.value = `${airport.iata} - ${airport.name}`;
                        resultsContainer.classList.add('d-none');

                        handleAirportSelection(airport, inputId);
                    });

                    resultsList.appendChild(item);
                });
            })
            .catch(error => {
                console.error('Error searching airports:', error);
                resultsList.innerHTML = `<div class="list-group-item bg-dark text-white">Error searching airports</div>`;
            });
    });

    // Search button click handler
    searchBtn.addEventListener('click', function () {
        const query = input.value.trim();
        if (query.length < 2) return;

        // Just trigger the input event to show results
        input.dispatchEvent(new Event('input'));
    });

    // Close results when clicking outside
    document.addEventListener('click', function (e) {
        if (!resultsContainer.contains(e.target) && e.target !== input && e.target !== searchBtn) {
            resultsContainer.classList.add('d-none');
        }
    });
}

/**
 * Handle airport selection for different inputs
 */
function handleAirportSelection(airport, inputId) {
    // Store the selected airport based on which input was used
    if (inputId === 'home-airport-search') {
        selectedHomeAirport = airport;
        console.log('Set selectedHomeAirport:', selectedHomeAirport);

        // Center map on selected airport
        if (jetMarketplaceLeafletMap) {
            jetMarketplaceLeafletMap.setView([airport.lat, airport.lon], 6);

            // Update the range circle
            const rangeValue = document.getElementById('range-slider')?.value || 1000;
            drawRangeCircle(parseInt(rangeValue));
        }
    } else if (inputId === 'from-airport') {
        selectedFromAirport = airport;
        console.log('Set selectedFromAirport:', selectedFromAirport);

        // Add marker on the map
        if (jetMarketplaceLeafletMap) {
            addAirportMarker(airport);
        }
    } else if (inputId === 'to-airport') {
        selectedToAirport = airport;
        console.log('Set selectedToAirport:', selectedToAirport);

        // Add marker on the map
        if (jetMarketplaceLeafletMap) {
            addAirportMarker(airport);
        }
    }

    // If we have both from and to airports, calculate distance
    if (selectedFromAirport && selectedToAirport && jetMarketplaceLeafletMap) {
        const distance = haversineDistance(
            selectedFromAirport.lat,
            selectedFromAirport.lon,
            selectedToAirport.lat,
            selectedToAirport.lon
        );

        console.log(`Calculated distance: ${distance} NM`);
    }
}

/**
 * Generate points along a great circle path between two points
 */
function generateGreatCirclePath(from, to, numPoints = 100) {
    const points = [];

    for (let i = 0; i <= numPoints; i++) {
        const fraction = i / numPoints;
        const point = intermediatePoint(
            from.lat, from.lng,
            to.lat, to.lng,
            fraction
        );
        points.push(L.latLng(point.lat, point.lng));
    }

    return points;
}

/**
 * Calculate intermediate point along great circle path
 */
function intermediatePoint(lat1, lng1, lat2, lng2, fraction) {
    // Convert to radians
    const φ1 = lat1 * Math.PI / 180;
    const λ1 = lng1 * Math.PI / 180;
    const φ2 = lat2 * Math.PI / 180;
    const λ2 = lng2 * Math.PI / 180;

    // Calculate distance (d)
    const d = 2 * Math.asin(
        Math.sqrt(
            Math.sin((φ2 - φ1) / 2) * Math.sin((φ2 - φ1) / 2) +
            Math.cos(φ1) * Math.cos(φ2) * Math.sin((λ2 - λ1) / 2) * Math.sin((λ2 - λ1) / 2)
        )
    );

    // If points are antipodal (opposite sides of earth), return a default route via the North Pole
    if (Math.abs(d - Math.PI) < 1e-10) {
        return { lat: 90, lng: (lng1 + lng2) / 2 };
    }

    // Formula for intermediate point
    const a = Math.sin((1 - fraction) * d) / Math.sin(d);
    const b = Math.sin(fraction * d) / Math.sin(d);

    const x = a * Math.cos(φ1) * Math.cos(λ1) + b * Math.cos(φ2) * Math.cos(λ2);
    const y = a * Math.cos(φ1) * Math.sin(λ1) + b * Math.cos(φ2) * Math.sin(λ2);
    const z = a * Math.sin(φ1) + b * Math.sin(φ2);

    const φ3 = Math.atan2(z, Math.sqrt(x * x + y * y));
    const λ3 = Math.atan2(y, x);

    // Convert back to degrees
    return {
        lat: φ3 * 180 / Math.PI,
        lng: ((λ3 * 180 / Math.PI) + 540) % 360 - 180 // Normalize to -180 to +180
    };
}

/**
 * Split path at international date line
 */
function splitPathAtDateLine(points) {
    const segments = [];
    let currentSegment = [];

    for (let i = 0; i < points.length; i++) {
        const currentPoint = points[i];
        currentSegment.push(currentPoint);

        // Check if we need to start a new segment (date line crossing)
        if (i < points.length - 1) {
            const nextPoint = points[i + 1];

            // Check for date line crossing (longitude difference > 180 degrees)
            if (Math.abs(nextPoint.lng - currentPoint.lng) > 180) {
                // End current segment
                segments.push([...currentSegment]);

                // Start new segment
                currentSegment = [];
            }
        }
    }

    // Add the last segment if not empty
    if (currentSegment.length > 0) {
        segments.push(currentSegment);
    }

    // If no date line crossing, return the original points
    if (segments.length === 0) {
        segments.push(points);
    }

    return segments;
}

/**
 * Function to calculate the Haversine distance between two points
 */
function haversineDistance(lat1, lon1, lat2, lon2) {
    // Convert degrees to radians
    const toRad = (deg) => deg * Math.PI / 180;

    // Get latitude and longitude in radians
    const rlat1 = toRad(lat1);
    const rlon1 = toRad(lon1);
    const rlat2 = toRad(lat2);
    const rlon2 = toRad(lon2);

    // Calculate differences
    const dlat = rlat2 - rlat1;
    const dlon = rlon2 - rlon1;

    // Haversine formula
    const a = Math.sin(dlat / 2) * Math.sin(dlat / 2) +
        Math.cos(rlat1) * Math.cos(rlat2) *
        Math.sin(dlon / 2) * Math.sin(dlon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

    // Radius of Earth in nautical miles
    const R = 3440; // nautical miles

    // Calculate distance
    return R * c;
}

/**
 * Show aircraft range on the map
 */
window.showAircraftRange = function (range, aircraftId) {
    console.log(`Showing range for aircraft ID ${aircraftId}: ${range} NM`);

    // Draw the range circle
    drawRangeCircle(range);

    // Update the range slider
    const rangeSlider = document.getElementById('range-slider');
    if (rangeSlider) {
        rangeSlider.value = range;
        const rangeValueEl = document.getElementById('range-value');
        if (rangeValueEl) {
            rangeValueEl.textContent = range;
        }
        const rangeValue2El = document.getElementById('range-value-2');
        if (rangeValue2El) {
            rangeValue2El.textContent = range;
        }
    }

    // Highlight the selected aircraft card
    document.querySelectorAll('.aircraft-card').forEach(card => {
        card.classList.remove('border-danger');
        card.classList.add('border-secondary');

        if (card.dataset.id === aircraftId) {
            card.classList.remove('border-secondary');
            card.classList.add('border-danger');
            card.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    });
}

/**
 * Show a toast notification
 */
function showToast(message) {
    console.log('Toast:', message);

    // Create a Bootstrap toast
    const toastContainer = document.createElement('div');
    toastContainer.className = 'position-fixed bottom-0 end-0 p-3';
    toastContainer.style.zIndex = '5';

    const toastEl = document.createElement('div');
    toastEl.className = 'toast';
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');

    toastEl.innerHTML = `
        <div class="toast-header bg-dark text-white">
            <strong class="me-auto">Jet Finder</strong>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body bg-dark text-white">
            ${message}
        </div>
    `;

    toastContainer.appendChild(toastEl);
    document.body.appendChild(toastContainer);

    // Initialize and show the toast
    const toast = new bootstrap.Toast(toastEl, {
        delay: 3000
    });
    toast.show();

    // Remove the element when hidden
    toastEl.addEventListener('hidden.bs.toast', function () {
        toastContainer.remove();
    });
} 