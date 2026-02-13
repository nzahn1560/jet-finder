/**
 * Aircraft Cost Analysis Module
 * Handles cost analysis for aircraft using data from the CSV import
 */

// Aircraft Analysis JavaScript
class AircraftAnalysis {
    constructor() {
        this.csvData = [];
        this.filteredData = [];
        this.allAircraft = []; // Store all aircraft for filtering
        this.currentSort = 'best_overall';
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadCSVData();
        this.setupSliderSync();
        this.autoPopulateFromTripPlanning();
    }

    bindEvents() {
        // CSV input change events
        document.querySelectorAll('.csv-input').forEach(input => {
            input.addEventListener('change', () => this.updateAnalysis());
            input.addEventListener('input', () => this.updateAnalysis());
        });

        // Sort button events
        document.querySelectorAll('.sort-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.currentSort = e.target.dataset.sort;
                this.sortAircraft();
                this.updateSortButtons();
            });
        });

        // Export button
        const exportBtn = document.getElementById('export-results');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => this.exportResults());
        }

        // Reset button
        const resetBtn = document.getElementById('reset-inputs');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => this.resetInputs());
        }
    }

    setupSliderSync() {
        // Sync price range slider with input
        const slider = document.getElementById('price-range-slider');
        const maxPriceInput = document.getElementById('max_price');

        if (slider && maxPriceInput) {
            slider.addEventListener('input', () => {
                maxPriceInput.value = slider.value;
                this.updateAnalysis();
            });

            maxPriceInput.addEventListener('change', () => {
                slider.value = maxPriceInput.value;
                this.updateAnalysis();
            });
        }
    }

    autoPopulateFromTripPlanning() {
        // Listen for trip planning updates
        window.addEventListener('tripPlanningUpdate', (event) => {
            const { longestLeg, averageDistance, tripCount } = event.detail;

            // Update range requirement
            const rangeInput = document.getElementById('range_nm');
            if (rangeInput && longestLeg) {
                rangeInput.value = Math.ceil(longestLeg);
                this.updateAnalysis();
            }

            // Update average trip length
            const avgTripInput = document.getElementById('avg_trip_length');
            if (avgTripInput && averageDistance) {
                avgTripInput.value = Math.ceil(averageDistance);
                this.updateAnalysis();
            }

            // Update number of trips
            const tripsInput = document.getElementById('num_trips');
            if (tripsInput && tripCount) {
                tripsInput.value = tripCount;
                this.updateAnalysis();
            }
        });

        // Auto-populate on page load if trip planning data exists
        this.checkTripPlanningData();
    }

    checkTripPlanningData() {
        // Check if we have trip planning data stored
        if (window.tripPlanningData) {
            const { longestLeg, averageDistance, tripCount } = window.tripPlanningData;

            if (longestLeg) {
                const rangeInput = document.getElementById('range_nm');
                if (rangeInput) rangeInput.value = Math.ceil(longestLeg);
            }

            if (averageDistance) {
                const avgTripInput = document.getElementById('avg_trip_length');
                if (avgTripInput) avgTripInput.value = Math.ceil(averageDistance);
            }

            if (tripCount) {
                const tripsInput = document.getElementById('num_trips');
                if (tripsInput) tripsInput.value = tripCount;
            }

            this.updateAnalysis();
        }
    }

    async loadCSVData() {
        try {
            // Load aircraft data from CSV
            const response = await fetch('/api/aircraft-data');
            if (response.ok) {
                this.csvData = await response.json();
                this.allAircraft = [...this.csvData]; // Store copy of all aircraft
                this.updateAnalysis();
            }
        } catch (error) {
            console.error('Error loading CSV data:', error);
        }
    }

    updateAnalysis() {
        // Get current input values
        const inputs = this.getInputValues();

        // Filter and analyze aircraft
        this.filteredData = this.filterAircraft(inputs);

        // Calculate analysis metrics
        this.calculateMetrics(inputs);

        // Update displays
        this.updateMissionAnalysis(inputs);
        this.displayAircraft();
        this.updateAvailableCount();
    }

    getInputValues() {
        return {
            lowestYear: parseInt(document.getElementById('lowest_acceptable_year')?.value) || 2000,
            rangeRequired: parseInt(document.getElementById('range_nm')?.value) || 500,
            passengers: parseInt(document.getElementById('passengers')?.value) || 4,
            maxPrice: parseInt(document.getElementById('max_price')?.value) || 5000000,
            avgTripLength: parseInt(document.getElementById('avg_trip_length')?.value) || 300,
            numTrips: parseInt(document.getElementById('num_trips')?.value) || 25,
            yearsOwnership: parseInt(document.getElementById('years_ownership')?.value) || 5,
            depreciationRate: parseFloat(document.getElementById('depreciation_rate')?.value) || 4.0,
            jetAPrice: parseFloat(document.getElementById('jet_a_price')?.value) || 6.5,
            avgasPrice: parseFloat(document.getElementById('avgas_price')?.value) || 4.0,
            costToCharter: parseFloat(document.getElementById('cost_to_charter')?.value) || 200
        };
    }

    filterAircraft(inputs) {
        return this.allAircraft.filter(aircraft => {
            // Apply filters based on requirements
            if (aircraft.year < inputs.lowestYear) return false;
            if (aircraft.range < inputs.rangeRequired) return false;
            if (aircraft.passengers < inputs.passengers) return false;
            if (aircraft.price > inputs.maxPrice) return false;

            return true;
        });
    }

    calculateMetrics(inputs) {
        // Calculate metrics for each aircraft
        this.filteredData.forEach(aircraft => {
            // Calculate annual hours based on mission
            aircraft.annualHours = inputs.avgTripLength * inputs.numTrips / aircraft.speed;

            // Calculate multi-year total cost
            aircraft.multiYearCost = this.calculateMultiYearCost(aircraft, inputs);

            // Calculate efficiency ratios
            aircraft.speedPerDollar = aircraft.speed / aircraft.price * 1000000;
            aircraft.rangePerDollar = aircraft.range / aircraft.price * 1000000;
            aircraft.efficiencyScore = this.calculateEfficiencyScore(aircraft, inputs);
        });
    }

    calculateMultiYearCost(aircraft, inputs) {
        const annualOperatingCost = aircraft.annualBudget || (aircraft.totalHourlyCost * aircraft.annualHours);
        const purchasePrice = aircraft.price;
        const depreciation = purchasePrice * (inputs.depreciationRate / 100) * inputs.yearsOwnership;

        return (annualOperatingCost * inputs.yearsOwnership) + depreciation;
    }

    calculateEfficiencyScore(aircraft, inputs) {
        // Normalized efficiency score (0-100)
        const speedScore = Math.min(aircraft.speed / 600 * 25, 25); // Max 25 points for 600+ kts
        const rangeScore = Math.min(aircraft.range / 4000 * 25, 25); // Max 25 points for 4000+ nm
        const costScore = Math.max(25 - (aircraft.price / 10000000 * 25), 0); // Max 25 points for low cost
        const efficiencyScore = Math.min(aircraft.speedPerDollar / 100 * 25, 25); // Max 25 points for efficiency

        return speedScore + rangeScore + costScore + efficiencyScore;
    }

    updateMissionAnalysis(inputs) {
        // Update mission analysis display
        const longestLeg = inputs.rangeRequired;
        const annualDistance = inputs.avgTripLength * inputs.numTrips;
        const availableCount = this.filteredData.length;

        // Update display elements
        document.getElementById('longest-leg-required').textContent = `${longestLeg.toLocaleString()} nm`;
        document.getElementById('annual-distance').textContent = `${annualDistance.toLocaleString()} nm`;
        document.getElementById('available-aircraft-count').textContent = availableCount;

        // Calculate average flight hours for mission
        if (this.filteredData.length > 0) {
            const avgHours = this.filteredData.reduce((sum, aircraft) => sum + aircraft.annualHours, 0) / this.filteredData.length;
            document.getElementById('avg-flight-hours').textContent = `${Math.round(avgHours)} hours`;
        } else {
            document.getElementById('avg-flight-hours').textContent = '0 hours';
        }
    }

    displayAircraft() {
        const container = document.querySelector('.aircraft-results');
        if (!container) return;

        // Sort aircraft before displaying
        this.sortAircraft();

        // Display all aircraft but mark filtered ones
        const allAircraftDisplay = this.allAircraft.map(aircraft => {
            const isFiltered = this.filteredData.includes(aircraft);
            return this.createAircraftCard(aircraft, isFiltered);
        }).join('');

        container.innerHTML = allAircraftDisplay;
    }

    createAircraftCard(aircraft, meetsRequirements) {
        const cardClass = meetsRequirements ? 'aircraft-card' : 'aircraft-card filtered-out';
        const badgeClass = meetsRequirements ? 'bg-success' : 'bg-secondary';
        const statusText = meetsRequirements ? 'Meets Requirements' : 'Does Not Meet Requirements';

        return `
            <div class="${cardClass}" ${!meetsRequirements ? 'style="opacity: 0.5;"' : ''}>
                <div class="aircraft-header">
                    <h5>${aircraft.manufacturer} ${aircraft.model}</h5>
                    <span class="badge ${badgeClass}">${statusText}</span>
                </div>
                
                <div class="aircraft-specs">
                    <div class="spec-item">
                        <span class="spec-label">Price:</span>
                        <span class="spec-value">$${aircraft.price.toLocaleString()}</span>
                    </div>
                    <div class="spec-item">
                        <span class="spec-label">Range:</span>
                        <span class="spec-value">${aircraft.range.toLocaleString()} nm</span>
                    </div>
                    <div class="spec-item">
                        <span class="spec-label">Speed:</span>
                        <span class="spec-value">${aircraft.speed} kts</span>
                    </div>
                    <div class="spec-item">
                        <span class="spec-label">Passengers:</span>
                        <span class="spec-value">${aircraft.passengers}</span>
                    </div>
                </div>
                
                ${meetsRequirements ? this.createFinancialAnalysis(aircraft) : ''}
                ${meetsRequirements ? this.createEfficiencyScores(aircraft) : ''}
            </div>
        `;
    }

    createFinancialAnalysis(aircraft) {
        return `
            <div class="financial-analysis">
                <h6>Financial Analysis</h6>
                <div class="financial-grid">
                    <div class="financial-item">
                        <span class="label">Annual Hours:</span>
                        <span class="value">${Math.round(aircraft.annualHours)} hrs</span>
                    </div>
                    <div class="financial-item">
                        <span class="label">Multi-Year Cost:</span>
                        <span class="value">$${aircraft.multiYearCost.toLocaleString()}</span>
                    </div>
                    <div class="financial-item">
                        <span class="label">Hourly Cost:</span>
                        <span class="value">$${aircraft.totalHourlyCost.toLocaleString()}</span>
                    </div>
                </div>
            </div>
        `;
    }

    createEfficiencyScores(aircraft) {
        return `
            <div class="efficiency-scores">
                <h6>Efficiency Scores</h6>
                <div class="score-grid">
                    <div class="score-item">
                        <span class="label">Speed/$:</span>
                        <span class="value">${aircraft.speedPerDollar.toFixed(2)}</span>
                    </div>
                    <div class="score-item">
                        <span class="label">Range/$:</span>
                        <span class="value">${aircraft.rangePerDollar.toFixed(2)}</span>
                    </div>
                    <div class="score-item">
                        <span class="label">Overall:</span>
                        <span class="value">${aircraft.efficiencyScore.toFixed(1)}</span>
                    </div>
                </div>
            </div>
        `;
    }

    sortAircraft() {
        const sortFunctions = {
            'best_overall': (a, b) => (b.efficiencyScore || 0) - (a.efficiencyScore || 0),
            'lowest_cost': (a, b) => (a.multiYearCost || 0) - (b.multiYearCost || 0),
            'best_range': (a, b) => (b.range || 0) - (a.range || 0),
            'best_speed': (a, b) => (b.speed || 0) - (a.speed || 0),
            'best_efficiency': (a, b) => (b.speedPerDollar || 0) - (a.speedPerDollar || 0)
        };

        if (sortFunctions[this.currentSort]) {
            this.filteredData.sort(sortFunctions[this.currentSort]);
            this.allAircraft.sort(sortFunctions[this.currentSort]);
        }
    }

    updateSortButtons() {
        document.querySelectorAll('.sort-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.sort === this.currentSort);
        });
    }

    updateAvailableCount() {
        const countElement = document.getElementById('available-aircraft-count');
        if (countElement) {
            countElement.textContent = this.filteredData.length;
        }
    }

    exportResults() {
        // Create CSV export data
        const csvData = this.filteredData.map(aircraft => ({
            'Aircraft': `${aircraft.manufacturer} ${aircraft.model}`,
            'Price': aircraft.price,
            'Range (nm)': aircraft.range,
            'Speed (kts)': aircraft.speed,
            'Passengers': aircraft.passengers,
            'Annual Hours': Math.round(aircraft.annualHours),
            'Multi-Year Cost': aircraft.multiYearCost,
            'Efficiency Score': aircraft.efficiencyScore.toFixed(1)
        }));

        this.downloadCSV(csvData, 'aircraft_analysis_results.csv');
    }

    downloadCSV(data, filename) {
        const csv = this.convertToCSV(data);
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        window.URL.revokeObjectURL(url);
    }

    convertToCSV(data) {
        if (!data.length) return '';

        const headers = Object.keys(data[0]);
        const csvContent = [
            headers.join(','),
            ...data.map(row => headers.map(header =>
                typeof row[header] === 'string' && row[header].includes(',')
                    ? `"${row[header]}"`
                    : row[header]
            ).join(','))
        ].join('\n');

        return csvContent;
    }

    resetInputs() {
        // Reset all inputs to defaults
        document.getElementById('lowest_acceptable_year').value = 2000;
        document.getElementById('range_nm').value = 500;
        document.getElementById('passengers').value = 4;
        document.getElementById('max_price').value = 5000000;
        document.getElementById('avg_trip_length').value = 300;
        document.getElementById('num_trips').value = 25;
        document.getElementById('years_ownership').value = 5;
        document.getElementById('depreciation_rate').value = 4.0;
        document.getElementById('jet_a_price').value = 6.5;
        document.getElementById('avgas_price').value = 4.0;

        // Update slider with $1B max
        const slider = document.getElementById('price-range-slider');
        if (slider) {
            slider.max = 1000000000; // Ensure max is set to $1B
            slider.value = 5000000;
        }

        this.updateAnalysis();
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.aircraftAnalysis = new AircraftAnalysis();
}); 