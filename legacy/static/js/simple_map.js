/**
 * Simple Map - Limited to one world without infinite scrolling
 */

console.log('🗺️ Loading Simple Map...');

let simpleMap = null;
let homeMarker = null;
let fromMarker = null;
let toMarker = null;
let rangeCircle = null;

document.addEventListener('DOMContentLoaded', function () {
    console.log('🗺️ Setting up simple map...');

    // Initialize map if container exists
    const mapContainer = document.getElementById('map');
    if (!mapContainer) {
        console.log('❌ No map container found');
        return;
    }

    try {
        // Create map with proper bounds to prevent infinite scrolling
        simpleMap = L.map('map', {
            center: [30, 0], // Center of the world
            zoom: 2,
            minZoom: 2,
            maxZoom: 12,
            // Prevent infinite scrolling
            worldCopyJump: false,
            maxBounds: [
                [-90, -180], // Southwest corner
                [90, 180]    // Northeast corner
            ],
            maxBoundsViscosity: 1.0 // Keep the map strictly within bounds
        });

        // Add tile layer
        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
            subdomains: 'abcd',
            maxZoom: 19,
            // Prevent wrapping
            noWrap: true
        }).addTo(simpleMap);

        console.log('✅ Simple map initialized successfully');

        // Listen for airport selections
        setupMapUpdates();

    } catch (error) {
        console.error('❌ Map initialization error:', error);
    }
});

function setupMapUpdates() {
    // Update map when airports are selected
    const originalSetHomeAirport = window.setHomeAirport;
    window.setHomeAirport = function (airport) {
        console.log('🏠 Updating map for home airport:', airport);

        // Remove existing home marker
        if (homeMarker) {
            simpleMap.removeLayer(homeMarker);
        }

        // Add new home marker
        homeMarker = L.marker([airport.lat, airport.lon], {
            title: `Home: ${airport.name}`
        }).addTo(simpleMap);

        homeMarker.bindPopup(`
            <div style="color: #000;">
                <strong>🏠 Home Airport</strong><br>
                <strong>${airport.iata}</strong> - ${airport.name}<br>
                ${airport.city}, ${airport.country}
            </div>
        `);

        // Center map on home airport
        simpleMap.setView([airport.lat, airport.lon], 6);

        // Draw range circle if range slider exists
        const rangeSlider = document.getElementById('range-slider');
        if (rangeSlider) {
            drawRangeCircle(airport, parseInt(rangeSlider.value));
        }

        // Call original function if it exists
        if (originalSetHomeAirport && typeof originalSetHomeAirport === 'function') {
            originalSetHomeAirport(airport);
        }
    };
}

function drawRangeCircle(airport, rangeNM) {
    if (!simpleMap || !airport) return;

    console.log(`🎯 Drawing range circle: ${rangeNM} NM from ${airport.iata}`);

    // Remove existing range circle
    if (rangeCircle) {
        simpleMap.removeLayer(rangeCircle);
    }

    // Convert nautical miles to meters (1 NM = 1852 meters)
    const rangeMeters = rangeNM * 1852;

    // Create range circle
    rangeCircle = L.circle([airport.lat, airport.lon], {
        radius: rangeMeters,
        color: '#F05545',
        weight: 2,
        opacity: 0.8,
        fillColor: '#F05545',
        fillOpacity: 0.1
    }).addTo(simpleMap);

    // Add tooltip
    rangeCircle.bindTooltip(`Range: ${rangeNM} NM`, {
        permanent: false,
        direction: 'center'
    });
}

// Update range circle when slider changes
document.addEventListener('DOMContentLoaded', function () {
    const rangeSlider = document.getElementById('range-slider');
    if (rangeSlider) {
        rangeSlider.addEventListener('input', function () {
            const rangeValue = parseInt(this.value);

            // Update display
            const rangeValueEl = document.getElementById('range-value');
            if (rangeValueEl) {
                rangeValueEl.textContent = rangeValue;
            }

            // Update circle if home airport is set
            if (window.selectedHomeAirport) {
                drawRangeCircle(window.selectedHomeAirport, rangeValue);
            }
        });
    }
});

// Global function to show aircraft range (called from aircraft cards)
window.showAircraftRange = function (range, aircraftId) {
    console.log(`🛩️ Showing aircraft range: ${range} NM`);

    // Update range slider
    const rangeSlider = document.getElementById('range-slider');
    const rangeValueEl = document.getElementById('range-value');

    if (rangeSlider) {
        rangeSlider.value = range;
        if (rangeValueEl) {
            rangeValueEl.textContent = range;
        }
    }

    // Update circle if home airport is set
    if (window.selectedHomeAirport) {
        drawRangeCircle(window.selectedHomeAirport, range);
    }

    // Highlight aircraft card
    document.querySelectorAll('.aircraft-card').forEach(card => {
        card.classList.remove('border-danger');
        if (card.dataset.id === aircraftId) {
            card.classList.add('border-danger');
            card.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    });
};

// Add map legend
function addMapLegend() {
    if (!simpleMap) return;

    // Remove existing legend if it exists
    if (window.mapLegend) {
        simpleMap.removeControl(window.mapLegend);
    }

    // Create legend control
    const legend = L.control({ position: 'bottomright' });

    legend.onAdd = function (map) {
        const div = L.DomUtil.create('div', 'map-legend');
        div.style.cssText = `
            background: rgba(26, 26, 26, 0.95);
            border: 2px solid #00A86B;
            border-radius: 8px;
            padding: 12px;
            font-family: 'Rajdhani', sans-serif;
            color: white;
            font-size: 13px;
            line-height: 1.4;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(10px);
            min-width: 180px;
        `;

        div.innerHTML = `
            <div style="font-weight: 700; margin-bottom: 8px; color: #00A86B; text-align: center; font-size: 12px;">
                <i class="fas fa-map me-1"></i>RANGE CIRCLES
            </div>
            
            <div style="display: flex; align-items: center; margin-bottom: 4px;">
                <div style="width: 12px; height: 12px; border-radius: 50%; background: rgba(255, 68, 68, 0.3); border: 2px solid #FF4444; margin-right: 8px;"></div>
                <span style="font-size: 12px;">Longest Leg</span>
            </div>
            <div style="display: flex; align-items: center; margin-bottom: 4px;">
                <div style="width: 12px; height: 12px; border-radius: 50%; background: rgba(68, 136, 255, 0.3); border: 2px solid #4488FF; margin-right: 8px;"></div>
                <span style="font-size: 12px;">Average Leg</span>
            </div>
            <div style="display: flex; align-items: center;">
                <div style="width: 12px; height: 12px; border-radius: 50%; background: rgba(255, 255, 255, 0.1); border: 2px solid #FFFFFF; margin-right: 8px;"></div>
                <span style="font-size: 12px;">Custom Range</span>
            </div>
        `;

        return div;
    };

    legend.addTo(simpleMap);
    window.mapLegend = legend;
}

// Call this function after map initialization
if (typeof addMapLegend === 'function') {
    // Add legend after a short delay to ensure map is ready
    setTimeout(addMapLegend, 500);
}

console.log('✅ Simple map setup complete!'); 