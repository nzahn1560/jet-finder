# Aircraft Price Chart Visualization

## Overview

This feature provides interactive aircraft price charts inspired by Robinhood and StockX, offering users a modern way to visualize aircraft value trends over time.

## Features

### 📊 Interactive Price Charts
- **Robinhood-style line graphs** with smooth animations
- **Touch and mouse support** for precise data exploration
- **Real-time tooltips** showing price, date, and volume data
- **Multiple timeframes**: 1M, 3M, 6M, 1Y, All Time

### 🎨 Design
- **Dark theme** optimized for aviation industry aesthetics
- **Mobile-first responsive design** works on all devices
- **Accessibility features** including high contrast and reduced motion support
- **Modern UI components** with smooth hover effects and transitions

### 📱 Mobile Optimization
- **Touch-friendly interactions** with gesture support
- **Optimized layouts** for portrait and landscape orientations
- **Performance optimized** for smooth scrolling and chart interactions

## Implementation

### Backend API Endpoints

#### `/api/aircraft/<id>/price-history`
Returns historical price data for a specific aircraft.

**Parameters:**
- `period`: Time period (1M, 3M, 6M, 1Y, ALL)

**Response:**
```json
{
  "success": true,
  "price_history": [
    {
      "date": "2024-01-01T00:00:00",
      "price": 8200000,
      "volume": 2,
      "high": 8250000,
      "low": 8150000
    }
  ],
  "current_price": 8200000,
  "price_change": {
    "amount": 50000,
    "percent": 0.61
  },
  "stats": {
    "day_high": 8250000,
    "day_low": 8150000,
    "avg_price": 8200000,
    "volume": 15
  }
}
```

#### `/aircraft/<id>/price-chart`
Renders the interactive price chart page for a specific aircraft.

### Frontend Components

#### `AircraftPriceChart` Class
Main JavaScript class handling chart functionality:

```javascript
const chart = new AircraftPriceChart(aircraftId);
```

**Features:**
- Chart.js integration with custom styling
- Touch event handling for mobile devices
- Dynamic color changes based on price trends
- Custom tooltip positioning and content
- Smooth animations and transitions

### File Structure

```
templates/
├── aircraft_price_chart.html    # Main price chart page
└── price_chart_demo.html        # Demo/showcase page

static/
├── css/
│   └── price_chart.css          # Dedicated styling
└── js/
    └── aircraft_price_chart.js  # Chart functionality

app.py                           # Backend routes and data generation
```

## Usage

### 1. Access the Demo Page
Visit `/price-charts-demo` to see featured aircraft with price chart links.

### 2. View Individual Aircraft Charts
Navigate to `/aircraft/<id>/price-chart` for any aircraft to see its price history.

### 3. Interact with Charts
- **Desktop**: Hover over the chart line to see tooltips
- **Mobile**: Touch and drag across the chart to explore data points
- **Time Filters**: Click time period buttons to change the view

### 4. Integrate into Existing Pages
Add price chart links to aircraft listings:

```html
<a href="{{ url_for('aircraft_price_chart', aircraft_id=aircraft.id) }}">
    View Price Chart
</a>
```

## Data Structure

The system expects aircraft data with the following structure:

```python
{
    'id': 1,
    'aircraft_name': 'Citation CJ3+',
    'manufacturer': 'Cessna',
    'model': 'CJ3+',
    'price': 8200000,
    'range': 2040,
    'speed': 464,
    'passengers': 9
}
```

Price history data is currently generated using realistic mock data that includes:
- Market volatility based on aircraft characteristics
- Volume variations for different aircraft price ranges
- Trend simulation with random walk algorithms

## Customization

### Styling
Modify `static/css/price_chart.css` to customize:
- Color schemes and themes
- Layout and spacing
- Animation speeds and effects
- Mobile breakpoints

### Chart Configuration
Update `static/js/aircraft_price_chart.js` to adjust:
- Chart.js options and styling
- Tooltip content and positioning
- Touch interaction sensitivity
- Data refresh intervals

### Mock Data Generation
Customize `generate_mock_price_history()` in `app.py` to:
- Adjust volatility and trend patterns
- Modify time periods and data density
- Add additional market factors

## Dependencies

- **Chart.js**: Interactive chart library
- **Font Awesome**: Icons for UI elements
- **Flask**: Backend framework

## Browser Support

- **Modern browsers**: Chrome, Firefox, Safari, Edge
- **Mobile browsers**: iOS Safari, Chrome Mobile, Samsung Internet
- **Accessibility**: Screen readers, keyboard navigation

## Performance Considerations

- Chart data is cached on the frontend to minimize API calls
- Mobile touch events use passive listeners for smooth scrolling
- CSS animations use hardware acceleration
- Images and assets are optimized for fast loading

## Future Enhancements

1. **Real-time data integration** with aircraft marketplaces
2. **Comparison charts** for multiple aircraft models
3. **Market sentiment indicators** and trend predictions
4. **Export functionality** for charts and data
5. **Notification system** for price alerts
6. **Advanced filtering** by aircraft specifications

## Testing

To test the price chart functionality:

1. Start the Flask development server
2. Navigate to `/price-charts-demo`
3. Click "View Price Chart" on any aircraft card
4. Test interactions on both desktop and mobile devices
5. Verify tooltips appear and data loads correctly across all time periods 