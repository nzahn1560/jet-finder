// Constants
const API_BASE_URL = '/api';
let rangeChart = null;

// DOM Elements
document.addEventListener('DOMContentLoaded', () => {
    fetchAircraftData();
    fetchAircraftRanges();
});

// Fetch aircraft data from the API and populate the UI
async function fetchAircraftData() {
    try {
        const response = await fetch(`${API_BASE_URL}/aircraft`);
        const data = await response.json();

        if (data.success && data.aircraft) {
            populateAircraftTable(data.aircraft);
            populateAircraftCards(data.aircraft);
        } else {
            console.error('Failed to load aircraft data:', data.message || 'Unknown error');
            showError('Failed to load aircraft data. Please try again later.');
        }
    } catch (error) {
        console.error('Error fetching aircraft data:', error);
        showError('An error occurred while fetching aircraft data.');
    }
}

// Fetch aircraft range data and create chart
async function fetchAircraftRanges() {
    try {
        const response = await fetch(`${API_BASE_URL}/aircraft/ranges`);
        const data = await response.json();

        if (data.success && data.ranges) {
            createRangeChart(data.ranges);
        } else {
            console.error('Failed to load aircraft range data:', data.message || 'Unknown error');
        }
    } catch (error) {
        console.error('Error fetching aircraft range data:', error);
    }
}

// Populate aircraft table
function populateAircraftTable(aircraftList) {
    const tableBody = document.querySelector('#aircraftTable tbody');
    tableBody.innerHTML = '';

    aircraftList.forEach(aircraft => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${aircraft.name || 'N/A'}</td>
            <td>${aircraft.manufacturer || 'N/A'}</td>
            <td>${aircraft.type || 'N/A'}</td>
            <td>${aircraft.range || 'N/A'}</td>
            <td>${aircraft.cruise_speed || 'N/A'}</td>
            <td>${aircraft.price ? '$' + aircraft.price + 'M' : 'N/A'}</td>
        `;
        tableBody.appendChild(row);
    });
}

// Create featured aircraft cards
function populateAircraftCards(aircraftList) {
    const cardsContainer = document.getElementById('aircraft-cards');
    cardsContainer.innerHTML = '';

    // Select random 3 aircraft to feature
    const featuredAircraft = getRandomItems(aircraftList, 3);

    featuredAircraft.forEach(aircraft => {
        const card = document.createElement('div');
        card.className = 'col-md-4';
        card.innerHTML = `
            <div class="card aircraft-card h-100">
                <div class="card-header bg-secondary text-white">
                    ${aircraft.manufacturer || 'Unknown Manufacturer'}
                </div>
                <div class="card-body d-flex flex-column">
                    <h5 class="card-title">${aircraft.name || 'Unknown Aircraft'}</h5>
                    <p class="card-text mb-1"><strong>Type:</strong> ${aircraft.type || 'N/A'}</p>
                    <p class="card-text mb-1"><strong>Range:</strong> ${aircraft.range || 'N/A'} NM</p>
                    <p class="card-text mb-1"><strong>Cruise Speed:</strong> ${aircraft.cruise_speed || 'N/A'} ktas</p>
                    <p class="card-text mb-3"><strong>Price:</strong> ${aircraft.price ? '$' + aircraft.price + 'M' : 'N/A'}</p>
                    <button class="btn btn-primary mt-auto" onclick="showAircraftDetails('${aircraft.name}')">View Details</button>
                </div>
            </div>
        `;
        cardsContainer.appendChild(card);
    });
}

// Create range comparison chart
function createRangeChart(rangeData) {
    const ctx = document.getElementById('rangeChart').getContext('2d');

    // If a chart already exists, destroy it
    if (rangeChart) {
        rangeChart.destroy();
    }

    // Sort data by range (descending)
    const sortedData = [...rangeData].sort((a, b) => b.range - a.range);

    // Take top 10 for readability
    const topRanges = sortedData.slice(0, 10);

    rangeChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: topRanges.map(item => item.name),
            datasets: [{
                label: 'Range (NM)',
                data: topRanges.map(item => item.range),
                backgroundColor: 'rgba(54, 162, 235, 0.6)',
                borderColor: 'rgba(54, 162, 235, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Range (Nautical Miles)'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Aircraft'
                    }
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: 'Aircraft Range Comparison (Top 10)',
                    font: {
                        size: 16
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            return `Range: ${context.raw} NM`;
                        }
                    }
                }
            }
        }
    });
}

// Utility function to get random items from an array
function getRandomItems(array, count) {
    const shuffled = [...array].sort(() => 0.5 - Math.random());
    return shuffled.slice(0, count);
}

// Function to show aircraft details (placeholder for now)
function showAircraftDetails(aircraftName) {
    alert(`Details for ${aircraftName} would be shown here in a future implementation.`);
}

// Display error message
function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'alert alert-danger';
    errorDiv.textContent = message;

    const container = document.querySelector('.container');
    container.insertBefore(errorDiv, container.firstChild);

    // Automatically remove after 5 seconds
    setTimeout(() => {
        errorDiv.remove();
    }, 5000);
} 