/**
 * Simple Airport Search - Clean implementation from scratch
 * Handles home, from, and to airport searches
 */

console.log('🚀 Loading Simple Airport Search...');

document.addEventListener('DOMContentLoaded', function () {
    console.log('📍 Setting up simple airport search...');

    // Setup airport search for each input
    setupAirportSearch('home-airport-search', 'home');
    setupAirportSearch('from-airport', 'from');
    setupAirportSearch('to-airport', 'to');

    function setupAirportSearch(inputId, type) {
        const input = document.getElementById(inputId);
        if (!input) {
            console.log(`❌ No ${inputId} input found`);
            return;
        }

        console.log(`✅ Found ${inputId} input`);

        // Create dropdown for this input
        const dropdownId = `simple-${type}-dropdown`;
        let dropdown = document.getElementById(dropdownId);
        if (!dropdown) {
            dropdown = document.createElement('div');
            dropdown.id = dropdownId;
            dropdown.style.cssText = `
                position: absolute;
                top: 100%;
                left: 0;
                right: 0;
                background: #1a1a1a;
                border: 2px solid #F05545;
                border-top: none;
                max-height: 250px;
                overflow-y: auto;
                z-index: 9999;
                display: none;
            `;

            // Insert dropdown after the input's parent
            const inputParent = input.closest('.input-group') || input.parentElement;
            inputParent.style.position = 'relative';
            inputParent.appendChild(dropdown);

            console.log(`✅ Created ${type} dropdown element`);
        }

        // Search function for this input
        async function searchAirports(query) {
            console.log(`🔍 Searching ${type} for: "${query}"`);

            try {
                const response = await fetch(`/api/airports?q=${encodeURIComponent(query)}`);
                const airports = await response.json();

                console.log(`📍 Found ${airports.length} airports for ${type}`);

                // Clear dropdown
                dropdown.innerHTML = '';

                if (airports.length === 0) {
                    dropdown.innerHTML = '<div style="padding: 10px; color: #ccc;">No airports found</div>';
                } else {
                    // Show up to 10 results
                    const results = airports.slice(0, 10);
                    results.forEach(airport => {
                        const item = document.createElement('div');
                        item.style.cssText = `
                            padding: 10px;
                            cursor: pointer;
                            border-bottom: 1px solid #333;
                            color: white;
                            transition: background 0.2s;
                        `;

                        item.innerHTML = `
                            <div style="font-weight: bold; color: #F05545;">${airport.iata || 'N/A'}</div>
                            <div style="font-size: 0.9em;">${airport.name}</div>
                            <div style="font-size: 0.8em; color: #ccc;">${airport.city}, ${airport.country}</div>
                        `;

                        // Hover effect
                        item.addEventListener('mouseenter', () => {
                            item.style.background = '#333';
                        });
                        item.addEventListener('mouseleave', () => {
                            item.style.background = 'transparent';
                        });

                        // Click to select
                        item.addEventListener('click', () => {
                            input.value = `${airport.iata} - ${airport.city}`;
                            dropdown.style.display = 'none';
                            console.log(`✅ Selected ${type} airport:`, airport);

                            // Store selected airport globally
                            if (type === 'home') {
                                window.selectedHomeAirport = airport;
                                // Trigger any home airport change events
                                if (window.setHomeAirport && typeof window.setHomeAirport === 'function') {
                                    window.setHomeAirport(airport);
                                }
                            } else if (type === 'from') {
                                window.selectedFromAirport = airport;
                            } else if (type === 'to') {
                                window.selectedToAirport = airport;
                            }
                        });

                        dropdown.appendChild(item);
                    });
                }

                // Show dropdown
                dropdown.style.display = 'block';

            } catch (error) {
                console.error(`❌ ${type} search error:`, error);
                dropdown.innerHTML = '<div style="padding: 10px; color: #ff6b6b;">Search failed</div>';
                dropdown.style.display = 'block';
            }
        }

        // Input event listener
        input.addEventListener('input', function () {
            const query = this.value.trim();

            if (query.length >= 2) {
                searchAirports(query);
            } else {
                dropdown.style.display = 'none';
            }
        });

        // Hide dropdown when clicking outside
        document.addEventListener('click', function (e) {
            if (!input.contains(e.target) && !dropdown.contains(e.target)) {
                dropdown.style.display = 'none';
            }
        });
    }

    console.log('✅ Simple airport search setup complete for all inputs!');
}); 