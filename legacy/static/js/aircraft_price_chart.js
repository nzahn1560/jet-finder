/**
 * Aircraft Price Chart - Robinhood/StockX Style Visualization
 * Features: Interactive line chart with touch support, real-time tooltips
 */

class AircraftPriceChart {
    constructor(aircraftId) {
        this.aircraftId = aircraftId;
        this.chart = null;
        this.currentPeriod = '6M';
        this.priceData = [];
        this.tooltip = document.getElementById('priceTooltip');
        this.isLoading = false;

        this.init();
    }

    async init() {
        try {
            await this.loadPriceData();
            this.initChart();
            this.bindEvents();
        } catch (error) {
            console.error('Failed to initialize price chart:', error);
            this.showError('Failed to load price data');
        }
    }

    async loadPriceData() {
        if (this.isLoading) return;

        this.isLoading = true;
        this.showLoading(true);

        try {
            const response = await fetch(`/api/aircraft/${this.aircraftId}/price-history?period=${this.currentPeriod}`);
            const data = await response.json();

            if (data.success) {
                this.priceData = data.price_history;
                this.updateStats(data.stats);
                this.updatePriceSummary(data.current_price, data.price_change);
            } else {
                throw new Error(data.error || 'Failed to load price data');
            }
        } catch (error) {
            console.error('Error loading price data:', error);
            this.showError('Unable to load price data. Please try again.');
        } finally {
            this.isLoading = false;
            this.showLoading(false);
        }
    }

    initChart() {
        const ctx = document.getElementById('priceChart');
        if (!ctx) {
            console.error('Price chart canvas not found');
            return;
        }

        // Prepare data for Chart.js
        const chartData = this.priceData.map(point => ({
            x: new Date(point.date),
            y: point.price
        }));

        // Determine if price is trending up or down for color
        const isPositiveTrend = chartData.length > 1 &&
            chartData[chartData.length - 1].y > chartData[0].y;

        const lineColor = isPositiveTrend ? '#30d158' : '#ff453a';
        const fillColor = isPositiveTrend ? 'rgba(48, 209, 88, 0.1)' : 'rgba(255, 69, 58, 0.1)';

        this.chart = new Chart(ctx, {
            type: 'line',
            data: {
                datasets: [{
                    data: chartData,
                    borderColor: lineColor,
                    backgroundColor: fillColor,
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 6,
                    pointHoverBackgroundColor: lineColor,
                    pointHoverBorderColor: '#ffffff',
                    pointHoverBorderWidth: 2,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        enabled: false // Custom tooltip
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        display: false,
                        grid: {
                            display: false
                        }
                    },
                    y: {
                        display: false,
                        grid: {
                            display: false
                        }
                    }
                },
                onHover: (event, activeElements) => {
                    this.handleChartHover(event, activeElements);
                },
                elements: {
                    point: {
                        hoverRadius: 8
                    }
                },
                animation: {
                    duration: 1000,
                    easing: 'easeInOutQuart'
                }
            }
        });

        // Add touch and mouse support
        this.addInteractionSupport();
    }

    addInteractionSupport() {
        const canvas = document.getElementById('priceChart');
        if (!canvas) return;

        let isTracking = false;

        // Touch events for mobile
        canvas.addEventListener('touchstart', (e) => {
            e.preventDefault();
            isTracking = true;
            this.handleTouch(e);
        }, { passive: false });

        canvas.addEventListener('touchmove', (e) => {
            e.preventDefault();
            if (isTracking) {
                this.handleTouch(e);
            }
        }, { passive: false });

        canvas.addEventListener('touchend', (e) => {
            e.preventDefault();
            isTracking = false;
            this.hideTooltip();
        }, { passive: false });

        // Mouse events for desktop
        canvas.addEventListener('mousemove', (e) => {
            this.handleMouse(e);
        });

        canvas.addEventListener('mouseleave', () => {
            this.hideTooltip();
        });

        // Prevent context menu on long press
        canvas.addEventListener('contextmenu', (e) => {
            e.preventDefault();
        });
    }

    handleChartHover(event, activeElements) {
        if (activeElements.length > 0) {
            const dataIndex = activeElements[0].index;
            if (dataIndex >= 0 && dataIndex < this.priceData.length) {
                const dataPoint = this.priceData[dataIndex];
                this.showTooltip(event, dataPoint);
            }
        } else {
            this.hideTooltip();
        }
    }

    handleTouch(e) {
        const rect = e.target.getBoundingClientRect();
        const x = e.touches[0].clientX - rect.left;
        this.findNearestDataPoint(x, e.touches[0].clientX, e.touches[0].clientY);
    }

    handleMouse(e) {
        const rect = e.target.getBoundingClientRect();
        const x = e.clientX - rect.left;
        this.findNearestDataPoint(x, e.clientX, e.clientY);
    }

    findNearestDataPoint(canvasX, screenX, screenY) {
        if (!this.chart || !this.priceData.length) return;

        const chartArea = this.chart.chartArea;

        // Calculate the relative position within the chart area
        const relativeX = (canvasX - chartArea.left) / (chartArea.right - chartArea.left);
        const dataIndex = Math.round(relativeX * (this.priceData.length - 1));

        if (dataIndex >= 0 && dataIndex < this.priceData.length) {
            const dataPoint = this.priceData[dataIndex];
            this.showTooltip({ clientX: screenX, clientY: screenY }, dataPoint);
        }
    }

    showTooltip(event, dataPoint) {
        if (!this.tooltip || !dataPoint) return;

        const date = new Date(dataPoint.date);
        const formattedDate = date.toLocaleDateString('en-US', {
            weekday: 'short',
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });

        // Update tooltip content
        const tooltipDate = document.getElementById('tooltipDate');
        const tooltipPrice = document.getElementById('tooltipPrice');
        const tooltipVolume = document.getElementById('tooltipVolume');

        if (tooltipDate) tooltipDate.textContent = formattedDate;
        if (tooltipPrice) tooltipPrice.textContent = `$${dataPoint.price.toLocaleString()}`;
        if (tooltipVolume) tooltipVolume.textContent = `Volume: ${dataPoint.volume || 0}`;

        // Position tooltip
        const rect = document.getElementById('priceChart').getBoundingClientRect();
        let x = event.clientX - rect.left - 70; // Center tooltip
        let y = event.clientY - rect.top - 80;

        // Keep tooltip within bounds
        x = Math.max(10, Math.min(x, rect.width - 140));
        y = Math.max(10, Math.min(y, rect.height - 80));

        this.tooltip.style.left = x + 'px';
        this.tooltip.style.top = y + 'px';
        this.tooltip.classList.add('show');
    }

    hideTooltip() {
        if (this.tooltip) {
            this.tooltip.classList.remove('show');
        }
    }

    updateStats(stats) {
        const elements = {
            dayHigh: document.getElementById('dayHigh'),
            dayLow: document.getElementById('dayLow'),
            avgPrice: document.getElementById('avgPrice'),
            volume: document.getElementById('volume')
        };

        if (elements.dayHigh) elements.dayHigh.textContent = `$${stats.day_high.toLocaleString()}`;
        if (elements.dayLow) elements.dayLow.textContent = `$${stats.day_low.toLocaleString()}`;
        if (elements.avgPrice) elements.avgPrice.textContent = `$${stats.avg_price.toLocaleString()}`;
        if (elements.volume) elements.volume.textContent = stats.volume.toLocaleString();
    }

    updatePriceSummary(currentPrice, priceChange) {
        const currentPriceEl = document.getElementById('currentPrice');
        const changeElement = document.getElementById('priceChange');
        const changeAmount = document.getElementById('changeAmount');
        const changePercent = document.getElementById('changePercent');

        if (currentPriceEl) {
            currentPriceEl.textContent = `$${currentPrice.toLocaleString()}`;
        }

        if (changeElement && changeAmount && changePercent) {
            const isPositive = priceChange.amount >= 0;
            changeElement.className = `price-change ${isPositive ? 'positive' : 'negative'}`;

            changeAmount.textContent = `${isPositive ? '+' : ''}$${Math.abs(priceChange.amount).toLocaleString()}`;
            changePercent.textContent = `(${isPositive ? '+' : ''}${priceChange.percent.toFixed(2)}%)`;
        }
    }

    bindEvents() {
        // Time filter buttons
        document.querySelectorAll('.time-filter').forEach(button => {
            button.addEventListener('click', async (e) => {
                if (this.isLoading) return;

                // Update active state
                document.querySelector('.time-filter.active')?.classList.remove('active');
                e.target.classList.add('active');

                this.currentPeriod = e.target.dataset.period;
                await this.loadPriceData();
                this.updateChart();
            });
        });
    }

    updateChart() {
        if (!this.chart) return;

        const chartData = this.priceData.map(point => ({
            x: new Date(point.date),
            y: point.price
        }));

        // Update colors based on trend
        const isPositiveTrend = chartData.length > 1 &&
            chartData[chartData.length - 1].y > chartData[0].y;

        const lineColor = isPositiveTrend ? '#30d158' : '#ff453a';
        const fillColor = isPositiveTrend ? 'rgba(48, 209, 88, 0.1)' : 'rgba(255, 69, 58, 0.1)';

        this.chart.data.datasets[0].data = chartData;
        this.chart.data.datasets[0].borderColor = lineColor;
        this.chart.data.datasets[0].backgroundColor = fillColor;
        this.chart.data.datasets[0].pointHoverBackgroundColor = lineColor;

        this.chart.update('active');
    }

    showLoading(show) {
        const chartWrapper = document.querySelector('.chart-wrapper');
        if (!chartWrapper) return;

        if (show) {
            if (!document.querySelector('.loading')) {
                const loadingDiv = document.createElement('div');
                loadingDiv.className = 'loading';
                loadingDiv.innerHTML = '<div class="spinner"></div>';
                chartWrapper.appendChild(loadingDiv);
            }
        } else {
            const loading = document.querySelector('.loading');
            if (loading) {
                loading.remove();
            }
        }
    }

    showError(message) {
        const chartWrapper = document.querySelector('.chart-wrapper');
        if (!chartWrapper) return;

        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.style.cssText = `
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: #ff453a;
            text-align: center;
            font-size: 16px;
            font-weight: 500;
        `;
        errorDiv.textContent = message;

        chartWrapper.appendChild(errorDiv);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            errorDiv.remove();
        }, 5000);
    }
}

// Export for use in HTML
window.AircraftPriceChart = AircraftPriceChart; 