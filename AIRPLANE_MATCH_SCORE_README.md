# Airplane Match Score System

## Overview

The new **Airplane Match Score System** is a sophisticated aircraft evaluation algorithm that helps users find their perfect aircraft match by combining data-driven analysis with personalized priorities. This system replaces traditional single-metric sorting with a comprehensive percentage-based scoring approach.

## How It Works

### 1. Raw Data Final Score (Base Score)

The system calculates percentages for 5 core value metrics and averages them:

- **Speed/$** - Speed performance per dollar spent
- **Range/$** - Range capability per dollar spent  
- **Performance/$** - Overall performance per dollar spent
- **Efficiency/$** - Fuel efficiency per dollar spent
- **All Around/$** - Combined metrics per dollar spent

Each metric is normalized to a 0-100% scale where 100% represents the best performer in that category across all aircraft.

**Formula:** Raw Data Final Score = (Speed/$ % + Range/$ % + Performance/$ % + Efficiency/$ % + All Around/$ %) ÷ 5

### 2. User Priority Final Score (Personalized Score)

Users can select 1-20 priority categories from any CSV column, including:

#### Performance Categories
- Speed (kts)
- Range (nm) 
- Max Altitude (ft)
- Passenger Capacity

#### Value Categories  
- Speed per Dollar
- Range per Dollar
- Performance per Dollar
- Efficiency per Dollar
- All-Around Value per Dollar

#### Cost Categories
- Purchase Price
- Annual Operating Budget
- Multi-Year Total Cost
- Hourly Operating Cost
- Cost per Mile

#### Physical Specifications
- Cabin Volume
- Cabin Height/Width/Length
- Baggage Volume
- Runway Length Required

#### And Many More...

Each selected priority is normalized to 0-100% and then averaged.

**Formula:** User Priority Final Score = (Sum of selected priority percentages) ÷ (Number of priorities selected)

### 3. Final Match Score

The system combines both scores to create the ultimate match percentage:

**Formula:** 
- If no user priorities selected: Final Match Score = Raw Data Final Score
- If user priorities selected: Final Match Score = (Raw Data Final Score + User Priority Final Score) ÷ 2

## Key Features

### 🎯 **Intelligent Scoring**
- Percentage-based rankings ensure fair comparison across all metrics
- Higher percentages always indicate better matches for user needs
- Transparent scoring breakdown shows exactly how scores are calculated

### 🔧 **Flexible Prioritization**
- Select 1-20 categories that matter most to you
- Choose from 50+ aircraft characteristics
- Real-time priority counter and validation

### 📊 **Comprehensive Data**
- Integrates with existing price chart functionality
- Market statistics and overview data
- Sortable results by any metric

### 🎨 **Modern Interface**
- StockX/Robinhood-inspired design
- Mobile-responsive layout
- Interactive charts and tooltips

## Technical Implementation

### Backend Functions

#### `calculate_raw_data_percentages(aircraft_list)`
Calculates the 5 core value metric percentages for all aircraft.

#### `calculate_user_priority_score(aircraft_list, user_priorities)`
Processes user-selected priorities and calculates personalized scores.

#### `calculate_airplane_match_score(aircraft_list, user_priorities=None)`
Main function that combines raw data and user priority scores.

### API Endpoints

#### `POST /api/airplane-match-score`
**Request:**
```json
{
  "user_inputs": {
    "average_trip_length": 400,
    "num_trips": 104,
    "years_ownership": 5
  },
  "user_priorities": ["speed", "range", "price", "cabin_volume"]
}
```

**Response:**
```json
{
  "success": true,
  "aircraft": [...],
  "total_count": 158,
  "scoring_method": "Enhanced Match Score",
  "user_priorities_count": 4,
  "scoring_breakdown": {
    "raw_data_metrics": ["Speed/$", "Range/$", "Performance/$", "Efficiency/$", "All Around/$"],
    "user_priorities": ["speed", "range", "price", "cabin_volume"],
    "calculation": "Average of Raw Data Score + User Priority Score"
  }
}
```

#### `GET /api/stock-market-overview`
Provides market statistics and top-performing aircraft.

#### `GET /api/available-columns`
Returns all available columns for priority selection with metadata.

### Frontend Integration

The system integrates seamlessly with the existing Jet Finder interface:

1. **Navigation Integration**: Added "Airplane Stock Market" tab to main navigation
2. **Price Chart Integration**: Each aircraft card links to existing price chart functionality
3. **Responsive Design**: Works perfectly on desktop and mobile devices

## Usage Examples

### Example 1: Speed-Focused Business User
**Selected Priorities:** Speed, Range, Hourly Cost, Runway Length
**Result:** Aircraft optimized for fast business travel with reasonable operating costs

### Example 2: Budget-Conscious Family User  
**Selected Priorities:** Price, Passenger Capacity, Annual Budget, Baggage Volume
**Result:** Affordable aircraft with good family-friendly features

### Example 3: Luxury-Focused User
**Selected Priorities:** Cabin Volume, Newest Model Year, Speed, All-Around Value
**Result:** Premium aircraft with latest amenities and performance

## Score Interpretation

- **90-100%**: Exceptional match - This aircraft perfectly aligns with your priorities
- **80-89%**: Excellent match - Strong candidate with minor trade-offs
- **70-79%**: Good match - Solid option worth considering
- **60-69%**: Fair match - May require compromises in some areas
- **Below 60%**: Poor match - Significant misalignment with priorities

## Benefits Over Traditional Systems

### ✅ **Advantages**
- **Holistic Evaluation**: Considers multiple factors simultaneously
- **Personalized Results**: Adapts to individual user priorities
- **Transparent Scoring**: Clear breakdown of how scores are calculated
- **Fair Comparison**: Percentage-based system ensures equal weighting
- **Flexible Selection**: Up to 20 customizable priority categories

### ❌ **Previous Limitations**
- Single-metric sorting (price, speed, etc.)
- No personalization options
- Difficult to compare apples-to-apples
- Limited user control over ranking factors

## Navigation & Access

The Airplane Stock Market is accessible through:
1. **Main Navigation**: Hamburger menu → "Airplane Stock Market"
2. **Direct URL**: `/airplane-stock-market`
3. **Price Charts**: Each aircraft result links to detailed price charts

## Future Enhancements

- **Save User Profiles**: Remember priority preferences
- **Comparison Tool**: Side-by-side aircraft comparison
- **Advanced Filters**: Filter by manufacturer, year range, etc.
- **Market Trends**: Track scoring trends over time
- **Export Results**: Download rankings as PDF/Excel

## Technical Requirements

- **Backend**: Flask with enhanced scoring algorithms
- **Frontend**: Modern JavaScript ES6+ with async/await
- **Database**: Uses existing CSV data structure
- **APIs**: RESTful endpoints with JSON responses
- **UI**: Bootstrap 5 + custom CSS with mobile optimization

## Support & Feedback

For questions about the scoring algorithm or suggestions for improvement, contact the development team. The system is designed to evolve based on user feedback and market needs.

---

*This system represents a significant advancement in aircraft selection technology, providing users with unprecedented control and insight into their aircraft purchasing decisions.* 