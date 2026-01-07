/**
 * CSV Input Linker - Links form inputs to CSV column data for seamless updates
 * Enhanced with intelligent input discovery and trip planning integration
 */

console.log('📊 Loading CSV Input Linker...');

class CSVInputLinker {
    constructor() {
        this.csvColumnMappings = this.getInputMappings();
        this.aircraftDataCache = [];
        this.lastUpdateTime = 0;
        this.updateThrottleMs = 1000; // Reduced from aggressive updates
        this.autoMonitoringEnabled = false; // Disabled by default
        this.isUpdating = false; // Prevent recursive updates
    }

    init() {
        console.log('📊 Initializing CSV Input Linker...');

        // Load aircraft data for dynamic filtering
        this.loadAircraftData();

        // Setup input monitoring - but disabled by default
        if (this.autoMonitoringEnabled) {
            this.setupInputMonitoring();
        } else {
            console.log('⚠️ Auto-monitoring disabled to prevent refresh loops');
        }

        console.log('✅ CSV Input Linker initialized');
    }

    setupInputMonitoring() {
        // DISABLED BY DEFAULT - This was contributing to the refresh loop
        if (!this.autoMonitoringEnabled) {
            console.log('⚠️ Input monitoring disabled');
            return;
        }

        // Monitor all form inputs for changes
        const inputs = document.querySelectorAll('input, select, textarea');

        inputs.forEach(input => {
            // Add heavily debounced change listener
            let timeout;
            const debouncedUpdate = () => {
                clearTimeout(timeout);
                timeout = setTimeout(() => {
                    if (!this.isUpdating) {
                        this.handleInputChange(input);
                    }
                }, 1000); // Increased debounce to 1 second
            };

            // Only monitor on explicit user interaction, not programmatic changes
            input.addEventListener('blur', debouncedUpdate);
            // Remove 'input' event listener that was too aggressive
            // input.addEventListener('input', debouncedUpdate);
        });

        console.log(`📊 Monitoring ${inputs.length} form inputs for changes (conservative mode)`);
    }

    async loadAircraftData() {
        try {
            const response = await fetch('/api/aircraft-data');
            if (response.ok) {
                this.aircraftDataCache = await response.json();
                console.log(`📊 Loaded ${this.aircraftDataCache.length} aircraft for dynamic filtering`);
            }
        } catch (error) {
            console.warn('📊 Could not load aircraft data for dynamic updates:', error);
        }
    }

    handleInputChange(input) {
        // Prevent recursive updates
        if (this.isUpdating) {
            return;
        }

        // Throttle updates to prevent excessive processing
        const now = Date.now();
        if (now - this.lastUpdateTime < this.updateThrottleMs) {
            return;
        }
        this.lastUpdateTime = now;
        this.isUpdating = true;

        // Get current form values
        const formData = this.getFormData();

        // Update aircraft listings if possible
        this.updateAircraftListings(formData);

        // Provide visual feedback
        this.showUpdateFeedback(input);

        // Reset updating flag after delay
        setTimeout(() => {
            this.isUpdating = false;
        }, 500);
    }

    getFormData() {
        const formData = {};

        // Get all form inputs
        const inputs = document.querySelectorAll('input, select, textarea');

        inputs.forEach(input => {
            if (input.name && input.value) {
                // Clean numeric values
                let value = input.value;
                if (input.type === 'number' || input.type === 'range') {
                    value = parseFloat(value) || 0;
                }

                formData[input.name] = value;
            }
        });

        return formData;
    }

    updateAircraftListings(formData) {
        if (!this.aircraftDataCache || this.aircraftDataCache.length === 0) {
            return;
        }

        // Apply filters based on form data
        const filteredAircraft = this.filterAircraft(formData);

        // Update the UI without triggering refresh
        this.updateAircraftUIMinimal(filteredAircraft);
    }

    filterAircraft(formData) {
        return this.aircraftDataCache.filter(aircraft => {
            // Range filter
            if (formData.min_range && aircraft.range < formData.min_range) {
                return false;
            }

            // Budget filter
            if (formData.max_price && aircraft.price > formData.max_price) {
                return false;
            }

            // Passenger filter
            if (formData.seats && aircraft.passengers < formData.seats) {
                return false;
            }

            // Speed filter
            if (formData.min_speed && aircraft.speed < formData.min_speed) {
                return false;
            }

            // Year filter
            if (formData.min_year && aircraft.year < formData.min_year) {
                return false;
            }

            if (formData.max_year && aircraft.year > formData.max_year) {
                return false;
            }

            return true;
        });
    }

    updateAircraftUIMinimal(filteredAircraft) {
        // Minimal UI updates that don't trigger refresh loops

        // Update results counter only
        const counterElements = document.querySelectorAll('.results-counter, .total-results');
        counterElements.forEach(el => {
            if (el.textContent !== filteredAircraft.length.toString()) {
                el.textContent = filteredAircraft.length;
            }
        });

        // NO grid updates that might trigger refreshes
        console.log(`📊 Filtered to ${filteredAircraft.length} aircraft (minimal UI update)`);
    }

    updateAircraftUI(filteredAircraft) {
        // LEGACY METHOD - Now calls minimal version
        this.updateAircraftUIMinimal(filteredAircraft);
    }

    showUpdateFeedback(input) {
        // Add visual feedback to show the input affected the results
        const originalBorder = input.style.borderColor;
        const originalBoxShadow = input.style.boxShadow;

        input.style.borderColor = '#F05545';
        input.style.boxShadow = '0 0 0 0.25rem rgba(240, 85, 69, 0.25)';

        setTimeout(() => {
            input.style.borderColor = originalBorder;
            input.style.boxShadow = originalBoxShadow;
        }, 800);
    }

    // Public method to link trip planning data to inputs
    linkTripPlanningData(tripStats) {
        // Prevent recursive updates
        if (this.isUpdating) {
            return 0;
        }
        this.isUpdating = true;

        const mappings = [
            { csvField: 'trip_frequency', value: tripStats.totalTrips },
            { csvField: 'yearly_usage', value: Math.round(tripStats.totalTrips * 2.5) },
            { csvField: 'range_required', value: tripStats.longestLeg },
            { csvField: 'average_leg', value: tripStats.averageLeg },
            { csvField: 'longest_leg', value: tripStats.longestLeg }
        ];

        let updatedCount = 0;

        mappings.forEach(mapping => {
            const patterns = this.csvColumnMappings[mapping.csvField] || [mapping.csvField];

            patterns.forEach(pattern => {
                const input = this.findInput(pattern);
                if (input && mapping.value > 0) {
                    const currentValue = parseFloat(input.value) || 0;

                    // Only update if empty or significantly different
                    if (currentValue === 0 || Math.abs(currentValue - mapping.value) > currentValue * 0.1) {
                        input.value = mapping.value;
                        this.showUpdateFeedback(input);

                        // Mark input as auto-updated to prevent loops
                        input.setAttribute('data-auto-updated', 'true');

                        // DON'T trigger change events to prevent loops
                        // input.dispatchEvent(new Event('change', { bubbles: true }));

                        updatedCount++;

                        // Remove the marker after a delay
                        setTimeout(() => {
                            input.removeAttribute('data-auto-updated');
                        }, 1000);
                    }
                }
            });
        });

        // Reset updating flag
        setTimeout(() => {
            this.isUpdating = false;
        }, 500);

        if (updatedCount > 0) {
            console.log(`📊 CSV Input Linker updated ${updatedCount} inputs from trip planning (no events triggered)`);
        }

        return updatedCount;
    }

    findInput(pattern) {
        // Try multiple ways to find the input

        // 1. By exact ID
        let input = document.getElementById(pattern);
        if (input) return input;

        // 2. By exact name
        input = document.querySelector(`input[name="${pattern}"]`);
        if (input) return input;

        // 3. By data attribute
        input = document.querySelector(`input[data-field="${pattern}"]`);
        if (input) return input;

        // 4. By partial name match (case insensitive)
        const inputs = document.querySelectorAll('input[type="number"], input[type="range"], input[type="text"]');
        for (const inp of inputs) {
            if (inp.name && inp.name.toLowerCase().includes(pattern.toLowerCase())) {
                return inp;
            }
            if (inp.id && inp.id.toLowerCase().includes(pattern.toLowerCase())) {
                return inp;
            }
        }

        return null;
    }

    // Public method to get current input mappings for debugging
    getInputMappings() {
        const mappings = {};

        Object.keys(this.csvColumnMappings).forEach(csvField => {
            const patterns = this.csvColumnMappings[csvField];
            const foundInputs = [];

            patterns.forEach(pattern => {
                const input = this.findInput(pattern);
                if (input) {
                    foundInputs.push({
                        pattern: pattern,
                        element: input.tagName.toLowerCase(),
                        id: input.id,
                        name: input.name,
                        value: input.value,
                        type: input.type
                    });
                }
            });

            if (foundInputs.length > 0) {
                mappings[csvField] = foundInputs;
            }
        });

        return mappings;
    }
}

// Initialize the CSV Input Linker
const csvInputLinker = new CSVInputLinker();

// Make it globally available
window.csvInputLinker = csvInputLinker;

console.log('✅ CSV Input Linker loaded successfully'); 