/**
 * Jet Marketplace - Listings JavaScript
 * Handles marketplace listing interactions and integration with Jet Finder
 */

document.addEventListener('DOMContentLoaded', function () {
    console.log('DOM fully loaded, initializing components...');

    // Initialize filter functionality
    initFilters();

    // Initialize favorite buttons
    initFavoriteButtons();

    // Initialize Jet Finder integration
    initJetFinderIntegration();

    // Initialize sorting functionality
    initSorting();

    // Initialize map right away (no delay)
    console.log('Initializing map...');
    initMap();

    // Setup airport search for all inputs
    console.log('Setting up airport search...');
    setupAirportSearch('home-airport-search', 'home-airport-list', 'home-airport-results', 'search-home-btn');
    setupAirportSearch('from-airport', 'from-airport-list', 'from-airport-results', 'search-from-btn');
    setupAirportSearch('to-airport', 'to-airport-list', 'to-airport-results', 'search-to-btn');

    // Set up range slider event handler
    const rangeSlider = document.getElementById('range-slider');
    if (rangeSlider) {
        rangeSlider.addEventListener('input', function () {
            const value = this.value;
            const rangeValueEl = document.getElementById('range-value');
            if (rangeValueEl) {
                rangeValueEl.textContent = value.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",") + ' NM';
            }
            // Update range circle on map
            drawRangeCircle(parseInt(value));
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
            }
        });
    }

    // Connect home airport to the hidden form input
    document.getElementById('home-airport-search').addEventListener('change', function () {
        if (selectedHomeAirport) {
            document.getElementById('home_airport').value = this.value;
        }
    });

    // Ensure map is properly initialized after the page is fully loaded
    window.addEventListener('load', function () {
        // Force map refresh after everything is loaded
        setTimeout(() => {
            if (map) {
                map.invalidateSize();
                console.log('Map size refreshed after complete page load');
            }
        }, 500);
    });
});

/**
 * Initialize filter functionality
 */
function initFilters() {
    // Clear individual filters
    document.querySelectorAll('.filter-pills .badge a').forEach(button => {
        button.addEventListener('click', function (e) {
            e.preventDefault();
            const badge = this.closest('.badge');

            // Add a fade-out animation before removing
            badge.classList.add('animate__animated', 'animate__fadeOut');
            badge.addEventListener('animationend', () => {
                badge.remove();
                // Here we would normally update the results based on removed filter
                updateListings();
            });
        });
    });

    // Clear all filters
    const clearAllButton = document.querySelector('.filter-pills .badge a:contains("Clear All Filters")');
    if (clearAllButton) {
        clearAllButton.addEventListener('click', function (e) {
            e.preventDefault();
            document.querySelectorAll('.filter-pills .badge:not(:last-child)').forEach(badge => {
                badge.remove();
            });

            // Here we would reset all filters and update results
            updateListings();
        });
    }

    // Advanced search modal apply button
    const applyFiltersButton = document.querySelector('#advancedSearchModal .btn-danger');
    if (applyFiltersButton) {
        applyFiltersButton.addEventListener('click', function () {
            // Collect all filter values from the form
            const filters = collectFormFilters();

            // Update the filter pills based on the selected filters
            updateFilterPills(filters);

            // Close the modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('advancedSearchModal'));
            modal.hide();

            // Update the listings based on the new filters
            updateListings(filters);
        });
    }
}

/**
 * Collect filter values from the advanced search form
 */
function collectFormFilters() {
    const filters = {};

    // Example: Get category
    const category = document.getElementById('aircraft-category').value;
    if (category) filters.category = category;

    // Example: Get manufacturer
    const manufacturer = document.getElementById('manufacturer').value;
    if (manufacturer) filters.manufacturer = manufacturer;

    // Example: Get model
    const model = document.getElementById('model').value;
    if (model) filters.model = model;

    // Example: Get year range
    const yearInputs = document.querySelectorAll('input[placeholder*="Year"]');
    if (yearInputs.length >= 2) {
        const minYear = yearInputs[0].value;
        const maxYear = yearInputs[1].value;

        if (minYear && maxYear) {
            filters.yearRange = {
                min: parseInt(minYear),
                max: parseInt(maxYear)
            };
        } else if (minYear) {
            filters.yearRange = { min: parseInt(minYear) };
        } else if (maxYear) {
            filters.yearRange = { max: parseInt(maxYear) };
        }
    }

    // Add more filter collection logic as needed

    return filters;
}

/**
 * Update filter pills based on selected filters
 */
function updateFilterPills(filters) {
    const pillsContainer = document.querySelector('.filter-pills');
    const clearAllButton = document.querySelector('.filter-pills .badge:last-child');

    // Remove existing filter pills except the "Clear All" button
    document.querySelectorAll('.filter-pills .badge:not(:last-child)').forEach(badge => {
        badge.remove();
    });

    // Create new pills based on the filters
    for (const [key, value] of Object.entries(filters)) {
        let pillText = '';

        switch (key) {
            case 'category':
                pillText = value.charAt(0).toUpperCase() + value.slice(1);
                break;
            case 'manufacturer':
                pillText = value.charAt(0).toUpperCase() + value.slice(1);
                break;
            case 'model':
                pillText = `Model: ${value}`;
                break;
            case 'yearRange':
                if (value.min && value.max) {
                    pillText = `Year: ${value.min}-${value.max}`;
                } else if (value.min) {
                    pillText = `Year: ≥ ${value.min}`;
                } else if (value.max) {
                    pillText = `Year: ≤ ${value.max}`;
                }
                break;
            // Add more cases as needed
        }

        if (pillText) {
            const pill = document.createElement('span');
            pill.className = 'badge rounded-pill bg-danger me-2 mb-2 animate__animated animate__fadeIn';
            pill.innerHTML = `
                <span class="fw-normal">${pillText}</span> 
                <a href="#" class="text-white ms-1" data-filter="${key}"><i class="fas fa-times-circle"></i></a>
            `;

            // Insert the pill before the "Clear All" button
            pillsContainer.insertBefore(pill, clearAllButton);

            // Add click event for removing the filter
            pill.querySelector('a').addEventListener('click', function (e) {
                e.preventDefault();
                pill.classList.add('animate__fadeOut');
                pill.addEventListener('animationend', () => {
                    pill.remove();
                    // Here we would update results based on removed filter
                    updateListings();
                });
            });
        }
    }
}

/**
 * Initialize favorite button functionality
 */
function initFavoriteButtons() {
    document.querySelectorAll('.favorite-btn').forEach(btn => {
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            const icon = this.querySelector('i');
            if (icon.classList.contains('far')) {
                icon.classList.remove('far');
                icon.classList.add('fas');
                icon.style.color = '#F05545';
            } else {
                icon.classList.remove('fas');
                icon.classList.add('far');
                icon.style.color = '';
            }
        });
    });
}

/**
 * Initialize Jet Finder integration with filters
 */
function initJetFinderIntegration() {
    console.log('Initializing Jet Finder integration');

    // Get references to Jet Finder inputs
    const rangeSlider = document.getElementById('range-slider');
    const rangeValue = document.getElementById('range-value');
    const homeAirportInput = document.getElementById('home-airport-search');
    const fromAirportInput = document.getElementById('from-airport');
    const toAirportInput = document.getElementById('to-airport');

    // Connect range slider to marketplace filter
    if (rangeSlider && rangeValue) {
        // Set initial value based on marketplace filter if available
        const minRangeSelect = document.getElementById('min_range');
        if (minRangeSelect) {
            const selectedRange = minRangeSelect.value || '1000';
            rangeSlider.value = selectedRange;
            rangeValue.textContent = selectedRange.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",") + ' NM';

            // Draw initial range circle if home airport is set
            if (selectedHomeAirport) {
                drawRangeCircle(parseInt(selectedRange));
            }
        }

        // Update marketplace filter when range slider changes
        rangeSlider.addEventListener('change', function () {
            const value = this.value;

            // Update the min_range select
            if (minRangeSelect) {
                // Find closest option value
                const options = Array.from(minRangeSelect.options).map(opt => parseInt(opt.value));
                const closestOption = options.reduce((prev, curr) => {
                    return (Math.abs(curr - value) < Math.abs(prev - value) ? curr : prev);
                }, Infinity);

                minRangeSelect.value = closestOption;
                console.log(`Updated min_range to: ${closestOption}`);

                // Auto-submit the form when range changes
                setTimeout(() => {
                    document.getElementById('aircraft-finder-form').submit();
                }, 500);
            }
        });
    }

    // Connect the "Add Route" button to update filters
    const addRouteBtn = document.getElementById('add-route-btn');
    if (addRouteBtn) {
        addRouteBtn.addEventListener('click', function () {
            const fromInput = document.getElementById('from-airport');
            const toInput = document.getElementById('to-airport');

            if (!fromInput || !toInput) return;

            const from = fromInput.value.trim();
            const to = toInput.value.trim();

            if (!from || !to) {
                alert('Please select both origin and destination airports');
                return;
            }

            // Calculate route distance
            calculateRouteDistance(from, to).then(distance => {
                // Update the range slider with the calculated distance
                if (rangeSlider && distance) {
                    const adjustedDistance = Math.min(Math.ceil(distance * 1.1), rangeSlider.max);
                    rangeSlider.value = adjustedDistance;
                    rangeValue.textContent = adjustedDistance.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",") + ' NM';

                    // Update the min_range select
                    const minRangeSelect = document.getElementById('min_range');
                    if (minRangeSelect) {
                        // Find closest option value
                        const options = Array.from(minRangeSelect.options).map(opt => parseInt(opt.value));
                        const closestOption = options.reduce((prev, curr) => {
                            return (Math.abs(curr - adjustedDistance) < Math.abs(prev - adjustedDistance) ? curr : prev);
                        }, Infinity);

                        minRangeSelect.value = closestOption;
                    }

                    // Draw route on map
                    drawRoute(from, to, distance);

                    // Update search results automatically
                    setTimeout(() => {
                        document.getElementById('aircraft-finder-form').submit();
                    }, 500);
                }
            });
        });
    }

    // Add visual cues to show connections between Jet Finder and marketplace
    addConnectionIndicators();
}

// Global variables to store selected airports
let selectedHomeAirport = null;
let selectedFromAirport = null;
let selectedToAirport = null;

// Function to calculate the Haversine distance between two points
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

// Function to calculate route distance
function calculateRouteDistance(from, to) {
    // If we have both airports with coordinates, calculate the actual distance
    if (selectedFromAirport && selectedFromAirport.lat && selectedFromAirport.lon &&
        selectedToAirport && selectedToAirport.lat && selectedToAirport.lon) {

        const distance = haversineDistance(
            selectedFromAirport.lat,
            selectedFromAirport.lon,
            selectedToAirport.lat,
            selectedToAirport.lon
        );

        return Promise.resolve(Math.round(distance));
    }

    // Fallback to demo values if airport data is incomplete
    return new Promise(resolve => {
        // Extract airport codes if possible
        const fromMatch = from.match(/([A-Z]{3,4})/);
        const toMatch = to.match(/([A-Z]{3,4})/);

        // Demo distances based on common airport pairs
        const distances = {
            'JFK-LAX': 2150,
            'LAX-JFK': 2150,
            'JFK-BOS': 185,
            'BOS-JFK': 185,
            'LAX-BOS': 2300,
            'BOS-LAX': 2300
        };

        if (fromMatch && toMatch) {
            const fromCode = fromMatch[1];
            const toCode = toMatch[1];
            const key = `${fromCode}-${toCode}`;

            if (distances[key]) {
                resolve(distances[key]);
                return;
            }
        }

        // Default distance if no match
        setTimeout(() => {
            resolve(Math.floor(Math.random() * 2000) + 500);
        }, 300);
    });
}

// Function to draw range circle on map
function drawRangeCircle(rangeNM) {
    if (typeof map === 'undefined' || !map) return;

    // Clear existing range circles
    if (window.rangeCircle) {
        map.removeLayer(window.rangeCircle);
    }

    // Get home airport location, or use default
    let center = [39.8283, -98.5795]; // Default: center of US

    if (selectedHomeAirport && selectedHomeAirport.lat && selectedHomeAirport.lon) {
        center = [selectedHomeAirport.lat, selectedHomeAirport.lon];
    }

    // Convert nautical miles to meters (1 NM = 1852 meters)
    const radiusMeters = rangeNM * 1852;

    // Create and add the circle
    window.rangeCircle = L.circle(center, {
        radius: radiusMeters,
        color: '#dc3545',
        fillColor: '#dc354580',
        fillOpacity: 0.2
    }).addTo(map);

    // Center the map on the circle
    map.setView(center, getZoomForRadius(radiusMeters));
}

// Function to draw a route on the map
function drawRoute(from, to, distance) {
    if (typeof map === 'undefined' || !map) return;

    // Clear existing routes
    if (window.routeLine) {
        map.removeLayer(window.routeLine);
    }

    // Default coordinates in case we don't have the airports
    let fromCoords = [39.8283, -98.5795];
    let toCoords = [39.8283 + 5, -98.5795 + 5];

    // Use actual coordinates if available
    if (selectedFromAirport && selectedFromAirport.lat && selectedFromAirport.lon) {
        fromCoords = [selectedFromAirport.lat, selectedFromAirport.lon];
    }

    if (selectedToAirport && selectedToAirport.lat && selectedToAirport.lon) {
        toCoords = [selectedToAirport.lat, selectedToAirport.lon];
    }

    // Create route line
    window.routeLine = L.polyline([fromCoords, toCoords], {
        color: '#dc3545',
        weight: 3,
        opacity: 0.7,
        dashArray: '5, 10'
    }).addTo(map);

    // Add markers for the airports
    L.marker(fromCoords).addTo(map)
        .bindPopup(`<b>${from}</b><br>Origin`);

    L.marker(toCoords).addTo(map)
        .bindPopup(`<b>${to}</b><br>Destination<br>${distance} NM`);

    // Fit map to show the route
    map.fitBounds(window.routeLine.getBounds(), { padding: [50, 50] });
}

// Helper function to determine appropriate zoom level for a radius
function getZoomForRadius(radius) {
    // Simple formula to estimate zoom level based on circle radius
    return Math.max(1, Math.min(15, Math.round(14 - Math.log(radius / 10000) / Math.log(2))));
}

// Function to select an aircraft and highlight it
function selectAircraft(aircraftId) {
    // Find the aircraft in the listings
    const aircraftCards = document.querySelectorAll('.listing-card');
    let found = false;

    aircraftCards.forEach(card => {
        // Reset all cards first
        card.classList.remove('border-danger');
        card.classList.add('border-secondary');

        // Check if this is the selected aircraft
        const modelText = card.querySelector('h5').textContent.toLowerCase();
        if (modelText.includes(aircraftId.replace(/-/g, ' '))) {
            card.classList.remove('border-secondary');
            card.classList.add('border-danger');
            card.scrollIntoView({ behavior: 'smooth', block: 'center' });
            found = true;
        }
    });

    // If not found in visible listings, we could trigger a search
    if (!found) {
        // In a real implementation, we would update search filters
        console.log('Aircraft not found in current listings:', aircraftId);
    }
}

// Airport search functionality
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
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.json();
            })
            .then(airports => {
                console.log(`Found ${airports.length} airports matching "${query}"`);
                resultsList.innerHTML = '';

                if (airports.length === 0) {
                    resultsList.innerHTML = '<div class="list-group-item bg-dark text-white">No airports found</div>';
                    return;
                }

                airports.forEach(airport => {
                    console.log(`Adding airport: ${airport.iata} - ${airport.name}`);
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
                        console.log(`Selected airport: ${airport.iata} - ${airport.name}`);
                        input.value = `${airport.iata} - ${airport.name}`;
                        resultsContainer.classList.add('d-none');

                        // Store the selected airport based on which input was used
                        if (inputId === 'home-airport-search') {
                            selectedHomeAirport = airport;
                            console.log('Set selectedHomeAirport:', selectedHomeAirport);

                            // Update the hidden input for home airport if it exists
                            const homeAirportInput = document.getElementById('home_airport');
                            if (homeAirportInput) {
                                homeAirportInput.value = input.value;
                                console.log('Updated home_airport hidden input:', homeAirportInput.value);
                            }

                            const rangeValue = document.getElementById('range-slider')?.value || 1000;
                            drawRangeCircle(rangeValue);
                        } else if (inputId === 'from-airport') {
                            selectedFromAirport = airport;
                            console.log('Set selectedFromAirport:', selectedFromAirport);

                            // Update the hidden input for trip origin if it exists
                            const tripOriginInput = document.getElementById('trip_origin');
                            if (tripOriginInput) {
                                tripOriginInput.value = input.value;
                                console.log('Updated trip_origin hidden input:', tripOriginInput.value);
                            }
                        } else if (inputId === 'to-airport') {
                            selectedToAirport = airport;
                            console.log('Set selectedToAirport:', selectedToAirport);

                            // Update the hidden input for trip destination if it exists
                            const tripDestinationInput = document.getElementById('trip_destination');
                            if (tripDestinationInput) {
                                tripDestinationInput.value = input.value;
                                console.log('Updated trip_destination hidden input:', tripDestinationInput.value);
                            }
                        }

                        // If we have both from and to airports, calculate distance
                        if (selectedFromAirport && selectedToAirport) {
                            calculateRouteDistance(input.value, input.value).then(distance => {
                                if (distance) {
                                    console.log(`Calculated distance: ${distance} NM`);
                                    drawRoute(
                                        `${selectedFromAirport.iata} - ${selectedFromAirport.name}`,
                                        `${selectedToAirport.iata} - ${selectedToAirport.name}`,
                                        distance
                                    );
                                }
                            });
                        }
                    });

                    resultsList.appendChild(item);
                });
            })
            .catch(error => {
                console.error('Error searching airports:', error);
                resultsList.innerHTML = `<div class="list-group-item bg-dark text-white">Error searching airports: ${error.message}</div>`;
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
 * Initialize sorting functionality
 */
function initSorting() {
    const sortSelect = document.getElementById('sort-select');
    if (sortSelect) {
        sortSelect.addEventListener('change', function () {
            const sortValue = this.value;

            // Set the hidden sort input
            document.getElementById('sort').value = sortValue;

            // Update the URL with the new sort parameter
            const currentUrl = new URL(window.location.href);
            currentUrl.searchParams.set('sort', sortValue);

            // Simulate a form submission
            document.getElementById('aircraft-finder-form').submit();
        });
    }
}

/**
 * Update listings based on filters and sorting
 */
function updateListings(filters = {}) {
    // This would normally make an API call to get filtered and sorted results
    // For demonstration, we'll just console log the filters
    console.log('Updating listings with filters:', filters);

    // Simulate a loading delay
    showLoadingOverlay();

    // In a real implementation, you would:
    // 1. Make an API call to get filtered data
    // 2. Update the DOM with the new listings
    // 3. Update pagination if needed

    setTimeout(() => {
        // For demo, let's just pretend we updated the listings
        hideLoadingOverlay();
    }, 800);
}

/**
 * Show a toast notification
 */
function showToast(message) {
    console.log('Toast:', message);
    // For compatibility with the existing codebase, we'll use the console
    // In a real implementation, you would show a visual toast notification
}

/**
 * Show loading overlay
 */
function showLoadingOverlay() {
    // Check if overlay already exists
    if (document.querySelector('.loading-overlay')) return;

    // Create loading overlay
    const overlay = document.createElement('div');
    overlay.className = 'loading-overlay position-fixed top-0 start-0 w-100 h-100 d-flex justify-content-center align-items-center';
    overlay.style.backgroundColor = 'rgba(0, 0, 0, 0.7)';
    overlay.style.zIndex = '9999';

    const spinner = document.createElement('div');
    spinner.className = 'spinner-border text-danger';
    spinner.setAttribute('role', 'status');

    const span = document.createElement('span');
    span.className = 'visually-hidden';
    span.textContent = 'Loading...';

    spinner.appendChild(span);
    overlay.appendChild(spinner);
    document.body.appendChild(overlay);

    // Add fade-in animation
    setTimeout(() => {
        overlay.style.opacity = '1';
    }, 10);
}

/**
 * Hide loading overlay
 */
function hideLoadingOverlay() {
    const overlay = document.querySelector('.loading-overlay');
    if (!overlay) return;

    // Add fade-out animation
    overlay.style.opacity = '0';

    // Remove from DOM after animation
    setTimeout(() => {
        overlay.remove();
    }, 300);
}

// Initialize map
let map;
function initMap() {
    // Don't initialize if already exists
    if (typeof map !== 'undefined' && map) {
        // If map exists but needs refresh, just invalidate size
        map.invalidateSize();
        console.log('Map refreshed');
        return;
    }

    // Get the map element
    const mapElement = document.getElementById('map');
    if (!mapElement) {
        console.error('Map element not found');
        return;
    }

    try {
        // Make sure Leaflet is loaded
        if (typeof L === 'undefined') {
            console.error('Leaflet library not loaded');
            return;
        }

        console.log('Initializing map...');

        // Initialize Leaflet map
        map = L.map('map', {
            center: [39.8283, -98.5795], // Center of US
            zoom: 4,
            worldCopyJump: true
        });

        // Add dark tile layer
        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            subdomains: 'abcd',
            maxZoom: 19
        }).addTo(map);

        // Add scale control
        L.control.scale({
            imperial: false,
            position: 'bottomleft'
        }).addTo(map);

        // Force a recalculation of map size
        setTimeout(() => {
            map.invalidateSize();
            console.log('Map size recalculated');
        }, 200);

        console.log('Map initialized successfully');
    } catch (error) {
        console.error('Error initializing map:', error);
    }
}

/**
 * Add visual indicators to show connections between Jet Finder tools and marketplace filters
 */
function addConnectionIndicators() {
    // Add badges to show connections
    const minRangeSelect = document.getElementById('min_range');
    if (minRangeSelect) {
        const badge = document.createElement('span');
        badge.className = 'badge bg-danger ms-2 d-inline-block';
        badge.innerHTML = '<i class="fas fa-exchange-alt me-1"></i> Connects with Range Calculator';

        // Add badge after the select element
        minRangeSelect.parentNode.appendChild(badge);
    }

    // Add info tooltips to explain integration
    const tooltips = [
        { selector: '#home-airport-search', text: 'Sets your home base for aircraft range calculations' },
        { selector: '#from-airport', text: 'Origin airport for trip planning' },
        { selector: '#to-airport', text: 'Destination airport for trip planning' },
        { selector: '#range-slider', text: 'Adjusts minimum range filter automatically' },
        { selector: '#add-route-btn', text: 'Updates range filter based on required trip distance' }
    ];

    // Add tooltip info icons
    tooltips.forEach(tooltip => {
        const element = document.querySelector(tooltip.selector);
        if (element) {
            const infoIcon = document.createElement('span');
            infoIcon.className = 'ms-2 text-danger';
            infoIcon.innerHTML = '<i class="fas fa-info-circle"></i>';
            infoIcon.title = tooltip.text;
            infoIcon.setAttribute('data-bs-toggle', 'tooltip');
            infoIcon.setAttribute('data-bs-placement', 'top');

            // For inputs, add after the parent label
            const label = element.closest('.mb-3')?.querySelector('.form-label');
            if (label) {
                label.appendChild(infoIcon);
            } else if (element.id === 'add-route-btn') {
                // For buttons, add inside
                element.appendChild(document.createTextNode(' '));
                element.appendChild(infoIcon);
            }
        }
    });

    // Initialize tooltips
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        const tooltipElements = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        tooltipElements.forEach(el => new bootstrap.Tooltip(el));
    }
} 