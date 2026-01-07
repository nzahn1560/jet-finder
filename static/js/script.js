// Jet Finder JavaScript

// Global variables
let map;
let circle;
let marker;
let geocoder;
let aircraftData = [];
let selectedAircraft = new Set();
let activePriorityColumn = 'as';
let activeFilters = {};
let routeMarkers = [];
let routeLegs = [];
let totalDistance = 0;
let selectedAirport = null;
let selectedFromAirport = null;
let selectedToAirport = null;
let rangeMode = 'average'; // 'average' or 'full'
let routePairs = [];
let allRouteLines = new Map();
let aircraftRangeCircles = new Map();
let homeAirport = null;
let rangeCircle = null;
let avgTripRangeCircle = null;
let longestLegRangeCircle = null;
let currentRange = 500;
let longestLegDistance = 0;
let averageTripDistance = 0;
let airportMarkers = {};
let rangeCirlceSegments = [];
let customRangePolygons = [];
let avgTripRangePolygons = [];
let longestLegRangePolygons = [];
let airports = [];

// Make key variables and functions available globally for restoration
window.routePairs = routePairs;
window.allRouteLines = allRouteLines;
window.homeAirport = homeAirport;
window.longestLegDistance = longestLegDistance;
window.averageTripDistance = averageTripDistance;
window.currentRange = currentRange;

// Debounce function to limit function calls
function debounce(func, wait) {
    let timeout;
    return function (...args) {
        const context = this;
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(context, args), wait);
    };
}

// Handle map move end event with debouncing
const handleMapMoveEnd = debounce(function () {
    const zoom = map.getZoom();
    const bounds = map.getBounds();

    if (!bounds) return;

    // Only update airport markers if we're at a zoom level where it makes sense
    if (zoom >= 5) {
        updateVisibleAirports();
    } else {
        // Hide all airport markers when zoomed out too far
        hideAllAirportMarkers();
    }

    // Save the current view to localStorage
    const center = map.getCenter();
    localStorage.setItem('mapCenter', JSON.stringify({
        lat: center.lat,
        lng: center.lng,
        zoom: zoom
    }));
}, 300); // 300ms debounce time

// Initialize the map
function initMap() {
    console.log('Initializing map...');

    // Create map centered on Pacific Ocean to show both sides of date line
    map = L.map('map', {
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

    // Expose map to window
    window.map = map;

    // Create custom panes with specific z-index values for better layer control
    map.createPane('rangeCirclePane');
    map.createPane('aircraftCirclePane');
    map.getPane('rangeCirclePane').style.zIndex = 200; // Base range circle behind
    map.getPane('aircraftCirclePane').style.zIndex = 400;

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
    }).addTo(map);

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
    }).addTo(map);

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
    }).addTo(map);

    // Configure the map to handle panning across the date line
    map.on('moveend', function () {
        // Normalize the center longitude when panning
        const center = map.getCenter();
        // No need to force center adjustments - let Leaflet handle it naturally
    });

    // Add scale control
    L.control.scale({
        imperial: false,
        position: 'bottomleft'
    }).addTo(map);

    // Set up event listener for map move end
    map.on('moveend', debounce(handleMapMoveEnd, 300));

    // Set up clicks on map to clear any selected airports
    map.on('click', function (e) {
        // Only clear if clicking on the map, not on markers or other overlays
        if (e.originalEvent.target === map._container ||
            e.originalEvent.target.classList.contains('leaflet-container')) {
            // Clear any selected airports
            selectedFromAirport = null;
            selectedToAirport = null;

            // Clear input fields
            const fromAirportInput = document.getElementById('from-airport');
            const toAirportInput = document.getElementById('to-airport');

            if (fromAirportInput) fromAirportInput.value = '';
            if (toAirportInput) toAirportInput.value = '';

            // Hide all dropdowns
            const homeResults = document.getElementById('home-airport-results');
            const fromResults = document.getElementById('from-airport-results');
            const toResults = document.getElementById('to-airport-results');

            if (homeResults) homeResults.classList.add('d-none');
            if (fromResults) fromResults.classList.add('d-none');
            if (toResults) toResults.classList.add('d-none');
        }
    });

    // Initialize airport search
    setupAirportSearchEventListeners();

    // Load all aircraft ranges and create circles
    loadAircraftRanges();
}

// Search for airports for home airport selection
function searchHomeAirport(query, resultsList, resultsContainer) {
    console.log('searchHomeAirport called with:', query, 'resultsList:', !!resultsList, 'resultsContainer:', !!resultsContainer);

    if (!query.trim()) {
        resultsContainer.classList.add('d-none');
        console.log('Query empty, hiding results container');
        return;
    }

    resultsList.innerHTML = '<div class="list-group-item bg-dark text-white">Searching...</div>';
    resultsContainer.classList.remove('d-none');
    console.log('Showing results container, removed d-none class');

    fetch(`/api/airports?q=${encodeURIComponent(query)}`)
        .then(response => {
            console.log('API response status:', response.status);
            return response.json();
        })
        .then(airports => {
            console.log('Received airports:', airports.length);
            resultsList.innerHTML = '';

            if (airports.length === 0) {
                resultsList.innerHTML = '<div class="list-group-item bg-dark text-white">No airports found</div>';
                console.log('No airports found, showing message');
                return;
            }

            console.log('Adding airports to dropdown...');
            airports.forEach((airport, index) => {
                const item = document.createElement('button');
                item.type = 'button';
                item.className = 'list-group-item list-group-item-action bg-dark text-white border-secondary';
                item.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            ${airport.iata ? `<strong class="me-2">${airport.iata}</strong>` : ''}
                            ${airport.icao ? `<span class="text-info">${airport.icao}</span>` : ''}
                        </div>
                        ${airport.size ? `<span class="badge bg-danger">${airport.size}</span>` : ''}
                    </div>
                    <div class="text-truncate">${airport.name}</div>
                    <small class="text-secondary text-truncate d-block">${airport.city}, ${airport.country}</small>
                `;

                item.addEventListener('click', function (e) {
                    e.preventDefault();
                    e.stopPropagation();
                    console.log('Airport selected:', airport.iata);
                    setHomeAirport(airport);
                    document.getElementById('home-airport-search').value = `${airport.iata} - ${airport.city}`;
                    resultsContainer.classList.add('d-none');
                });

                resultsList.appendChild(item);
                console.log(`Added airport ${index + 1}:`, airport.iata);
            });
            console.log('All airports added to dropdown');
        })
        .catch(error => {
            console.error('Error searching home airports:', error);
            resultsList.innerHTML = '<div class="list-group-item bg-dark text-white">Error searching airports</div>';
        });
}

// Get color based on range
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

// Function to load aircraft ranges from the API and display them on the map
function loadAircraftRanges() {
    // Instead of loading aircraft circles, we now create the three range rings
    if (!homeAirport) {
        console.log('No home airport set, cannot create range rings');
        return;
    }

    console.log('Creating range rings for home airport');
    updateRangeRings();
}

// Function to update the range rings
function updateRangeRings() {
    // Clear existing range circles
    if (rangeCircle) {
        map.removeLayer(rangeCircle);
        rangeCircle = null;
    }
    if (customRangePolygons) {
        customRangePolygons.forEach(polygon => map.removeLayer(polygon));
        customRangePolygons = [];
    }
    if (avgTripRangeCircle) {
        map.removeLayer(avgTripRangeCircle);
        avgTripRangeCircle = null;
    }
    if (avgTripRangePolygons) {
        avgTripRangePolygons.forEach(polygon => map.removeLayer(polygon));
        avgTripRangePolygons = [];
    }
    if (longestLegRangeCircle) {
        map.removeLayer(longestLegRangeCircle);
        longestLegRangeCircle = null;
    }
    if (longestLegRangePolygons) {
        longestLegRangePolygons.forEach(polygon => map.removeLayer(polygon));
        longestLegRangePolygons = [];
    }

    // Check if home airport is set
    if (!homeAirport) {
        console.log('No home airport set, cannot create range rings');
        return;
    }

    // Get current ranges
    const customRange = parseInt(document.getElementById('range-slider').value) || 500;
    currentRange = customRange;

    // Recalculate metrics from route pairs
    if (routePairs.length > 0) {
        // Find the longest leg distance
        longestLegDistance = Math.max(...routePairs.map(route => route.distance));

        // Calculate total trips and weighted average
        const totalTrips = routePairs.reduce((sum, route) => sum + route.frequency, 0);
        let totalWeightedDistance = 0;
        routePairs.forEach(route => {
            totalWeightedDistance += route.distance * route.frequency;
        });

        averageTripDistance = totalTrips > 0 ? Math.round(totalWeightedDistance / totalTrips) : 0;

        console.log(`Range ring metrics - Custom: ${customRange}, Average: ${averageTripDistance}, Longest: ${longestLegDistance}`);
    } else {
        longestLegDistance = 0;
        averageTripDistance = 0;
    }

    // Create custom range ring (red) - always show this one
    if (customRange > 0) {
        const customRangeInfo = createGeodesicCircle([homeAirport.lat, homeAirport.lon], customRange);
        createRangeDisplay(customRangeInfo, customRange, '#F05545', 'Custom Range', customRangePolygons);
    }

    // Create average trip range ring (white) if we have route data
    if (averageTripDistance > 0 && averageTripDistance !== customRange) {
        const avgRangeInfo = createGeodesicCircle([homeAirport.lat, homeAirport.lon], averageTripDistance);
        createRangeDisplay(avgRangeInfo, averageTripDistance, '#FFFFFF', 'Average Trip', avgTripRangePolygons);
    }

    // Create longest leg range ring (blue) if we have route data
    if (longestLegDistance > 0 && longestLegDistance !== customRange && longestLegDistance !== averageTripDistance) {
        const longestLegInfo = createGeodesicCircle([homeAirport.lat, homeAirport.lon], longestLegDistance);
        createRangeDisplay(longestLegInfo, longestLegDistance, '#3498DB', 'Longest Leg', longestLegRangePolygons);
    }

    // Add range legend
    addRangeLegend();
}

// Helper function to create range display (circle or polygon)
function createRangeDisplay(rangeInfo, distance, color, label, polygonArray) {
    if (distance > 3400) {
        // For very large ranges, use simple lines instead of polygons
        if (rangeInfo.isDateLineCrossing) {
            // Create polylines with proper date line handling
            const segments = [];
            let currentSegment = [];

            // Start with the first point
            currentSegment.push([...rangeInfo.points[0]]);

            // Process all points and create new segments when crossing the date line
            for (let i = 1; i < rangeInfo.points.length; i++) {
                const prevPt = rangeInfo.points[i - 1];
                const pt = rangeInfo.points[i];

                // If we cross the date line, end current segment and start a new one
                if (Math.abs(prevPt[1] - pt[1]) > 180) {
                    // Calculate the exact latitude where the line crosses the date line
                    const ratio = Math.abs(180 - Math.abs(prevPt[1])) / Math.abs(prevPt[1] - pt[1]);
                    const crossingLat = prevPt[0] + ratio * (pt[0] - prevPt[0]);

                    // Add crossing point to current segment
                    if (prevPt[1] >= 0) { // Moving from east to west
                        currentSegment.push([crossingLat, 180]);
                    } else { // Moving from west to east
                        currentSegment.push([crossingLat, -180]);
                    }

                    // Save current segment and start a new one
                    if (currentSegment.length > 1) {
                        segments.push([...currentSegment]);
                    }

                    // Start new segment with the crossing point on the other side
                    currentSegment = [];
                    if (prevPt[1] >= 0) { // Moving from east to west
                        currentSegment.push([crossingLat, -180]);
                    } else { // Moving from west to east
                        currentSegment.push([crossingLat, 180]);
                    }
                }

                // Add the current point to the current segment
                currentSegment.push([...pt]);
            }

            // Add the last segment if it has points
            if (currentSegment.length > 1) {
                segments.push(currentSegment);
            }

            // Create polylines for each segment
            segments.forEach((segment, index) => {
                const polyline = L.polyline(segment, {
                    color: color,
                    weight: 2,
                    dashArray: '5, 5',
                    pane: 'rangeCirclePane'
                }).addTo(map);

                polygonArray.push(polyline);

                // Add tooltip to the first segment
                if (index === 0) {
                    polyline.bindTooltip(`${label}: ${Math.round(distance)} nm`, {
                        permanent: false,
                        direction: 'top',
                        className: 'range-tooltip'
                    });
                }
            });
        } else {
            // Create a regular polyline if it doesn't cross the date line
            const rangeLine = L.polyline(rangeInfo.points, {
                color: color,
                weight: 2,
                dashArray: '5, 5',
                pane: 'rangeCirclePane'
            }).addTo(map);

            polygonArray.push(rangeLine);

            rangeLine.bindTooltip(`${label}: ${Math.round(distance)} nm`, {
                permanent: false,
                direction: 'top',
                className: 'range-tooltip'
            });
        }
    } else if (rangeInfo.isDateLineCrossing) {
        // Create two polygons for date line crossing
        // Eastern hemisphere polygon
        const eastPolygon = L.polygon(rangeInfo.eastPolygon, {
            color: color,
            weight: 2,
            fillColor: color,
            fillOpacity: 0.05,
            dashArray: '5, 5',
            pane: 'rangeCirclePane'
        }).addTo(map);

        // Western hemisphere polygon
        const westPolygon = L.polygon(rangeInfo.westPolygon, {
            color: color,
            weight: 2,
            fillColor: color,
            fillOpacity: 0.05,
            dashArray: '5, 5',
            pane: 'rangeCirclePane'
        }).addTo(map);

        polygonArray.push(eastPolygon, westPolygon);

        // Add tooltip to the first polygon
        eastPolygon.bindTooltip(`${label}: ${Math.round(distance)} nm`, {
            permanent: false,
            direction: 'top',
            className: 'range-tooltip'
        });
    } else {
        // Create a regular circle if it doesn't cross the date line
        const circle = L.circle(rangeInfo.center, {
            radius: rangeInfo.radius,
            color: color,
            weight: 2,
            fillColor: color,
            fillOpacity: 0.05,
            dashArray: '5, 5',
            pane: 'rangeCirclePane'
        }).addTo(map);

        // Store circle reference based on type
        if (color === '#F05545') {
            rangeCircle = circle;
        } else if (color === '#FFFFFF') {
            avgTripRangeCircle = circle;
        } else if (color === '#3498DB') {
            longestLegRangeCircle = circle;
        }

        circle.bindTooltip(`${label}: ${Math.round(distance)} nm`, {
            permanent: false,
            direction: 'top',
            className: 'range-tooltip'
        });
    }
}

// Create a simple circle with radius in nautical miles
function createGeodesicCircle(centerLatLng, radiusNM) {
    // Convert from nautical miles to meters (Leaflet uses meters)
    const radiusMeters = radiusNM * 1852; // 1 NM = 1852 meters

    // For geodesic circle, calculate points around the circumference
    const numPoints = 144; // More points for smoother circle (every 2.5 degrees)
    const points = [];

    // Invalid inputs check
    if (!centerLatLng || !Array.isArray(centerLatLng) || centerLatLng.length !== 2 ||
        isNaN(centerLatLng[0]) || isNaN(centerLatLng[1]) || isNaN(radiusNM) || radiusNM <= 0) {
        console.error("Invalid parameters for geodesic circle", centerLatLng, radiusNM);
        return { center: centerLatLng, radius: radiusMeters };
    }

    const [lat, lng] = centerLatLng;

    // Earth's radius in meters
    const earthRadius = 6371000; // meters

    // Angular radius (in radians)
    const angularRadius = radiusMeters / earthRadius;

    // For each point around the circle
    for (let i = 0; i < numPoints; i++) {
        const bearing = (i * 360 / numPoints) * (Math.PI / 180); // Convert to radians

        // Calculate the lat/lon for this point
        const latRad = deg2rad(lat);
        const lngRad = deg2rad(lng);

        const pointLat = Math.asin(
            Math.sin(latRad) * Math.cos(angularRadius) +
            Math.cos(latRad) * Math.sin(angularRadius) * Math.cos(bearing)
        );

        let pointLng = lngRad + Math.atan2(
            Math.sin(bearing) * Math.sin(angularRadius) * Math.cos(latRad),
            Math.cos(angularRadius) - Math.sin(latRad) * Math.sin(pointLat)
        );

        // Normalize longitude to -180 to 180
        pointLng = ((pointLng + 3 * Math.PI) % (2 * Math.PI)) - Math.PI;

        points.push([rad2deg(pointLat), rad2deg(pointLng)]);
    }

    // Close the circle
    points.push(points[0]);

    // Check if circle crosses the international date line
    if (detectDateLineCrossing(points)) {
        // Split the circle into two polygons
        const [eastPolygon, westPolygon] = splitCircleAtDateLine(points);

        return {
            center: centerLatLng,
            radius: radiusMeters,
            isDateLineCrossing: true,
            eastPolygon: eastPolygon,
            westPolygon: westPolygon,
            points: points
        };
    }

    return {
        center: centerLatLng,
        radius: radiusMeters,
        points: points,
        isDateLineCrossing: false
    };
}

// Helper function to split a circle that crosses the date line into two polygons
function splitCircleAtDateLine(points) {
    // Separate points into eastern and western hemispheres
    const eastPoints = [];
    const westPoints = [];

    // First pass: separate points and find crossings
    for (let i = 0; i < points.length; i++) {
        const point = points[i];
        const nextPoint = points[(i + 1) % points.length];

        // Add current point to the appropriate hemisphere
        if (point[1] >= 0) { // Eastern hemisphere
            eastPoints.push([...point]); // Copy to avoid reference issues
        } else { // Western hemisphere
            westPoints.push([...point]); // Copy to avoid reference issues
        }

        // Check if we cross the date line between this point and the next
        if (Math.abs(point[1] - nextPoint[1]) > 180) {
            // Calculate the exact latitude where the line crosses the date line
            const ratio = Math.abs(180 - Math.abs(point[1])) / Math.abs(point[1] - nextPoint[1]);
            const crossingLat = point[0] + ratio * (nextPoint[0] - point[0]);

            // Add the crossing points to both hemispheres
            if (point[1] >= 0) { // Moving from east to west
                eastPoints.push([crossingLat, 180]); // Eastern crossing at +180
                westPoints.push([crossingLat, -180]); // Western crossing at -180
            } else { // Moving from west to east
                westPoints.push([crossingLat, -180]); // Western crossing at -180
                eastPoints.push([crossingLat, 180]); // Eastern crossing at +180
            }
        }
    }

    // No points in one hemisphere, which shouldn't happen for a circle crossing the date line
    if (eastPoints.length < 3 || westPoints.length < 3) {
        console.error("Incomplete circle split: not enough points in one hemisphere");
        return [points, []]; // Return original circle as fallback
    }

    // Find points that are exactly on the date line (longitude ±180)
    const eastBoundaryPoints = eastPoints.filter(p => Math.abs(Math.abs(p[1]) - 180) < 0.001)
        .sort((a, b) => b[0] - a[0]); // Sort by latitude, north to south

    const westBoundaryPoints = westPoints.filter(p => Math.abs(Math.abs(p[1]) - 180) < 0.001)
        .sort((a, b) => b[0] - a[0]); // Sort by latitude, north to south

    // We should have the same number of boundary points in each hemisphere
    if (eastBoundaryPoints.length < 2 || westBoundaryPoints.length < 2) {
        console.error("Not enough boundary points for proper split");
        return [points, []]; // Return original points as fallback
    }

    // Extract east hemisphere points that aren't boundary points
    const eastInteriorPoints = eastPoints.filter(p => Math.abs(Math.abs(p[1]) - 180) >= 0.001);

    // Create properly sorted eastern polygon with vertical boundary
    const finalEastPolygon = [...eastInteriorPoints];

    // Add boundary points in north-to-south order
    for (const point of eastBoundaryPoints) {
        finalEastPolygon.push([...point]);
    }

    // Extract west hemisphere points that aren't boundary points
    const westInteriorPoints = westPoints.filter(p => Math.abs(Math.abs(p[1]) - 180) >= 0.001);

    // Create properly sorted western polygon with vertical boundary
    const finalWestPolygon = [...westInteriorPoints];

    // Add boundary points in south-to-north order (reverse of eastBoundaryPoints)
    for (const point of westBoundaryPoints.slice().reverse()) {
        finalWestPolygon.push([...point]);
    }

    // Ensure polygons are closed properly
    if (finalEastPolygon.length > 0 &&
        (finalEastPolygon[0][0] !== finalEastPolygon[finalEastPolygon.length - 1][0] ||
            finalEastPolygon[0][1] !== finalEastPolygon[finalEastPolygon.length - 1][1])) {
        finalEastPolygon.push([...finalEastPolygon[0]]);
    }

    if (finalWestPolygon.length > 0 &&
        (finalWestPolygon[0][0] !== finalWestPolygon[finalWestPolygon.length - 1][0] ||
            finalWestPolygon[0][1] !== finalWestPolygon[finalWestPolygon.length - 1][1])) {
        finalWestPolygon.push([...finalWestPolygon[0]]);
    }

    return [finalEastPolygon, finalWestPolygon];
}

// Function to add a legend to the map
function addRangeLegend() {
    // Remove existing legend if present
    const existingLegend = document.querySelector('.range-legend');
    if (existingLegend) {
        existingLegend.remove();
    }

    // Create new legend
    const legend = L.control({ position: 'bottomleft' });

    legend.onAdd = function () {
        const div = L.DomUtil.create('div', 'range-legend');
        div.innerHTML = `
            <div class="bg-dark p-2 rounded" style="border: 1px solid rgba(255,255,255,0.2);">
                <div style="font-weight: bold; margin-bottom: 8px; color: white; text-align: center; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 4px;">Range Rings</div>
                <div class="d-flex align-items-center mb-2">
                    <div style="width: 18px; height: 3px; background-color: #F05545; margin-right: 8px;"></div>
                    <span style="color: white; font-size: 12px;">Custom: ${Math.round(currentRange)} nm</span>
            </div>
                <div class="d-flex align-items-center mb-2">
                    <div style="width: 18px; height: 3px; background-color: #FFFFFF; margin-right: 8px;"></div>
                    <span style="color: white; font-size: 12px;">Average Trip: ${averageTripDistance} nm</span>
                </div>
                <div class="d-flex align-items-center">
                    <div style="width: 18px; height: 3px; background-color: #3498DB; margin-right: 8px;"></div>
                    <span style="color: white; font-size: 12px;">Longest Leg: ${Math.round(longestLegDistance)} nm</span>
            </div>
        </div>
    `;

        // Add CSS to prevent interaction with the legend so map clicks work
        div.style.pointerEvents = 'none';

        return div;
    };

    legend.addTo(map);
}

// Function to update range circles visibility based on range requirement
function updateRangeCircles(requiredRange) {
    // Update the custom range and refresh all rings
    currentRange = requiredRange;
    updateRangeRings();

    // Update legend with new values
    addRangeLegend();
}

// Function to load aircraft data on demand with the latest sheet data
function forceRefreshAircraftRanges() {
    // Empty function - refresh functionality is disabled
    console.log('Refresh functionality is disabled');
    return;
}

// Set the home airport for range circles
function setHomeAirport(airport, skipMapCentering = false) {
    homeAirport = airport;

    // Remove existing range circles
    if (rangeCircle) {
        map.removeLayer(rangeCircle);
        rangeCircle = null;
    }
    if (customRangePolygons) {
        customRangePolygons.forEach(polygon => map.removeLayer(polygon));
        customRangePolygons = [];
    }
    if (avgTripRangeCircle) {
        map.removeLayer(avgTripRangeCircle);
        avgTripRangeCircle = null;
    }
    if (avgTripRangePolygons) {
        avgTripRangePolygons.forEach(polygon => map.removeLayer(polygon));
        avgTripRangePolygons = [];
    }
    if (longestLegRangeCircle) {
        map.removeLayer(longestLegRangeCircle);
        longestLegRangeCircle = null;
    }
    if (longestLegRangePolygons) {
        longestLegRangePolygons.forEach(polygon => map.removeLayer(polygon));
        longestLegRangePolygons = [];
    }

    // Only adjust map view if not skipping (i.e., during normal user interaction)
    if (!skipMapCentering) {
        // Adjust center point based on airport location to ensure good visibility
        // For airports near the date line, adjust the center to keep the whole range visible
        let centerLng = airport.lon;

        // If we're close to the international date line, adjust the view
        // to ensure range circles are visible in our single world view
        if (airport.lon > 140 || airport.lon < -140) {
            // For western Pacific (east Asia), center more toward the east
            // For eastern Pacific (west US/Canada), center more toward the west
            centerLng = airport.lon > 0 ? airport.lon - 20 : airport.lon + 20;
        }

        // Set the map view, centered on the airport with a zoom level that shows the region
        map.setView([airport.lat, centerLng], 4);
    }

    // Create new range rings
    updateRangeRings();

    // Show success message only if not during restoration
    if (!skipMapCentering) {
        showToast(`Home airport set to ${airport.iata} - ${airport.city}`, 'success');
    }

    // Update home airport display
    const homeAirportSearch = document.getElementById('home-airport-search');
    if (homeAirportSearch) {
        homeAirportSearch.value = `${airport.iata} - ${airport.city}`;
    }
    const homeAirportResults = document.getElementById('home-airport-results');
    if (homeAirportResults) {
        homeAirportResults.classList.add('d-none');
    }
}

// Update range slider and related elements
function updateRangeSlider(newRange) {
    const rangeSlider = document.getElementById('range-slider');
    if (!rangeSlider) {
        console.log("Range slider element not found");
        return;
    }

    // Use a safe default if no value provided
    if (newRange === undefined || isNaN(parseInt(newRange))) {
        console.log("Invalid range value provided, using current slider value");
        newRange = parseInt(rangeSlider.value || 500);
    }

    // Ensure the range is an integer
    newRange = parseInt(newRange);
    console.log(`Setting range slider to ${newRange} nm`);

    // Update the slider value first
    rangeSlider.value = newRange;

    // Then update visual display elements
    const rangeValue = document.getElementById('range-value');
    const rangeValue2 = document.getElementById('range-value-2');
    if (rangeValue) rangeValue.textContent = newRange.toLocaleString();
    if (rangeValue2) rangeValue2.textContent = newRange.toLocaleString();

    // Update global current range value
    currentRange = newRange;

    // Apply the change to the map immediately
    updateRangeCircles(newRange);

    // Provide user feedback
    showToast(`Updated range filter to ${newRange.toLocaleString()} nm`, 'info');

    // --- NEW LOGIC: If range filter surpasses longest leg, set range requirement to longest leg ---
    if (typeof window.longestLegDistance === 'number' && newRange >= window.longestLegDistance) {
        const rangeInput = document.getElementById('range-input');
        if (rangeInput) {
            rangeInput.value = Math.round(window.longestLegDistance);
            console.log(`✅ Auto-set range requirement to longest leg: ${Math.round(window.longestLegDistance)} nm`);
        }
    }
}

// Initialize range slider event listeners
function initRangeSlider() {
    const rangeSlider = document.getElementById('range-slider');
    const resetRangeBtn = document.getElementById('reset-range-btn');
    let rangeUpdateTimer;

    if (rangeSlider) {
        // Add a more responsive input event that updates on every change
        rangeSlider.addEventListener('input', function () {
            const range = parseInt(this.value);
            if (isNaN(range)) return;

            // Update range value display immediately
            const rangeValue = document.getElementById('range-value');
            const rangeValue2 = document.getElementById('range-value-2');
            if (rangeValue) rangeValue.textContent = range.toLocaleString();
            if (rangeValue2) rangeValue2.textContent = range.toLocaleString();

            // Debounce the actual circle updates to prevent too many updates during sliding
            clearTimeout(rangeUpdateTimer);
            rangeUpdateTimer = setTimeout(() => {
                console.log(`Range slider changed to: ${range} nm - updating custom range ring`);
                currentRange = range; // Update current range immediately
                updateRangeCircles(range); // Apply the new range
            }, 50); // Small timeout for better performance during sliding
        });

        // When slider is released, ensure the final value is applied
        rangeSlider.addEventListener('change', function () {
            const range = parseInt(this.value);
            if (isNaN(range)) return;

            console.log(`Range slider final value: ${range} nm`);

            // Cancel any pending updates
            clearTimeout(rangeUpdateTimer);

            // Apply the final range immediately
            currentRange = range;
            updateRangeCircles(range);

            // Show user feedback
            showToast(`Custom range set to ${range.toLocaleString()} nm`, 'success');
        });
    }

    if (resetRangeBtn) {
        resetRangeBtn.addEventListener('click', function () {
            // If routes exist, set to average trip distance
            if (routePairs.length > 0) {
                const totalDistance = routePairs.reduce((sum, route) => sum + route.distance, 0);
                const averageDistance = Math.round(totalDistance / routePairs.length);
                console.log(`Reset range to route average: ${averageDistance} nm`);
                updateRangeSlider(averageDistance);
                showToast(`Custom range reset to average route distance: ${averageDistance.toLocaleString()} nm`, 'success');
            } else {
                // Default to 500 if no routes
                console.log('Reset range to default: 500 nm');
                updateRangeSlider(500);
                showToast('Custom range reset to default: 500 nm', 'success');
            }
        });
    }
}

// Update range slider when route pairs change
function updateAverageLegDistance() {
    let averageDistance = 500; // Default value
    let totalFrequency = 0;
    let totalWeightedDistance = 0;

    if (routePairs.length > 0) {
        // Calculate total distance and frequency for true weighted average
        routePairs.forEach(route => {
            totalWeightedDistance += route.distance * route.frequency;
            totalFrequency += route.frequency;
        });

        // True weighted average: total miles / total trips
        if (totalFrequency > 0) {
            averageDistance = Math.round(totalWeightedDistance / totalFrequency);
        } else {
            // Fall back to simple average if no frequencies
            const totalDistance = routePairs.reduce((sum, route) => sum + route.distance, 0);
            averageDistance = Math.round(totalDistance / routePairs.length);
        }
    }

    // Update the range slider with the new average distance
    updateRangeSlider(averageDistance);

    // Store the current range for the Google Sheet updates
    currentRange = averageDistance;

    // Display a toast message about the updated range
    if (routePairs.length > 0) {
        showToast(`Route average: ${averageDistance} nm (${totalFrequency} total trips)`, 'info');
    }
}

// Add a route pair between two airports
function addRoutePair(fromAirport, toAirport) {
    if (!fromAirport || !toAirport) return;

    // Check if this route already exists
    const existingRoute = routePairs.find(route =>
        (route.from.iata === fromAirport.iata && route.to.iata === toAirport.iata) ||
        (route.from.iata === toAirport.iata && route.to.iata === fromAirport.iata)
    );

    if (existingRoute) {
        // If route exists, just increment the frequency
        existingRoute.frequency += 1;
        existingRoute.totalDistance = existingRoute.distance * existingRoute.frequency;
        showToast(`Increased frequency for ${existingRoute.from.iata}-${existingRoute.to.iata} to ${existingRoute.frequency} legs per year`, 'success');

        // Update displays without adding new route
        updateRoutesDisplay();
        updateRangeRings();
        updateInputFields();
        return;
    }

    // Default frequency is 1 for new routes
    const frequency = 1;

    const legDistance = calculateDistance(fromAirport.lat, fromAirport.lon, toAirport.lat, toAirport.lon);

    const routePair = {
        id: `${fromAirport.iata}-${toAirport.iata}-${Date.now()}`,
        from: fromAirport,
        to: toAirport,
        distance: legDistance,
        frequency: frequency,
        totalDistance: legDistance * frequency
    };

    routePairs.push(routePair);

    console.log(`Adding route ${fromAirport.iata}-${toAirport.iata}, distance: ${Math.round(legDistance)} nm, frequency: ${frequency}`);

    // Generate route points for proper great circle path
    const routePoints = generateGreatCirclePath(
        [fromAirport.lat, fromAirport.lon],
        [toAirport.lat, toAirport.lon],
        Math.max(30, Math.min(120, Math.ceil(legDistance / 30)))
    );

    // Draw a single continuous route line
    const routeLine = L.polyline(routePoints, {
        color: '#F05545',
        weight: 3,
        opacity: 0.8
    }).addTo(map);

    // Store the route line
    allRouteLines.set(routePair.id, [routeLine]);

    // Add markers for each airport
    const fromIcon = L.divIcon({
        className: 'airport-marker',
        html: `<div class="airport-icon">${fromAirport.iata}</div>`,
        iconSize: [40, 40],
        iconAnchor: [20, 20]
    });

    const toIcon = L.divIcon({
        className: 'airport-marker',
        html: `<div class="airport-icon">${toAirport.iata}</div>`,
        iconSize: [40, 40],
        iconAnchor: [20, 20]
    });

    const fromMarker = L.marker([fromAirport.lat, fromAirport.lon], {
        icon: fromIcon
    }).addTo(map);

    const toMarker = L.marker([toAirport.lat, toAirport.lon], {
        icon: toIcon
    }).addTo(map);

    // Store the markers in the route pair object
    routePair.markers = {
        from: fromMarker,
        to: toMarker
    };

    // Add popups with airport info and delete button
    fromMarker.bindPopup(`
        <strong>${fromAirport.iata}</strong><br>
        ${fromAirport.name}<br>
        ${fromAirport.city}, ${fromAirport.country || ''}<br>
        <button class="btn btn-sm btn-danger mt-2 delete-route-btn" data-route-id="${routePair.id}">Delete Route</button>
    `);

    toMarker.bindPopup(`
        <strong>${toAirport.iata}</strong><br>
        ${toAirport.name}<br>
        ${toAirport.city}, ${toAirport.country || ''}<br>
        <button class="btn btn-sm btn-danger mt-2 delete-route-btn" data-route-id="${routePair.id}">Delete Route</button>
    `);

    // Add event listeners for delete buttons
    fromMarker.on('popupopen', function () {
        const btn = document.querySelector(`.delete-route-btn[data-route-id="${routePair.id}"]`);
        if (btn) {
            btn.addEventListener('click', function () {
                deleteRoutePair(routePair.id);
                fromMarker.closePopup();
            });
        }
    });

    toMarker.on('popupopen', function () {
        const btn = document.querySelector(`.delete-route-btn[data-route-id="${routePair.id}"]`);
        if (btn) {
            btn.addEventListener('click', function () {
                deleteRoutePair(routePair.id);
                toMarker.closePopup();
            });
        }
    });

    // Update displays
    updateRoutesDisplay();
    updateRangeRings();
    updateInputFields();

    // Clear selections
    selectedFromAirport = null;
    selectedToAirport = null;
    document.getElementById('from-airport').value = '';
    document.getElementById('to-airport').value = '';

    showToast(`Added route ${fromAirport.iata}-${toAirport.iata} (${Math.round(legDistance)} nm)`, 'success');
}

// Generate a great circle path between two points
function generateGreatCirclePath(from, to, numPoints) {
    const points = [];

    // Add the starting point
    points.push(from);

    // Calculate the great circle path
    const fromLat = deg2rad(from[0]);
    const fromLon = deg2rad(from[1]);
    const toLat = deg2rad(to[0]);
    const toLon = deg2rad(to[1]);

    // Handle date line crossing by choosing the direction that avoids it
    // We'll take the shorter path around the globe
    let deltaLon = toLon - fromLon;

    // Ensure we take the shorter path around the globe
    if (Math.abs(deltaLon) > Math.PI) {
        // If the difference is greater than 180 degrees, go the other way
        deltaLon = deltaLon > 0 ? deltaLon - 2 * Math.PI : deltaLon + 2 * Math.PI;
    }

    // Angular distance between points
    const d = 2 * Math.asin(
        Math.sqrt(
            Math.pow(Math.sin((fromLat - toLat) / 2), 2) +
            Math.cos(fromLat) * Math.cos(toLat) *
            Math.pow(Math.sin(deltaLon / 2), 2)
        )
    );

    // Generate intermediate points
    for (let i = 1; i < numPoints; i++) {
        const f = i / numPoints; // Fraction along the path

        // For very short distances, linear interpolation
        if (d < 0.0001) {
            const lat = from[0] + f * (to[0] - from[0]);

            // Special handling for longitude to ensure we stay in -180 to 180 range
            let lon = from[1] + f * (to[1] - from[1]);
            while (lon > 180) lon -= 360;
            while (lon < -180) lon += 360;

            points.push([lat, lon]);
            continue;
        }

        // Calculate intermediate point using spherical formulas
        const a = Math.sin((1 - f) * d) / Math.sin(d);
        const b = Math.sin(f * d) / Math.sin(d);

        const x = a * Math.cos(fromLat) * Math.cos(fromLon) +
            b * Math.cos(toLat) * Math.cos(toLon);
        const y = a * Math.cos(fromLat) * Math.sin(fromLon) +
            b * Math.cos(toLat) * Math.sin(toLon);
        const z = a * Math.sin(fromLat) + b * Math.sin(toLat);

        const lat = Math.atan2(z, Math.sqrt(Math.pow(x, 2) + Math.pow(y, 2)));
        let lon = Math.atan2(y, x);

        // Convert back to degrees
        points.push([
            rad2deg(lat),
            rad2deg(lon)
        ]);
    }

    // Add the ending point
    points.push(to);

    // Post-process the path to ensure longitude continuity
    for (let i = 1; i < points.length; i++) {
        const prevLon = points[i - 1][1];
        let currentLon = points[i][1];

        // If there's a large jump in longitude, adjust it
        if (Math.abs(currentLon - prevLon) > 180) {
            // Determine which way to wrap
            if (currentLon > prevLon) {
                // Current point is far east of previous point
                while (currentLon - prevLon > 180) {
                    currentLon -= 360;
                }
            } else {
                // Current point is far west of previous point
                while (prevLon - currentLon > 180) {
                    currentLon += 360;
                }
            }
            points[i][1] = currentLon;
        }
    }

    return points;
}

// Detect if a path crosses the international date line
function detectDateLineCrossing(points) {
    // Check consecutive points for large longitude differences
    for (let i = 0; i < points.length - 1; i++) {
        const p1 = points[i];
        const p2 = points[i + 1];

        // If longitude difference is greater than 180°, it crosses the date line
        if (Math.abs(p1[1] - p2[1]) > 180) {
            return true;
        }
    }

    // Also check if the circle spans the east and west hemispheres
    // This can help catch cases where points don't directly cross the date line
    // but the circle does span both hemispheres
    let hasEasternPoints = false;
    let hasWesternPoints = false;

    for (const point of points) {
        if (point[1] >= 0) hasEasternPoints = true;
        if (point[1] < 0) hasWesternPoints = true;

        // If we have points in both hemispheres, and the circle is large enough,
        // it's likely we cross the date line
        if (hasEasternPoints && hasWesternPoints) {
            // Check if we have points very close to the date line
            const nearDateLine = points.some(p => Math.abs(Math.abs(p[1]) - 180) < 10);
            if (nearDateLine) {
                return true;
            }
        }
    }

    return false;
}

// Create a geodesic line that follows the shortest path around the globe
function createGeodesicLine(startLatLng, endLatLng) {
    // Convert degrees to radians
    const startLat = deg2rad(startLatLng[0]);
    const startLng = deg2rad(startLatLng[1]);
    const endLat = deg2rad(endLatLng[0]);
    const endLng = deg2rad(endLatLng[1]);

    // Number of intermediate points
    const numPoints = 100;

    // Array to hold the points
    const points = [startLatLng];

    // Check if we're going east-west (primarily longitude change)
    const latDiff = Math.abs(endLatLng[0] - startLatLng[0]);
    const lngDiff = Math.abs(endLatLng[1] - startLatLng[1]);
    const isEastWestRoute = lngDiff > latDiff;

    // Check if we cross the antimeridian (international date line)
    const crossesAntimeridian = Math.abs(endLatLng[1] - startLatLng[1]) > 180;

    // For routes crossing the date line with worldCopyJump enabled,
    // we need a special handling to draw the shorter path
    if (crossesAntimeridian) {
        // Determine which direction to go around the world (east or west)
        // We want the shorter path
        const goEast = shouldGoEast(startLatLng[1], endLatLng[1]);

        // Create the points
        for (let i = 1; i < numPoints; i++) {
            const fraction = i / numPoints;

            // Handle longitude wrapping appropriately
            let intermediateLng;
            if (goEast) {
                // Going east - ensure proper wrapping
                if (startLatLng[1] > endLatLng[1]) {
                    // When starting east and going west across the date line
                    intermediateLng = startLatLng[1] + (360 - Math.abs(startLatLng[1] - endLatLng[1])) * fraction;
                    if (intermediateLng > 180) intermediateLng -= 360;
                } else {
                    // Normal east movement
                    intermediateLng = startLatLng[1] + (endLatLng[1] - startLatLng[1]) * fraction;
                }
            } else {
                // Going west - ensure proper wrapping
                if (startLatLng[1] < endLatLng[1]) {
                    // When starting west and going east across the date line
                    intermediateLng = startLatLng[1] - (360 - Math.abs(startLatLng[1] - endLatLng[1])) * fraction;
                    if (intermediateLng < -180) intermediateLng += 360;
                } else {
                    // Normal west movement
                    intermediateLng = startLatLng[1] + (endLatLng[1] - startLatLng[1]) * fraction;
                }
            }

            // Linear interpolation for latitude
            const intermediateLat = startLatLng[0] + (endLatLng[0] - startLatLng[0]) * fraction;

            points.push([intermediateLat, intermediateLng]);
        }
    } else {
        // For normal routes, use great circle path
        for (let i = 1; i < numPoints; i++) {
            const fraction = i / numPoints;
            const point = intermediatePoint(startLat, startLng, endLat, endLng, fraction);
            points.push([rad2deg(point[0]), rad2deg(point[1])]);
        }
    }

    // Add end point
    points.push(endLatLng);

    return points;
}

// Determine whether to go east or west between two longitudes for the shortest path
function shouldGoEast(lon1, lon2) {
    // Normalize longitudes to be between -180 and 180
    lon1 = ((lon1 + 180) % 360) - 180;
    lon2 = ((lon2 + 180) % 360) - 180;

    // Calculate distance going east and west
    let distEast, distWest;

    if (lon1 <= lon2) {
        // Normal case
        distEast = lon2 - lon1;
        distWest = (lon1 + 360) - lon2;
    } else {
        // When lon1 > lon2
        distEast = (lon2 + 360) - lon1;
        distWest = lon1 - lon2;
    }

    // Return true if going east is shorter or equal
    return distEast <= distWest;
}

// Calculate bearing from point 1 to point 2
function calculateBearing(lat1, lon1, lat2, lon2) {
    const lat1Rad = deg2rad(lat1);
    const lat2Rad = deg2rad(lat2);
    const lonDiff = deg2rad(lon2 - lon1);

    const y = Math.sin(lonDiff) * Math.cos(lat2Rad);
    const x = Math.cos(lat1Rad) * Math.sin(lat2Rad) -
        Math.sin(lat1Rad) * Math.cos(lat2Rad) * Math.cos(lonDiff);

    let bearing = Math.atan2(y, x);
    bearing = rad2deg(bearing);
    return (bearing + 360) % 360; // Normalize to 0-360
}

// Calculate intermediate point on a great circle
function intermediatePoint(lat1, lng1, lat2, lng2, fraction) {
    const d = 2 * Math.asin(
        Math.sqrt(
            Math.pow(Math.sin((lat1 - lat2) / 2), 2) +
            Math.cos(lat1) * Math.cos(lat2) * Math.pow(Math.sin((lng1 - lng2) / 2), 2)
        )
    );

    if (d === 0) {
        return [rad2deg(lat1), rad2deg(lng1)];
    }

    const A = Math.sin((1 - fraction) * d) / Math.sin(d);
    const B = Math.sin(fraction * d) / Math.sin(d);

    const x = A * Math.cos(lat1) * Math.cos(lng1) + B * Math.cos(lat2) * Math.cos(lng2);
    const y = A * Math.cos(lat1) * Math.sin(lng1) + B * Math.cos(lat2) * Math.sin(lng2);
    const z = A * Math.sin(lat1) + B * Math.sin(lat2);

    const lat = Math.atan2(z, Math.sqrt(Math.pow(x, 2) + Math.pow(y, 2)));
    const lng = Math.atan2(y, x);

    return [lat, lng];
}

// Convert radians to degrees
function rad2deg(rad) {
    return rad * 180 / Math.PI;
}

// Update the route display in the UI
function updateRoutesDisplay() {
    const routesContainer = document.getElementById('routes-container');
    const totalDistanceElement = document.getElementById('total-distance');

    if (!routesContainer || !totalDistanceElement) return;

    // Calculate various metrics
    if (routePairs.length > 0) {
        // Find the longest leg distance
        longestLegDistance = Math.max(...routePairs.map(route => route.distance));

        // Calculate total trips (sum of all frequencies)
        const totalTrips = routePairs.reduce((sum, route) => sum + route.frequency, 0);

        // Calculate weighted average distance
        let totalWeightedDistance = 0;
        routePairs.forEach(route => {
            totalWeightedDistance += route.distance * route.frequency;
        });

        // Calculate the weighted average and round it
        const weightedAvgDistance = totalTrips > 0 ?
            Math.round(totalWeightedDistance / totalTrips) : 0;

        // Update the display to show average, longest leg, and total trips
        totalDistanceElement.textContent = `${weightedAvgDistance} nm avg, ${Math.round(longestLegDistance)} nm longest, ${totalTrips} trips`;

        // Update average trip distance for the range rings - ensure exact match with displayed value
        averageTripDistance = weightedAvgDistance;

        console.log(`Route metrics updated - Avg: ${averageTripDistance}, Longest: ${longestLegDistance}, Total trips: ${totalTrips}`);
    } else {
        totalDistanceElement.textContent = '0 nm avg, 0 nm longest, 0 trips';
        longestLegDistance = 0;
        averageTripDistance = 500; // Default fallback
    }

    // Update routes list
    routesContainer.innerHTML = '';

    if (routePairs.length === 0) {
        routesContainer.innerHTML = '<div class="text-secondary text-center">No routes added</div>';
        return;
    }

    // Calculate total weighted distance for percentage calculation
    const totalWeightedDistance = routePairs.reduce((sum, route) => sum + (route.distance * route.frequency), 0);
    const totalTrips = routePairs.reduce((sum, route) => sum + route.frequency, 0);

    routePairs.forEach(route => {
        const percentage = totalWeightedDistance > 0
            ? Math.round((route.distance * route.frequency / totalWeightedDistance) * 100)
            : 0;
        const tripPercentage = totalTrips > 0
            ? Math.round((route.frequency / totalTrips) * 100)
            : 0;

        // Highlight the longest leg
        const isLongestLeg = Math.abs(route.distance - longestLegDistance) < 0.1;
        const routeItemClass = isLongestLeg ? 'route-item p-2 mb-2 rounded border border-primary' : 'route-item p-2 mb-2 rounded';
        const distanceClass = isLongestLeg ? 'text-primary' : 'text-danger';

        const routeItem = document.createElement('div');
        routeItem.className = routeItemClass;
        routeItem.innerHTML = `
            <div class="d-flex justify-content-between align-items-center mb-1">
                <div>
                    <strong>${route.from.iata}</strong> → <strong>${route.to.iata}</strong>
                    <div class="text-secondary small">${route.from.city} to ${route.to.city}</div>
                </div>
                <button class="btn btn-sm btn-outline-danger delete-route" data-id="${route.id}">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="d-flex justify-content-between align-items-center">
                <div class="${distanceClass}">
                    <div>${Math.round(route.distance)} nm per leg ${isLongestLeg ? '(Longest)' : ''}</div>
                    <div class="text-secondary small">
                        ${Math.round(route.distance * route.frequency)} nm total (${percentage}%)
                    </div>
                    <div class="text-secondary small">
                        ${route.frequency} legs per year (${tripPercentage}%)
                    </div>
                </div>
                <div class="d-flex align-items-center">
                    <label class="text-white me-2 small">Legs/Year:</label>
                    <input type="number" class="form-control form-control-sm route-frequency" 
                           style="width: 60px;" min="1" value="${route.frequency}" 
                           data-id="${route.id}">
                </div>
            </div>
        `;

        const deleteBtn = routeItem.querySelector('.delete-route');
        deleteBtn.addEventListener('click', () => deleteRoutePair(route.id));

        // Add event listener for frequency changes
        const frequencyInput = routeItem.querySelector('.route-frequency');
        frequencyInput.addEventListener('change', function () {
            let newFrequency = parseInt(this.value) || 1;
            if (newFrequency < 1) {
                this.value = 1;
                newFrequency = 1;
            }
            updateRouteFrequency(route.id, newFrequency);
        });

        routesContainer.appendChild(routeItem);
    });
}

// Delete a route pair by ID
function deleteRoutePair(pairId) {
    // Find the route
    const index = routePairs.findIndex(route => route.id === pairId);
    if (index !== -1) {
        const routePair = routePairs[index];

        // Remove the airport markers if they exist
        if (routePair.markers) {
            if (routePair.markers.from) {
                map.removeLayer(routePair.markers.from);
            }
            if (routePair.markers.to) {
                map.removeLayer(routePair.markers.to);
            }
        }

        // Remove from the array
        routePairs.splice(index, 1);
    }

    // Remove route lines from the map
    const routeLines = allRouteLines.get(pairId);
    if (routeLines) {
        // Remove each route segment
        routeLines.forEach(line => {
            map.removeLayer(line);
        });
        allRouteLines.delete(pairId);
    }

    // Update displays and input fields
    updateRoutesDisplay();
    updateRangeRings();
    updateInputFields();

    console.log(`Deleted route: ${pairId}`);
}

// Clear all routes
function clearAllRoutes() {
    // Remove all airport markers
    routePairs.forEach(route => {
        if (route.markers) {
            if (route.markers.from) {
                map.removeLayer(route.markers.from);
            }
            if (route.markers.to) {
                map.removeLayer(route.markers.to);
            }
        }
    });

    // Remove all lines from map
    allRouteLines.forEach(routeLines => {
        // Each route may have multiple line segments
        routeLines.forEach(line => {
            map.removeLayer(line);
        });
    });

    // Clear collections
    allRouteLines.clear();
    routePairs = [];

    // Reset distance variables
    longestLegDistance = 0;
    averageTripDistance = 0;

    // Update displays and input fields
    updateRoutesDisplay();
    updateRangeRings();
    updateInputFields();

    console.log('Cleared all routes');
    showToast('All routes cleared', 'info');
}

// Make sure to resize the map when the container size changes
function resizeMap() {
    if (map) {
        // Force the map to resize after the layout has loaded
        setTimeout(() => {
            map.invalidateSize();
        }, 500);
    }
}

// Event listener setup for the page
document.addEventListener('DOMContentLoaded', function () {
    console.log('JetFinder initializing...');

    // Initialize the map
    initMap();

    // Show welcome message and instructions
    showToast('Welcome to JetFinder! Please select a home airport', 'info');

    // Enable typeahead search for home airport
    setupAirportSearchEventListeners();

    // Google Sheet interactions are disabled for now
    // setupGoogleSheetInteractions();
    // setupGoogleSheetAutoUpdate();

    // Initialize range slider
    initRangeSlider();

    // Add event listeners for route planning
    setupRoutePlanningEventListeners();

    // Add resize handler for the map
    window.addEventListener('resize', resizeMap);

    // Ensure map is properly sized after page load
    resizeMap();

    // Add event listeners for scenario analysis
    const scenarioBtn = document.getElementById('scenarioAnalysisBtn');
    if (scenarioBtn) {
        scenarioBtn.addEventListener('click', showScenarioAnalysis);
    }
    const runScenarioBtn = document.getElementById('runScenarioBtn');
    if (runScenarioBtn) {
        runScenarioBtn.addEventListener('click', runScenarioAnalysis);
    }
});

// Setup airport search event listeners
function setupAirportSearchEventListeners() {
    console.log('Setting up airport search event listeners...');

    // Home airport search elements
    const homeAirportSearch = document.getElementById('home-airport-search');
    const homeAirportResults = document.getElementById('home-airport-results');
    const homeAirportList = document.getElementById('home-airport-list');
    const searchHomeBtn = document.getElementById('search-home-btn');

    console.log('Home airport elements:', {
        search: !!homeAirportSearch,
        results: !!homeAirportResults,
        list: !!homeAirportList,
        button: !!searchHomeBtn
    });

    // From/To airport search elements
    const fromAirportInput = document.getElementById('from-airport');
    const toAirportInput = document.getElementById('to-airport');
    const searchFromBtn = document.getElementById('search-from-btn');
    const searchToBtn = document.getElementById('search-to-btn');
    const fromAirportResults = document.getElementById('from-airport-results');
    const toAirportResults = document.getElementById('to-airport-results');
    const fromAirportList = document.getElementById('from-airport-list');
    const toAirportList = document.getElementById('to-airport-list');

    console.log('From/To airport elements:', {
        fromInput: !!fromAirportInput,
        toInput: !!toAirportInput,
        fromResults: !!fromAirportResults,
        toResults: !!toAirportResults
    });

    // Home airport search event listeners
    if (homeAirportSearch) {
        homeAirportSearch.addEventListener('input', function () {
            console.log('Home airport input triggered:', this.value);
            const query = this.value.trim();
            if (query.length >= 2) {
                searchHomeAirport(query, homeAirportList, homeAirportResults);
            } else {
                homeAirportResults.classList.add('d-none');
            }
        });
        console.log('✅ Home airport input listener added');
    } else {
        console.log('❌ Home airport search input not found');
    }

    if (searchHomeBtn) {
        searchHomeBtn.addEventListener('click', function () {
            console.log('Home airport search button clicked');
            const query = homeAirportSearch.value.trim();
            if (query.length >= 2) {
                searchHomeAirport(query, homeAirportList, homeAirportResults);
            }
        });
        console.log('✅ Home airport button listener added');
    } else {
        console.log('❌ Home airport search button not found');
    }

    // From airport search event listeners
    if (fromAirportInput) {
        fromAirportInput.addEventListener('input', function () {
            console.log('From airport input triggered:', this.value);
            const query = this.value.trim();
            if (query.length >= 2) {
                searchAirports(query, fromAirportList, fromAirportResults, 'from');
            } else {
                fromAirportResults.classList.add('d-none');
            }
        });
        console.log('✅ From airport input listener added');
    } else {
        console.log('❌ From airport input not found');
    }

    // To airport search event listeners
    if (toAirportInput) {
        toAirportInput.addEventListener('input', function () {
            console.log('To airport input triggered:', this.value);
            const query = this.value.trim();
            if (query.length >= 2) {
                searchAirports(query, toAirportList, toAirportResults, 'to');
            } else {
                toAirportResults.classList.add('d-none');
            }
        });
        console.log('✅ To airport input listener added');
    } else {
        console.log('❌ To airport input not found');
    }

    if (searchFromBtn) {
        searchFromBtn.addEventListener('click', function () {
            console.log('From search button clicked');
            const query = fromAirportInput.value.trim();
            if (query.length >= 2) {
                searchAirports(query, fromAirportList, fromAirportResults, 'from');
            }
        });
        console.log('✅ From airport button listener added');
    } else {
        console.log('❌ From airport search button not found');
    }

    if (searchToBtn) {
        searchToBtn.addEventListener('click', function () {
            console.log('To search button clicked');
            const query = toAirportInput.value.trim();
            if (query.length >= 2) {
                searchAirports(query, toAirportList, toAirportResults, 'to');
            }
        });
        console.log('✅ To airport button listener added');
    } else {
        console.log('❌ To airport search button not found');
    }

    // Close search results when clicking outside
    document.addEventListener('click', function (event) {
        // Home airport dropdown
        if (homeAirportResults && homeAirportSearch) {
            if (!homeAirportSearch.contains(event.target) &&
                !homeAirportResults.contains(event.target) &&
                !searchHomeBtn?.contains(event.target)) {
                homeAirportResults.classList.add('d-none');
            }
        }

        // From airport dropdown
        if (fromAirportResults && fromAirportInput) {
            if (!fromAirportInput.contains(event.target) &&
                !fromAirportResults.contains(event.target) &&
                !searchFromBtn?.contains(event.target)) {
                fromAirportResults.classList.add('d-none');
            }
        }

        // To airport dropdown  
        if (toAirportResults && toAirportInput) {
            if (!toAirportInput.contains(event.target) &&
                !toAirportResults.contains(event.target) &&
                !searchToBtn?.contains(event.target)) {
                toAirportResults.classList.add('d-none');
            }
        }
    });
}

// Setup route planning event listeners
function setupRoutePlanningEventListeners() {
    const addRouteBtn = document.getElementById('add-route-btn');
    const clearRoutesBtn = document.getElementById('clear-routes-btn');

    if (addRouteBtn) {
        addRouteBtn.addEventListener('click', function () {
            if (selectedFromAirport && selectedToAirport) {
                addRoutePair(selectedFromAirport, selectedToAirport);
            } else {
                showToast('Please select both departure and arrival airports', 'warning');
            }
        });
    }

    if (clearRoutesBtn) {
        clearRoutesBtn.addEventListener('click', function () {
            clearAllRoutes();
        });
    }
}

// Handle airport search input
function searchAirports(query, resultsList, resultsContainer, type = 'from') {
    console.log('searchAirports called with:', query, 'type:', type, 'resultsList:', !!resultsList, 'resultsContainer:', !!resultsContainer);

    if (!query.trim()) {
        resultsContainer.classList.add('d-none');
        console.log('Query empty, hiding results container for type:', type);
        return;
    }

    // Show loading state
    resultsList.innerHTML = '<div class="list-group-item bg-dark text-white">Searching...</div>';
    resultsContainer.classList.remove('d-none');
    console.log('Showing results container for type:', type, 'removed d-none class');

    // Fetch airports from API
    fetch(`/api/airports?q=${encodeURIComponent(query)}`)
        .then(response => {
            console.log('API response status for type', type, ':', response.status);
            return response.json();
        })
        .then(airports => {
            console.log('Received airports for type', type, ':', airports.length);
            resultsList.innerHTML = '';

            if (airports.length === 0) {
                resultsList.innerHTML = '<div class="list-group-item bg-dark text-white">No airports found</div>';
                console.log('No airports found for type:', type);
                return;
            }

            console.log('Adding airports to dropdown for type:', type);
            airports.forEach((airport, index) => {
                const item = document.createElement('button');
                item.type = 'button';
                item.className = 'list-group-item list-group-item-action bg-dark text-white border-secondary';
                item.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    ${airport.iata ? `<strong class="me-2">${airport.iata}</strong>` : ''}
                    ${airport.icao ? `<span class="text-info">${airport.icao}</span>` : ''}
                </div>
                ${airport.size ? `<span class="badge bg-danger">${airport.size}</span>` : ''}
            </div>
            <div class="text-truncate">${airport.name}</div>
            <small class="text-secondary text-truncate d-block">${airport.city}, ${airport.country}</small>
        `;

                item.addEventListener('click', function (e) {
                    e.preventDefault();
                    e.stopPropagation();
                    console.log('Airport selected for type', type, ':', airport.iata);
                    if (type === 'from') {
                        selectedFromAirport = airport;
                        document.getElementById('from-airport').value = `${airport.iata} - ${airport.city}`;
                    } else {
                        selectedToAirport = airport;
                        document.getElementById('to-airport').value = `${airport.iata} - ${airport.city}`;
                    }
                    resultsContainer.classList.add('d-none');
                });

                resultsList.appendChild(item);
                console.log(`Added airport ${index + 1} for type ${type}:`, airport.iata);
            });
            console.log('All airports added to dropdown for type:', type);
        })
        .catch(error => {
            console.error('Error searching airports for type', type, ':', error);
            resultsList.innerHTML = '<div class="list-group-item bg-dark text-white">Error searching airports</div>';
        });
}

// Calculate distance between two points using Haversine formula
function calculateDistance(lat1, lon1, lat2, lon2) {
    const R = 3440.065; // Radius of the earth in nautical miles
    const dLat = deg2rad(lat2 - lat1);
    const dLon = deg2rad(lon2 - lon1);
    const a =
        Math.sin(dLat / 2) * Math.sin(dLat / 2) +
        Math.cos(deg2rad(lat1)) * Math.cos(deg2rad(lat2)) *
        Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    const distance = R * c; // Distance in nm
    return distance;
}

// Convert degrees to radians
function deg2rad(deg) {
    return deg * (Math.PI / 180);
}

// Show toast message
function showToast(message, type = 'info') {
    // Disabled toast notifications - just log to console instead
    console.log(`[${type.toUpperCase()}] ${message}`);
    // Original toast code removed
}

// Update visible airports within the current bounds
function updateVisibleAirports() {
    const bounds = map.getBounds();
    if (!bounds) return;

    const currentZoom = map.getZoom();
    const MIN_ZOOM_FOR_AIRPORTS = 5;
    if (currentZoom < MIN_ZOOM_FOR_AIRPORTS) {
        hideAllAirportMarkers();
        return;
    }

    // Check which markers are in the current bounds
    for (const markerId in airportMarkers) {
        const marker = airportMarkers[markerId];
        const pos = marker.getLatLng();

        if (!bounds.contains(pos)) {
            marker.remove();
        } else {
            marker.addTo(map);
        }
    }

    // Load airports in the current view
    const visibleBounds = {
        north: bounds.getNorthEast().lat,
        south: bounds.getSouthWest().lat,
        east: bounds.getNorthEast().lng,
        west: bounds.getSouthWest().lng
    };

    loadAirportsInView(visibleBounds);
}

// Hide all airport markers on the map
function hideAllAirportMarkers() {
    for (const markerId in airportMarkers) {
        airportMarkers[markerId].remove();
    }
}

// Load airports that are within the specified bounds
function loadAirportsInView(bounds) {
    // This function would normally load airports from a database
    // For now, it's just a placeholder
    console.log('Loading airports in view:', bounds);
}

// Update route frequency
function updateRouteFrequency(routeId, newFrequency) {
    const route = routePairs.find(r => r.id === routeId);
    if (!route) return;

    route.frequency = newFrequency;
    route.totalDistance = route.distance * route.frequency;

    console.log(`Updated frequency for route ${route.from.iata}-${route.to.iata} to ${newFrequency}`);

    // Update displays
    updateRoutesDisplay();
    updateRangeRings();
    updateInputFields();

    showToast(`Updated ${route.from.iata}-${route.to.iata} frequency to ${newFrequency} legs per year`, 'info');
}

// Update input fields with calculated values
function updateInputFields() {
    console.log('updateInputFields() called');
    console.log('routePairs.length:', routePairs.length);
    console.log('URL params:', window.location.search);

    // Check if we're in a restoration state (URL has parameters indicating submitted data)
    const urlParams = new URLSearchParams(window.location.search);
    const hasSubmittedData = urlParams.has('budget') || urlParams.has('range_requirement') ||
        urlParams.has('passengers') || urlParams.has('avg_trip_length') ||
        urlParams.has('yearly_trips');

    console.log('hasSubmittedData:', hasSubmittedData);

    // If we have submitted data, don't auto-update the fields at all - let restoration handle it
    if (hasSubmittedData) {
        console.log('Skipping auto-update - in restoration mode');
        return;
    }

    const rangeInput = document.getElementById('range-input');
    const avgTripInput = document.getElementById('avg-trip-length');
    const numberOfTripsInput = document.getElementById('number-of-trips');

    if (routePairs.length === 0) {
        console.log('Clearing form fields - no routes and no submitted data');
        // Clear auto-calculated fields when no routes and no submitted data
        if (rangeInput) rangeInput.value = '';
        if (avgTripInput) avgTripInput.value = '';
        if (numberOfTripsInput) numberOfTripsInput.value = '';
        return;
    }

    // Calculate metrics across ALL routes
    const totalTrips = routePairs.reduce((sum, route) => sum + route.frequency, 0);
    let totalWeightedDistance = 0;
    routePairs.forEach(route => {
        totalWeightedDistance += route.distance * route.frequency;
    });

    const longestLeg = Math.max(...routePairs.map(route => route.distance));
    const weightedAverageTrip = totalTrips > 0 ? Math.round(totalWeightedDistance / totalTrips) : 0;

    console.log('Calculated route metrics:', {
        totalTrips,
        longestLeg: Math.round(longestLeg),
        weightedAverageTrip,
        totalWeightedDistance
    });

    // Always update the auto-calculated fields (these should reflect current route data)
    // Range input = longest leg across all routes
    if (rangeInput) {
        const roundedLongestLeg = Math.round(longestLeg);
        rangeInput.value = roundedLongestLeg;
        console.log(`✅ Updated range input to longest leg: ${roundedLongestLeg} nm`);

        // Debug: Verify the value was set correctly
        setTimeout(() => {
            const actualValue = document.getElementById('range-input')?.value;
            console.log(`🔍 Range input verification - Set: ${roundedLongestLeg}, Actual: ${actualValue}`);
            if (actualValue != roundedLongestLeg) {
                console.error(`❌ Range input mismatch! Expected: ${roundedLongestLeg}, Got: ${actualValue}`);
            }
        }, 100);
    } else {
        console.error('❌ Range input element not found!');
    }

    // Average trip length = weighted average across all routes
    if (avgTripInput) {
        avgTripInput.value = weightedAverageTrip;
        console.log(`✅ Updated avg trip length to weighted average: ${weightedAverageTrip} nm`);
    }

    // Number of trips = total frequency across all routes
    if (numberOfTripsInput) {
        numberOfTripsInput.value = totalTrips;
        console.log(`✅ Updated number of trips to total: ${totalTrips}`);
    }

    // Update global variables for range ring calculations
    window.longestLegDistance = longestLeg;
    window.averageTripDistance = weightedAverageTrip;
}

// Expose functions to window for restoration
window.generateGreatCirclePath = generateGreatCirclePath;
window.updateRoutesDisplay = updateRoutesDisplay;
window.updateRangeRings = updateRangeRings;
window.deleteRoutePair = deleteRoutePair;
window.setHomeAirport = setHomeAirport;
window.updateInputFields = updateInputFields;

// ===== MARKET INTELLIGENCE & AI FEATURES =====

let marketInsightsChart = null;
let manufacturerChart = null;
let scenarioChart = null;

function showMarketInsights() {
    // ... existing code ...
}

function showAIRecommendations() {
    // ... existing code ...
}

function showScenarioAnalysis() {
    // Show the scenario analysis modal
    const modal = new bootstrap.Modal(document.getElementById('scenarioAnalysisModal'));
    modal.show();
}

function runScenarioAnalysis() {
    // Collect scenario parameters from modal inputs
    const hours = parseInt(document.getElementById('scenarioHours').value) || 100;
    const fuelPrice = parseFloat(document.getElementById('scenarioFuelPrice').value) || 6.5;
    const years = parseInt(document.getElementById('scenarioYears').value) || 5;

    // You can add more parameters as needed
    const scenario = {
        name: 'Custom Scenario',
        inputs: {
            annual_hours: hours,
            fuel_price: fuelPrice,
            ownership_years: years
        },
        priorities: {} // Optionally add priorities
    };

    // Show loading state
    const scenarioTableBody = document.getElementById('scenarioTableBody');
    scenarioTableBody.innerHTML = '<tr><td colspan="5">Running analysis...</td></tr>';

    // Call the backend API
    fetch('/api/scenario-analysis', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenarios: [scenario] })
    })
        .then(response => response.json())
        .then(data => {
            if (data && data.scenario_analysis && data.scenario_analysis.length > 0) {
                const top = data.scenario_analysis[0].top_recommendations;
                scenarioTableBody.innerHTML = '';
                top.forEach(rec => {
                    const ac = rec.aircraft;
                    const comp = rec.component_scores;
                    scenarioTableBody.innerHTML += `
                        <tr>
                            <td>${ac.manufacturer} ${ac.model}</td>
                            <td>$${(ac.annual_budget || 0).toLocaleString()}</td>
                            <td>$${(ac.multi_year_total_cost || 0).toLocaleString()}</td>
                            <td>$${(ac.total_hourly_cost || 0).toLocaleString()}</td>
                            <td>${(comp && comp.spreadsheet ? comp.spreadsheet.toFixed(1) : '')}</td>
                        </tr>
                    `;
                });
            } else {
                scenarioTableBody.innerHTML = '<tr><td colspan="5">No results found.</td></tr>';
            }
        })
        .catch(error => {
            scenarioTableBody.innerHTML = `<tr><td colspan="5">Error: ${error.message}</td></tr>`;
        });
}

// Attach event listeners for scenario analysis

// Ensure What-If Analysis button opens modal and runs scenario analysis
const scenarioBtn = document.getElementById('scenarioAnalysisBtn');
if (scenarioBtn) {
    scenarioBtn.addEventListener('click', showScenarioAnalysis);
}
const runScenarioBtn = document.getElementById('runScenarioBtn');
if (runScenarioBtn) {
    runScenarioBtn.addEventListener('click', runScenarioAnalysis);
}

// Optional developer-only warning for unwired buttons (disabled in production)
// To enable for a specific button, add data-warn-if-unwired="true"
document.addEventListener('click', function (e) {
    const btn = e.target.closest('button');
    if (!btn) return;
    // Ignore Bootstrap/ARIA toggles and functional buttons
    if (btn.hasAttribute('data-bs-toggle') || btn.hasAttribute('data-bs-dismiss')) return;
    if (btn.dataset.action || typeof btn.onclick === 'function') return;
    if (btn.getAttribute('data-warn-if-unwired') === 'true') {
        // eslint-disable-next-line no-alert
        alert('This button is not yet connected to a feature. Please check back soon!');
    }
});
