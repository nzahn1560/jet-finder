/**
 * Enhanced Trip Planner - Complete functionality with frequency tracking and seamless updates
 */

console.log('✈️ Loading Enhanced Trip Planner...');

let routes = [];
let routeLines = [];
let tripStatsBar = null;
let autoUpdateEnabled = false; // Disable auto-updates by default

document.addEventListener('DOMContentLoaded', function () {
    console.log('✈️ Setting up enhanced trip planner...');

    setupTripPlannerButtons();
    updateTripStatistics();

    // Set up auto-update event listeners - but disabled by default
    // setupAutoUpdateListeners();

    // Create trip statistics information bar
    createTripStatsBar();

    // Restore page state if available - but without auto-scrolling
    setTimeout(() => {
        restorePageStateMinimal();
    }, 1000);

    // Set up minimal state preservation without aggressive timers
    setupMinimalStatePreservation();
});

function createTripStatsBar() {
    // Remove any existing stats bar
    const existingStatsBar = document.querySelector('.trip-stats-bar');
    if (existingStatsBar) {
        existingStatsBar.remove();
    }

    // Find the Trip Planning card body specifically
    const tripPlanningCard = document.querySelector('.card-header h4 i.fa-route')?.closest('.card');
    let targetLocation = null;

    if (tripPlanningCard) {
        // Look for the Trip Statistics Panel within the trip planning card
        const existingStatsPanel = tripPlanningCard.querySelector('.card.bg-secondary.bg-opacity-25');
        if (existingStatsPanel) {
            // Replace the existing static panel with our dynamic one
            targetLocation = existingStatsPanel.parentNode;
            existingStatsPanel.remove();
        } else {
            // If no existing panel, insert after route controls
            const routeControls = tripPlanningCard.querySelector('.d-flex.justify-content-between');
            if (routeControls) {
                targetLocation = routeControls.parentNode;
            }
        }
    }

    if (!targetLocation) {
        console.warn('⚠️ Could not find trip planning section for stats bar');
        return;
    }

    // Create the dynamic trip statistics bar
    tripStatsBar = document.createElement('div');
    tripStatsBar.className = 'trip-stats-bar card bg-secondary bg-opacity-25 border-secondary mb-3';
    tripStatsBar.innerHTML = `
        <div class="card-header bg-transparent border-bottom border-secondary py-2">
            <h6 class="mb-0 text-warning">
                <i class="fas fa-chart-line me-2"></i>Trip Statistics
            </h6>
        </div>
        <div class="card-body py-2">
            <div class="row text-center">
                <div class="col-4">
                    <div class="border-end border-secondary pe-2">
                        <div class="fs-4 fw-bold text-danger" id="longest-leg-display">0</div>
                        <div class="small text-muted">Longest Leg (NM)</div>
                    </div>
                </div>
                <div class="col-4">
                    <div class="border-end border-secondary pe-2">
                        <div class="fs-4 fw-bold text-primary" id="avg-leg-display">0</div>
                        <div class="small text-muted">Avg. Leg (NM)</div>
                    </div>
                </div>
                <div class="col-4">
                    <div>
                        <div class="fs-4 fw-bold text-success" id="total-trips-display">0</div>
                        <div class="small text-muted"># of trips</div>
                    </div>
                </div>
            </div>
            <div class="row mt-2">
                <div class="col-12 text-center">
                    <div class="text-warning fw-bold">
                        Total Distance: <span id="total-distance-display">0 nm</span>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Insert the stats bar in the trip planning section
    const routeControls = targetLocation.querySelector('.d-flex.justify-content-between');
    if (routeControls) {
        targetLocation.insertBefore(tripStatsBar, routeControls.nextSibling);
    } else {
        targetLocation.appendChild(tripStatsBar);
    }

    console.log('✅ Trip statistics bar correctly placed in trip planning section');
}

function setupTripPlannerButtons() {
    // Add Route button
    const addRouteBtn = document.getElementById('add-route-btn');
    if (addRouteBtn) {
        addRouteBtn.addEventListener('click', function () {
            console.log('➕ Add route button clicked');
            addRoute();
        });
        console.log('✅ Add route button setup');
    }

    // Clear Routes button
    const clearRoutesBtn = document.getElementById('clear-routes-btn');
    if (clearRoutesBtn) {
        clearRoutesBtn.addEventListener('click', function () {
            console.log('🗑️ Clear routes button clicked');
            clearAllRoutes();
        });
        console.log('✅ Clear routes button setup');
    }
}

function addRoute() {
    // Get selected airports from global variables
    const fromAirport = window.selectedFromAirport;
    const toAirport = window.selectedToAirport;

    if (!fromAirport) {
        alert('Please select a departure airport');
        return;
    }

    if (!toAirport) {
        alert('Please select an arrival airport');
        return;
    }

    if (fromAirport.iata === toAirport.iata) {
        alert('Departure and arrival airports cannot be the same');
        return;
    }

    // Calculate distance using Haversine formula
    const distance = calculateDistance(fromAirport.lat, fromAirport.lon, toAirport.lat, toAirport.lon);

    // Create route object with frequency tracking
    const route = {
        id: Date.now(),
        from: fromAirport,
        to: toAirport,
        distance: Math.round(distance),
        frequency: 1 // Default to 1 trip per period
    };

    // Add to routes array
    routes.push(route);

    console.log(`✅ Added route: ${fromAirport.iata} → ${toAirport.iata} (${route.distance} NM)`);

    // Update displays
    updateRoutesDisplay();
    updateMapWithRoutes();
    updateTripStatistics();
    updateAircraftInputsSeamlessly();

    // Clear the from/to inputs
    const fromInput = document.getElementById('from-airport');
    const toInput = document.getElementById('to-airport');
    if (fromInput) fromInput.value = '';
    if (toInput) toInput.value = '';

    // Clear selected airports
    window.selectedFromAirport = null;
    window.selectedToAirport = null;
}

function removeRoute(routeId) {
    console.log(`🗑️ Removing route ${routeId}`);

    // Remove from routes array
    routes = routes.filter(route => route.id !== routeId);

    // Update displays
    updateRoutesDisplay();
    updateMapWithRoutes();
    updateTripStatistics();
    updateAircraftInputsSeamlessly();
}

function clearAllRoutes() {
    console.log('🗑️ Clearing all routes');

    routes = [];

    // Update displays
    updateRoutesDisplay();
    updateMapWithRoutes();
    updateTripStatistics();
    updateAircraftInputsSeamlessly();
}

function updateRouteFrequency(routeId, frequency) {
    const route = routes.find(r => r.id === routeId);
    if (route) {
        route.frequency = Math.max(1, parseInt(frequency) || 1);
        console.log(`📊 Updated route ${route.from.iata}→${route.to.iata} frequency to ${route.frequency}`);

        updateRoutesDisplay();
        updateTripStatistics();
        updateAircraftInputsSeamlessly();
    }
}

function updateRoutesDisplay() {
    const container = document.getElementById('routes-container');
    const noRoutesMsg = document.getElementById('no-routes-message');
    const routesCount = document.getElementById('routes-count');

    if (!container) return;

    if (routes.length === 0) {
        if (noRoutesMsg) {
            noRoutesMsg.classList.remove('d-none');
        }
        container.innerHTML = '';
        if (noRoutesMsg) {
            container.appendChild(noRoutesMsg);
        }
    } else {
        if (noRoutesMsg) {
            noRoutesMsg.classList.add('d-none');
        }

        container.innerHTML = routes.map(route => `
            <div class="route-item bg-secondary bg-opacity-25 rounded p-2 mb-2">
                <div class="d-flex justify-content-between align-items-center">
                    <div class="flex-grow-1">
                        <div class="d-flex align-items-center justify-content-between mb-1">
                            <div class="fw-bold text-warning">${route.from.iata} → ${route.to.iata}</div>
                            <button class="btn btn-sm btn-outline-danger px-2 py-0" onclick="removeRoute(${route.id})" title="Remove route">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                        <div class="small text-muted mb-2">
                            ${route.from.city} → ${route.to.city}
                            <span class="badge bg-primary ms-1">${route.distance.toLocaleString()} nm</span>
                        </div>
                        <div class="d-flex align-items-center justify-content-between">
                            <div class="d-flex align-items-center gap-2">
                                <label class="small text-muted mb-0">Trips:</label>
                                <input type="number" 
                                       class="form-control form-control-sm" 
                                       style="width: 60px; background: #333; border: 1px solid #555; color: white; padding: 2px 6px;"
                                       value="${route.frequency}" 
                                       min="1" 
                                       max="365"
                                       onchange="updateRouteFrequency(${route.id}, this.value)">
                            </div>
                            <span class="badge bg-info small">${(route.frequency * route.distance).toLocaleString()} nm total</span>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
    }

    // Update routes count
    if (routesCount) {
        routesCount.textContent = routes.length;
    }
}

function updateMapWithRoutes() {
    if (!simpleMap) return;

    // Remove existing route lines
    routeLines.forEach(line => {
        simpleMap.removeLayer(line);
    });
    routeLines = [];

    if (routes.length === 0) {
        // Update map legend even when no routes
        if (typeof addMapLegend === 'function') {
            addMapLegend();
        }
        return;
    }

    // Draw all routes with airport squares
    routes.forEach(route => {
        // Create route line with thickness based on frequency
        const routeLine = L.polyline([
            [route.from.lat, route.from.lon],
            [route.to.lat, route.to.lon]
        ], {
            color: '#00A86B', // Updated to use green color
            weight: Math.min(2 + route.frequency, 8), // Thicker lines for more frequent routes
            opacity: 0.8,
            dashArray: '5, 10'
        }).addTo(simpleMap);

        // Add popup to route line
        routeLine.bindPopup(`
            <div style="color: #000;">
                <strong>${route.from.iata} → ${route.to.iata}</strong><br>
                Distance: ${route.distance} NM<br>
                Frequency: ${route.frequency} trips<br>
                Total: ${route.distance * route.frequency} NM<br>
                ${route.from.city} → ${route.to.city}
            </div>
        `);

        routeLines.push(routeLine);

        // Add airport code squares instead of regular markers
        addAirportSquare(route.from);
        addAirportSquare(route.to);
    });

    // Add range circles for longest, average, and custom ranges
    updateRangeCircles();

    // Update map legend
    if (typeof addMapLegend === 'function') {
        addMapLegend();
    }

    // Fit map to show all routes
    if (routes.length > 0) {
        const allPoints = [];
        routes.forEach(route => {
            allPoints.push([route.from.lat, route.from.lon]);
            allPoints.push([route.to.lat, route.to.lon]);
        });

        const bounds = L.latLngBounds(allPoints);
        simpleMap.fitBounds(bounds, { padding: [50, 50] });
    }
}

function addAirportSquare(airport) {
    // Check if this airport square already exists
    const existingSquare = routeLines.find(line =>
        line.options && line.options.airportCode === airport.iata
    );

    if (existingSquare) return; // Don't add duplicate squares

    // Create a custom square marker using DivIcon
    const squareIcon = L.divIcon({
        className: 'airport-square',
        html: `<div style="
            background: #1a1a1a;
            border: 2px solid #00A86B;
            color: #00A86B;
            width: 40px;
            height: 25px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 10px;
            font-family: 'Rajdhani', sans-serif;
            box-shadow: 0 2px 5px rgba(0,0,0,0.3);
        ">${airport.iata}</div>`,
        iconSize: [40, 25],
        iconAnchor: [20, 12]
    });

    const airportMarker = L.marker([airport.lat, airport.lon], {
        icon: squareIcon,
        airportCode: airport.iata // Custom property to identify
    }).addTo(simpleMap);

    airportMarker.options.airportCode = airport.iata; // Store for identification

    airportMarker.bindPopup(`
        <div style="color: #000;">
            <strong>${airport.iata}</strong> - ${airport.name}<br>
            ${airport.city}, ${airport.country}<br>
            <small>Lat: ${airport.lat.toFixed(4)}, Lon: ${airport.lon.toFixed(4)}</small>
        </div>
    `);

    routeLines.push(airportMarker);
}

function updateRangeCircles() {
    if (!window.selectedHomeAirport || routes.length === 0) return;

    const stats = calculateTripStatistics();
    const homeAirport = window.selectedHomeAirport;

    // Remove existing range circles
    routeLines.forEach(line => {
        if (line.options && line.options.isRangeCircle) {
            simpleMap.removeLayer(line);
        }
    });
    routeLines = routeLines.filter(line => !(line.options && line.options.isRangeCircle));

    // Add longest leg circle (Red)
    if (stats.longestLeg > 0) {
        const longestCircle = L.circle([homeAirport.lat, homeAirport.lon], {
            radius: stats.longestLeg * 1852, // Convert NM to meters
            color: '#FF4444',
            weight: 2,
            opacity: 0.7,
            fillColor: '#FF4444',
            fillOpacity: 0.1,
            isRangeCircle: true,
            circleType: 'longest'
        }).addTo(simpleMap);

        longestCircle.bindTooltip(`Longest Leg: ${stats.longestLeg} NM`, {
            permanent: false,
            direction: 'center'
        });

        routeLines.push(longestCircle);
    }

    // Add average leg circle (Blue)
    if (stats.averageLeg > 0) {
        const averageCircle = L.circle([homeAirport.lat, homeAirport.lon], {
            radius: stats.averageLeg * 1852,
            color: '#4488FF',
            weight: 2,
            opacity: 0.7,
            fillColor: '#4488FF',
            fillOpacity: 0.1,
            isRangeCircle: true,
            circleType: 'average'
        }).addTo(simpleMap);

        averageCircle.bindTooltip(`Average Leg: ${Math.round(stats.averageLeg)} NM`, {
            permanent: false,
            direction: 'center'
        });

        routeLines.push(averageCircle);
    }

    // Add custom range circle (White) from range slider
    const rangeSlider = document.getElementById('range-slider');
    if (rangeSlider) {
        const customRange = parseInt(rangeSlider.value);
        const customCircle = L.circle([homeAirport.lat, homeAirport.lon], {
            radius: customRange * 1852,
            color: '#FFFFFF',
            weight: 2,
            opacity: 0.7,
            fillColor: '#FFFFFF',
            fillOpacity: 0.05,
            isRangeCircle: true,
            circleType: 'custom'
        }).addTo(simpleMap);

        customCircle.bindTooltip(`Custom Range: ${customRange} NM`, {
            permanent: false,
            direction: 'center'
        });

        routeLines.push(customCircle);
    }
}

function calculateTripStatistics() {
    if (routes.length === 0) {
        return {
            totalTrips: 0,
            longestLeg: 0,
            averageLeg: 0,
            totalDistance: 0
        };
    }

    const totalTrips = routes.reduce((sum, route) => sum + route.frequency, 0);
    const longestLeg = Math.max(...routes.map(r => r.distance));

    // Calculate weighted average based on frequency
    const totalWeightedDistance = routes.reduce((sum, route) => sum + (route.distance * route.frequency), 0);
    const averageLeg = totalWeightedDistance / totalTrips;

    const totalDistance = routes.reduce((sum, route) => sum + (route.distance * route.frequency), 0);

    return {
        totalTrips,
        longestLeg,
        averageLeg,
        totalDistance
    };
}

function updateTripStatistics() {
    const stats = calculateTripStatistics();

    // Update the information bar
    updateTripStatsBar(stats);

    // Update other UI elements
    updateTripStatisticsDisplay(stats);
}

function updateTripStatsBar(stats) {
    // Update the trip statistics in the trip planning section
    const longestLegDisplay = document.getElementById('longest-leg-display');
    const avgLegDisplay = document.getElementById('avg-leg-display');
    const totalTripsDisplay = document.getElementById('total-trips-display');
    const totalDistanceDisplay = document.getElementById('total-distance-display');

    if (longestLegDisplay) {
        longestLegDisplay.textContent = stats.longestLeg || '0';
        // Add animation for changes
        longestLegDisplay.style.transform = 'scale(1.1)';
        longestLegDisplay.style.color = '#F05545';
        setTimeout(() => {
            longestLegDisplay.style.transform = 'scale(1)';
        }, 200);
    }

    if (avgLegDisplay) {
        avgLegDisplay.textContent = Math.round(stats.averageLeg) || '0';
        // Add animation for changes
        avgLegDisplay.style.transform = 'scale(1.1)';
        avgLegDisplay.style.color = '#F05545';
        setTimeout(() => {
            avgLegDisplay.style.transform = 'scale(1)';
        }, 200);
    }

    if (totalTripsDisplay) {
        totalTripsDisplay.textContent = stats.totalTrips || '0';
        // Add animation for changes
        totalTripsDisplay.style.transform = 'scale(1.1)';
        totalTripsDisplay.style.color = '#F05545';
        setTimeout(() => {
            totalTripsDisplay.style.transform = 'scale(1)';
        }, 200);
    }

    if (totalDistanceDisplay) {
        totalDistanceDisplay.textContent = `${Math.round(stats.totalDistance) || 0} nm`;
    }

    console.log('✅ Trip statistics bar updated with new values');
}

function updateTripStatisticsDisplay(stats) {
    // Update trip statistics display with better formatting
    const totalTripsElement = document.getElementById('total-trips');
    const longestLegElement = document.getElementById('longest-leg');
    const averageLegElement = document.getElementById('average-leg');
    const totalDistanceElement = document.getElementById('total-distance');

    if (totalTripsElement) {
        totalTripsElement.textContent = stats.totalTrips.toLocaleString();
    }

    if (longestLegElement) {
        longestLegElement.textContent = stats.longestLeg > 0 ? stats.longestLeg.toLocaleString() : '0';
    }

    if (averageLegElement) {
        averageLegElement.textContent = stats.averageLeg > 0 ? Math.round(stats.averageLeg).toLocaleString() : '0';
    }

    if (totalDistanceElement) {
        totalDistanceElement.textContent = `${stats.totalDistance.toLocaleString()} nm`;
    }

    // Store data globally for other components
    window.tripPlanningData = stats;

    console.log(`📊 Trip stats updated:`, {
        'Total Trips': stats.totalTrips,
        'Longest Leg': stats.longestLeg + ' nm',
        'Average Leg': Math.round(stats.averageLeg) + ' nm',
        'Total Distance': stats.totalDistance + ' nm'
    });

    // Update range circles if home airport is set
    if (window.selectedHomeAirport) {
        updateRangeCircles();
    }

    // Trigger auto-update event for aircraft inputs
    triggerAutoUpdate(stats);
}

function updateAircraftInputsSeamlessly() {
    // Only update if auto-updates are enabled and this isn't a recursive call
    if (!autoUpdateEnabled || window.updatingInputs) {
        return;
    }

    // Set flag to prevent recursive calls
    window.updatingInputs = true;

    // Save current state before updating
    savePageStateMinimal();

    const stats = calculateTripStatistics();

    // Use CSV Input Linker if available
    if (window.csvInputLinker) {
        const updatedCount = window.csvInputLinker.linkTripPlanningData(stats);
        if (updatedCount > 0) {
            console.log(`🔄 Trip planner linked ${updatedCount} inputs via CSV Input Linker`);
        }
    } else {
        // Fallback to direct input updating
        updateCSVInputsSeamlessly(stats);
    }

    // Remove flag after a delay
    setTimeout(() => {
        window.updatingInputs = false;
    }, 1000);
}

function updateCSVInputsSeamlessly(stats) {
    // Get all potential input fields that could match CSV columns
    const inputMappings = [
        // Trip-related inputs
        { patterns: ['trips', 'num_trips', 'number_of_trips', 'total_trips', 'trip_frequency'], value: stats.totalTrips },
        { patterns: ['yearly_usage', 'annual_usage', 'flight_hours', 'hours_per_year'], value: Math.round(stats.totalTrips * 2.5) }, // Estimate flight hours
        { patterns: ['range_required', 'min_range', 'required_range'], value: stats.longestLeg },
        { patterns: ['average_leg', 'avg_leg', 'typical_leg'], value: stats.averageLeg },
        { patterns: ['longest_leg', 'max_leg', 'maximum_leg'], value: stats.longestLeg }
    ];

    let updatedCount = 0;

    inputMappings.forEach(mapping => {
        mapping.patterns.forEach(pattern => {
            // Search by ID
            let input = document.getElementById(pattern);

            // Search by name if not found by ID
            if (!input) {
                input = document.querySelector(`input[name="${pattern}"]`);
            }

            // Search by data attribute
            if (!input) {
                input = document.querySelector(`input[data-field="${pattern}"]`);
            }

            // Search by partial name match
            if (!input) {
                const inputs = document.querySelectorAll('input[type="number"], input[type="range"]');
                for (const inp of inputs) {
                    if (inp.name && inp.name.toLowerCase().includes(pattern.toLowerCase())) {
                        input = inp;
                        break;
                    }
                }
            }

            if (input && mapping.value > 0) {
                const currentValue = parseFloat(input.value) || 0;

                // Only update if the new value is significantly higher or the field is empty
                if (currentValue === 0 || mapping.value > currentValue * 1.1) {
                    input.value = mapping.value;

                    // Add visual feedback
                    input.style.borderColor = '#F05545';
                    input.style.boxShadow = '0 0 0 0.25rem rgba(240, 85, 69, 0.25)';

                    // Remove feedback after animation
                    setTimeout(() => {
                        input.style.borderColor = '';
                        input.style.boxShadow = '';
                    }, 1500);

                    updatedCount++;

                    // Trigger change event to update any dependent calculations
                    input.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }
        });
    });

    if (updatedCount > 0) {
        console.log(`🔄 Seamlessly updated ${updatedCount} input fields`);
    }
}

function updateAircraftListingsAjax(stats) {
    // Try to update aircraft listings without page refresh
    const currentUrl = new URL(window.location.href);

    // Update URL parameters with new values
    currentUrl.searchParams.set('min_range', stats.longestLeg);
    currentUrl.searchParams.set('yearly_usage', Math.round(stats.totalTrips * 2.5));

    // Trigger a gentle update of the aircraft cards if possible
    const aircraftContainer = document.querySelector('.aircraft-grid') ||
        document.querySelector('#aircraft-container') ||
        document.querySelector('[class*="aircraft"]');

    if (aircraftContainer) {
        // Add a subtle loading indicator
        aircraftContainer.style.opacity = '0.8';
        aircraftContainer.style.transition = 'opacity 0.3s ease';

        // Reset opacity after a brief moment
        setTimeout(() => {
            aircraftContainer.style.opacity = '1';
        }, 500);
    }

    // Update results counter if available
    if (stats.totalTrips > 0) {
        // Dispatch event for other components to update
        document.dispatchEvent(new CustomEvent('tripPlanningUpdated', {
            detail: stats
        }));
    }
}

function triggerAutoUpdate(stats) {
    // Dispatch a custom event for other components to listen to
    const autoUpdateEvent = new CustomEvent('tripPlannerAutoUpdate', {
        detail: {
            longestLeg: stats.longestLeg,
            averageLeg: stats.averageLeg,
            totalTrips: stats.totalTrips,
            totalDistance: stats.totalDistance,
            timestamp: Date.now()
        },
        bubbles: true
    });

    document.dispatchEvent(autoUpdateEvent);

    // Also trigger the old event name for backward compatibility
    const legacyEvent = new CustomEvent('tripPlanningUpdate', {
        detail: {
            longestLeg: stats.longestLeg,
            averageDistance: stats.averageLeg,
            tripCount: stats.totalTrips,
            totalDistance: stats.totalDistance
        },
        bubbles: true
    });

    window.dispatchEvent(legacyEvent);
}

function calculateDistance(lat1, lon1, lat2, lon2) {
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
    const R = 3440;

    // Calculate distance
    return R * c;
}

// Make functions available globally
window.removeRoute = removeRoute;
window.updateRouteFrequency = updateRouteFrequency;

// Update range circles when range slider changes
document.addEventListener('DOMContentLoaded', function () {
    const rangeSlider = document.getElementById('range-slider');
    if (rangeSlider) {
        rangeSlider.addEventListener('input', function () {
            updateRangeCircles();
        });
    }
});

function setupAutoUpdateListeners() {
    // DISABLED - This was causing the refresh loop
    console.log('⚠️ Auto-update listeners disabled to prevent refresh loop');
    return;

    /* COMMENTED OUT TO PREVENT REFRESH LOOP
    // Listen for form submissions to preserve trip planning data
    document.addEventListener('submit', function (e) {
        if (window.tripPlanningData) {
            sessionStorage.setItem('tripPlanningData', JSON.stringify(window.tripPlanningData));
        }
        // Save complete page state
        savePageState();
    });

    // Restore trip planning data on page load
    const savedData = sessionStorage.getItem('tripPlanningData');
    if (savedData) {
        try {
            window.tripPlanningData = JSON.parse(savedData);
            console.log('📊 Restored trip planning data:', window.tripPlanningData);
        } catch (e) {
            console.warn('Could not restore trip planning data:', e);
        }
    }

    // Listen for aircraft analysis form changes but don't auto-refresh
    const aircraftForm = document.querySelector('form');
    if (aircraftForm) {
        aircraftForm.addEventListener('change', function (e) {
            // Only preserve state, don't trigger auto-refresh
            if (!e.target.hasAttribute('data-auto-updated')) {
                // Save current state but don't refresh
                savePageState();

                // Still allow manual updates from trip planning
                setTimeout(() => {
                    updateAircraftInputsSeamlessly();
                }, 500);
            }
        });
    }

    // Set up range slider auto-update
    const rangeSlider = document.getElementById('range-slider');
    if (rangeSlider) {
        rangeSlider.addEventListener('input', function () {
            updateRangeCircles();
            // Save state when slider changes
            savePageState();
        });

        // Auto-update range slider from trip planning if it's at default value
        if (window.tripPlanningData && window.tripPlanningData.longestLeg > 0) {
            const currentValue = parseInt(rangeSlider.value);
            if (currentValue <= 500) { // Default value
                rangeSlider.value = window.tripPlanningData.longestLeg;
                updateRangeCircles();
            }
        }
    }

    // Add manual refresh button functionality
    addManualRefreshControls();
    */
}

function addManualRefreshControls() {
    // Find the aircraft selection criteria section
    const criteriaSection = document.querySelector('.card .card-header h4');
    if (criteriaSection && criteriaSection.textContent.includes('Aircraft Selection Criteria')) {
        const cardHeader = criteriaSection.parentElement;

        // Check if refresh button already exists
        if (!document.getElementById('manual-refresh-btn')) {
            const refreshBtn = document.createElement('button');
            refreshBtn.id = 'manual-refresh-btn';
            refreshBtn.type = 'button';
            refreshBtn.className = 'btn btn-success btn-sm ms-2';
            refreshBtn.innerHTML = '<i class="fas fa-sync-alt me-1"></i>Update Aircraft List';
            refreshBtn.title = 'Apply current settings to aircraft list';

            refreshBtn.addEventListener('click', function () {
                // Save current state first
                savePageState();

                // Show loading indicator
                this.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Updating...';
                this.disabled = true;

                // Apply current filters with a small delay
                setTimeout(() => {
                    const form = document.querySelector('form[method="GET"]');
                    if (form) {
                        // Get current trip planning stats
                        const stats = calculateTripStatistics();

                        // Update hidden inputs or create them if needed
                        updateFormWithTripData(form, stats);

                        // Submit form
                        form.submit();
                    } else {
                        // Fallback: refresh with current URL parameters
                        window.location.reload();
                    }
                }, 100);
            });

            cardHeader.appendChild(refreshBtn);
        }
    }

    // Also add a subtle hint about the manual refresh
    const routeControls = document.querySelector('#add-route-btn')?.parentElement;
    if (routeControls && !document.getElementById('refresh-hint')) {
        const hint = document.createElement('small');
        hint.id = 'refresh-hint';
        hint.className = 'text-muted d-block mt-2';
        hint.innerHTML = '<i class="fas fa-info-circle me-1"></i>Trip planning data auto-updates inputs. Use "Update Aircraft List" to refresh results.';
        routeControls.appendChild(hint);
    }
}

function updateFormWithTripData(form, stats) {
    // Helper function to create or update hidden inputs with trip planning data
    const updateHiddenInput = (name, value) => {
        let input = form.querySelector(`input[name="${name}"]`);
        if (!input) {
            input = document.createElement('input');
            input.type = 'hidden';
            input.name = name;
            form.appendChild(input);
        }
        input.value = value;
    };

    // Update form with current trip planning data
    if (stats.longestLeg > 0) {
        updateHiddenInput('min_range', stats.longestLeg);
        updateHiddenInput('required_range', stats.longestLeg);
    }

    if (stats.totalTrips > 0) {
        updateHiddenInput('trips', stats.totalTrips);
        updateHiddenInput('yearly_usage', stats.totalTrips);
    }

    if (stats.averageLeg > 0) {
        updateHiddenInput('avg_trip_length', Math.round(stats.averageLeg));
    }

    // Preserve current visible form values
    const visibleInputs = form.querySelectorAll('input:not([type="hidden"]), select, textarea');
    visibleInputs.forEach(input => {
        if (input.name && input.value) {
            updateHiddenInput(input.name, input.value);
        }
    });
}

function savePageStateMinimal() {
    try {
        const pageState = {
            timestamp: Date.now(),
            routes: routes,
            tripData: window.tripPlanningData || {}
        };

        sessionStorage.setItem('jetFinderTripData', JSON.stringify(pageState));
        console.log('💾 Minimal page state saved');
    } catch (e) {
        console.warn('Could not save minimal page state:', e);
    }
}

function restorePageStateMinimal() {
    try {
        const savedState = sessionStorage.getItem('jetFinderTripData');
        if (savedState) {
            const pageState = JSON.parse(savedState);

            // Only restore if saved within last 5 minutes
            if (Date.now() - pageState.timestamp < 300000) {
                console.log('🔄 Restoring minimal trip data:', pageState);

                // Restore routes only
                if (pageState.routes && Array.isArray(pageState.routes)) {
                    routes = pageState.routes;
                    updateRoutesDisplay();
                    updateMapWithRoutes();
                    updateTripStatistics();
                }

                // Restore trip data
                if (pageState.tripData) {
                    window.tripPlanningData = pageState.tripData;
                }

                return true;
            }
        }
    } catch (e) {
        console.warn('Could not restore minimal page state:', e);
    }
    return false;
}

function restoreFormData(formData) {
    // DISABLED to prevent change event loops
    console.log('⚠️ Form data restoration disabled to prevent refresh loop');
    return;

    /* COMMENTED OUT TO PREVENT REFRESH LOOP
    Object.keys(formData).forEach(key => {
        const input = document.getElementById(key) || document.querySelector(`[name="${key}"]`);
        if (input) {
            if (input.type === 'checkbox') {
                input.checked = formData[key];
            } else if (input.type === 'radio') {
                if (input.value === formData[key]) {
                    input.checked = true;
                }
            } else {
                input.value = formData[key];
            }

            // Trigger change event to update dependent elements
            input.dispatchEvent(new Event('change', { bubbles: true }));
        }
    });
    */
}

function setupMinimalStatePreservation() {
    console.log('🔄 Setting up minimal state preservation');

    // Save state before page unload only
    window.addEventListener('beforeunload', function () {
        savePageStateMinimal();
    });
}

function setupStatePreservation() {
    // DISABLED - Use minimal version instead
    console.log('⚠️ Full state preservation disabled to prevent refresh loop');
    return;

    /* COMMENTED OUT TO PREVENT REFRESH LOOP
    console.log('🔄 Setting up state preservation');

    // Save state before form submissions
    document.addEventListener('submit', function (e) {
        console.log('💾 Saving state before form submission');
        savePageState();
    });

    // Save state before major button clicks
    document.addEventListener('click', function (e) {
        const target = e.target.closest('button, a');
        if (target) {
            // Save state for buttons that might cause navigation or major changes
            if (target.type === 'submit' ||
                target.classList.contains('btn-primary') ||
                target.classList.contains('btn-danger') ||
                target.href ||
                target.id === 'search-aircraft-btn' ||
                target.id === 'apply-filters-btn') {

                console.log('💾 Saving state before button click:', target.id || target.className);
                savePageState();
            }
        }
    });

    // Save state before page unload
    window.addEventListener('beforeunload', function () {
        savePageState();
    });

    // Save state periodically (every 30 seconds) while user is active
    let stateTimer = setInterval(() => {
        if (routes.length > 0 || Object.keys(getFormData()).length > 0) {
            savePageState();
        }
    }, 30000);

    // Clear timer when page is hidden
    document.addEventListener('visibilitychange', function () {
        if (document.hidden) {
            savePageState();
            clearInterval(stateTimer);
        } else {
            // Restart timer when page becomes visible again
            stateTimer = setInterval(() => {
                if (routes.length > 0 || Object.keys(getFormData()).length > 0) {
                    savePageState();
                }
            }, 30000);
        }
    });

    // Override form submission to save state first
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        const originalSubmit = form.submit;
        form.submit = function () {
            savePageState();
            originalSubmit.call(this);
        };
    });
    */
}

console.log('✅ Enhanced trip planner setup complete - Auto-refresh disabled!'); 