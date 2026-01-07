/**
 * Airport Search Module - Rebuilt from scratch
 * Clean, simple, and robust implementation
 */

class AirportSearch {
    constructor() {
        this.searchDelay = 300; // ms delay for search
        this.minQueryLength = 2;
        this.activeRequests = new Map(); // Track active requests
        this.init();
    }

    init() {
        console.log('🚀 Initializing Airport Search from scratch...');

        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setupEventListeners());
        } else {
            this.setupEventListeners();
        }
    }

    setupEventListeners() {
        console.log('🔧 Setting up event listeners...');

        // Home airport search
        this.setupSearchInput('home-airport-search', 'home-airport-results', 'home-airport-list', this.selectHomeAirport.bind(this));

        // Route planning airports
        this.setupSearchInput('from-airport', 'from-airport-results', 'from-airport-list', this.selectFromAirport.bind(this));
        this.setupSearchInput('to-airport', 'to-airport-results', 'to-airport-list', this.selectToAirport.bind(this));

        // Close dropdowns when clicking outside
        document.addEventListener('click', (e) => this.handleOutsideClick(e));

        console.log('✅ Event listeners setup complete');
    }

    setupSearchInput(inputId, resultsId, listId, selectCallback) {
        const input = document.getElementById(inputId);
        const results = document.getElementById(resultsId);
        const list = document.getElementById(listId);

        if (!input || !results || !list) {
            console.log(`⚠️ Missing elements for ${inputId}:`, {
                input: !!input,
                results: !!results,
                list: !!list
            });
            return;
        }

        console.log(`✅ Setting up ${inputId}`);

        // Clear any existing listeners
        input.removeEventListener('input', input._airportSearchHandler);
        input.removeEventListener('keydown', input._keydownHandler);

        // Input handler with debouncing
        let searchTimeout;
        input._airportSearchHandler = (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                this.handleSearch(input.value.trim(), results, list, selectCallback);
            }, this.searchDelay);
        };

        // Keydown handler for navigation
        input._keydownHandler = (e) => {
            this.handleKeyNavigation(e, list, selectCallback);
        };

        input.addEventListener('input', input._airportSearchHandler);
        input.addEventListener('keydown', input._keydownHandler);

        // Store references for cleanup
        input._resultsContainer = results;
        input._resultsList = list;
    }

    async handleSearch(query, resultsContainer, resultsList, selectCallback) {
        console.log(`🔍 Searching for: "${query}"`);

        // Hide results if query too short
        if (query.length < this.minQueryLength) {
            this.hideResults(resultsContainer);
            return;
        }

        // Cancel any previous request for this container
        const requestKey = resultsContainer.id;
        if (this.activeRequests.has(requestKey)) {
            this.activeRequests.get(requestKey).abort();
        }

        // Show loading state
        this.showLoading(resultsContainer, resultsList);

        try {
            // Create new AbortController for this request
            const controller = new AbortController();
            this.activeRequests.set(requestKey, controller);

            const response = await fetch(`/api/airports?q=${encodeURIComponent(query)}`, {
                signal: controller.signal
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const airports = await response.json();
            console.log(`📍 Found ${airports.length} airports`);

            // Clear the active request
            this.activeRequests.delete(requestKey);

            // Display results
            this.displayResults(airports, resultsContainer, resultsList, selectCallback, query);

        } catch (error) {
            // Clear the active request
            this.activeRequests.delete(requestKey);

            if (error.name === 'AbortError') {
                console.log('🚫 Search request aborted');
                return;
            }

            console.error('❌ Search error:', error);
            this.showError(resultsContainer, resultsList, `Search failed: ${error.message}`);
        }
    }

    showLoading(resultsContainer, resultsList) {
        resultsList.innerHTML = `
            <div class="airport-item loading">
                <div class="d-flex align-items-center">
                    <div class="spinner-border spinner-border-sm me-2" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    Searching airports...
                </div>
            </div>
        `;
        this.showResults(resultsContainer);
    }

    displayResults(airports, resultsContainer, resultsList, selectCallback, query) {
        if (airports.length === 0) {
            resultsList.innerHTML = `
                <div class="airport-item no-results">
                    <div class="text-muted">
                        <i class="fas fa-search me-2"></i>
                        No airports found for "${query}"
                    </div>
                    <small class="text-muted">Try searching by IATA code (LAX) or city name</small>
                </div>
            `;
        } else {
            resultsList.innerHTML = airports.map(airport => this.createAirportItem(airport)).join('');

            // Add click listeners to airport items
            const airportItems = resultsList.querySelectorAll('.airport-item[data-airport]');
            airportItems.forEach(item => {
                item.addEventListener('click', () => {
                    const airport = JSON.parse(item.dataset.airport);
                    selectCallback(airport);
                    this.hideResults(resultsContainer);
                });
            });
        }

        this.showResults(resultsContainer);
    }

    createAirportItem(airport) {
        return `
            <div class="airport-item" data-airport='${JSON.stringify(airport)}'>
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <div class="fw-bold">
                            <span class="text-danger me-2">${airport.iata || 'N/A'}</span>
                            <span class="text-info">${airport.icao || ''}</span>
                        </div>
                        <div class="airport-name">${airport.name}</div>
                        <small class="text-muted">${airport.city}, ${airport.country}</small>
                    </div>
                    ${airport.size ? `<span class="badge bg-secondary">${airport.size}</span>` : ''}
                </div>
            </div>
        `;
    }

    showError(resultsContainer, resultsList, message) {
        resultsList.innerHTML = `
            <div class="airport-item error">
                <div class="text-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    ${message}
                </div>
            </div>
        `;
        this.showResults(resultsContainer);
    }

    showResults(resultsContainer) {
        resultsContainer.classList.remove('d-none');
        resultsContainer.style.display = 'block';
    }

    hideResults(resultsContainer) {
        resultsContainer.classList.add('d-none');
        resultsContainer.style.display = 'none';
    }

    handleOutsideClick(event) {
        // Find all airport search containers
        const containers = document.querySelectorAll('#home-airport-results, #from-airport-results, #to-airport-results');

        containers.forEach(container => {
            const input = container.previousElementSibling?.querySelector('input') ||
                container.closest('.input-group')?.querySelector('input');

            if (input && !input.contains(event.target) && !container.contains(event.target)) {
                this.hideResults(container);
            }
        });
    }

    handleKeyNavigation(event, resultsList, selectCallback) {
        const items = resultsList.querySelectorAll('.airport-item[data-airport]');
        if (items.length === 0) return;

        let selectedIndex = Array.from(items).findIndex(item => item.classList.contains('selected'));

        switch (event.key) {
            case 'ArrowDown':
                event.preventDefault();
                selectedIndex = Math.min(selectedIndex + 1, items.length - 1);
                this.updateSelection(items, selectedIndex);
                break;

            case 'ArrowUp':
                event.preventDefault();
                selectedIndex = Math.max(selectedIndex - 1, 0);
                this.updateSelection(items, selectedIndex);
                break;

            case 'Enter':
                event.preventDefault();
                if (selectedIndex >= 0) {
                    const selectedItem = items[selectedIndex];
                    const airport = JSON.parse(selectedItem.dataset.airport);
                    selectCallback(airport);
                    this.hideResults(resultsList.closest('.airport-results, [id$="-results"]'));
                }
                break;

            case 'Escape':
                this.hideResults(resultsList.closest('.airport-results, [id$="-results"]'));
                break;
        }
    }

    updateSelection(items, selectedIndex) {
        items.forEach((item, index) => {
            item.classList.toggle('selected', index === selectedIndex);
        });

        if (selectedIndex >= 0) {
            items[selectedIndex].scrollIntoView({ block: 'nearest' });
        }
    }

    // Airport selection handlers
    selectHomeAirport(airport) {
        console.log('🏠 Selected home airport:', airport);
        const input = document.getElementById('home-airport-search');
        if (input) {
            input.value = `${airport.iata} - ${airport.city}`;

            // Trigger home airport change event
            if (window.setHomeAirport && typeof window.setHomeAirport === 'function') {
                window.setHomeAirport(airport);
            }
        }
    }

    selectFromAirport(airport) {
        console.log('✈️ Selected from airport:', airport);
        const input = document.getElementById('from-airport');
        if (input) {
            input.value = `${airport.iata} - ${airport.city}`;

            // Update global variable if it exists
            if (window.selectedFromAirport !== undefined) {
                window.selectedFromAirport = airport;
            }
        }
    }

    selectToAirport(airport) {
        console.log('🛬 Selected to airport:', airport);
        const input = document.getElementById('to-airport');
        if (input) {
            input.value = `${airport.iata} - ${airport.city}`;

            // Update global variable if it exists
            if (window.selectedToAirport !== undefined) {
                window.selectedToAirport = airport;
            }
        }
    }
}

// Initialize when script loads
new AirportSearch(); 