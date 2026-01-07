# Aircraft Scoring System Implementation

## Overview
This document describes the implementation of the aircraft scoring system for the Jet Finder application, which provides personalized aircraft recommendations based on both objective performance metrics and user priorities.

## Scoring Methodology

### Step 1: Spreadsheet Score (Objective Metrics)
The spreadsheet score is calculated using 5 key performance-per-dollar metrics from the CSV data:

1. **Speed per Dollar** (`normalized_speed_dollar`)
2. **Range per Dollar** (`normalized_range_dollar`) 
3. **Performance per Dollar** (`normalized_performance_dollar`)
4. **Efficiency per Dollar** (`normalized_efficiency_dollar`)
5. **All-Around per Dollar** (`best_all_around_dollar`)

**Calculation:**
- Each metric is converted to a percentage (0-100 scale) using: `min(100, max(0, metric * 10))`
- The spreadsheet score is the average of all valid (non-zero) metrics
- Result: Percentage representing objective value performance

### Step 2: Priority Score (Subjective Preferences)
The priority score reflects how well each aircraft matches the user's personal priorities and requirements.

**Supported Priority Metrics:**
- **Price** (lower is better) - normalized against $100M max
- **Range** (higher is better) - normalized against 8000 NM max  
- **Speed** (higher is better) - normalized against 800 KTS max
- **Passengers** (higher is better) - normalized against 20 passengers max
- **Operating Costs** (lower is better) - normalized against $15K/hr max
- **Runway Length** (lower is better) - normalized against 8000 ft max

**Calculation:**
- Each metric value is normalized to 0-100 percentage
- Normalized scores are multiplied by user-assigned weights
- Final priority score is weighted average of all priority metrics
- Result: Percentage representing fit to user preferences

### Step 3: Combined Score
The combined score averages the spreadsheet score and priority score:
```
combined_score = (spreadsheet_score + priority_score) / 2
```

### Step 4: Final Recommendation Score
The final score incorporates the all-around per dollar metric:
```
all_around_percentage = min(100, max(0, best_all_around_dollar * 10))
final_score = (combined_score + all_around_percentage) / 2
```

## API Endpoints

### `/api/aircraft-scoring` (POST)
Primary endpoint for the new scoring system.

**Request Body:**
```json
{
  "priorities": {
    "price": 30,
    "range": 25, 
    "speed": 20,
    "passengers": 15,
    "total_hourly_cost": 10
  },
  "user_inputs": {
    "budget": 50000000,
    "range_requirement": 3000,
    "passengers": 8,
    "mission_type": "business"
  }
}
```

**Response:**
```json
{
  "aircraft_rankings": [
    {
      "aircraft": { /* aircraft data */ },
      "final_recommendation_score": 93.4,
      "spreadsheet_score": 100.0,
      "priority_score": 73.7,
      "combined_score": 86.9,
      "all_around_percentage": 100.0,
      "scoring_details": { /* breakdown */ }
    }
  ],
  "scoring_methodology": { /* explanation */ },
  "total_aircraft_evaluated": 316
}
```

### `/api/calculate-priority-ranking` (POST)
Updated endpoint using the new scoring system for backward compatibility.

## Frontend Integration

### Aircraft Listings Page
- Default sorting by score (highest first)
- Each aircraft shows display score and value rating
- Score breakdown available in tooltip/modal

### Scoring Demo Page (`/scoring-demo`)
Interactive demonstration page showing:
- Real-time priority weight adjustment
- Mission requirement filters
- Live score calculations
- Top 10 recommendations with detailed breakdowns

## Implementation Details

### Key Functions

#### `calculate_spreadsheet_score(aircraft, user_inputs=None)`
Calculates objective performance score from CSV metrics.

#### `calculate_priority_score(aircraft, priorities)`
Calculates subjective fit score based on user priorities.

#### `normalize_metric_to_percentage(metric_key, value)`
Normalizes different metrics to 0-100 scale with appropriate scaling.

#### `calculate_final_recommendation_score(aircraft, priorities, user_inputs=None)`
Main function implementing the complete scoring methodology.

### Data Structure
Each aircraft record includes:
- Basic specs (price, range, speed, passengers)
- Performance metrics (all per-dollar values)
- Calculated scores (display_score, score_breakdown)
- Value rating (Excellent, Very Good, Good, Fair, Poor)

## Testing

### Test Suite (`test_scoring_system.py`)
Comprehensive test suite verifying:
- API endpoint functionality
- Scoring logic accuracy
- Expected score calculations
- Real aircraft data processing

**Test Results:**
- ✅ All 316 aircraft evaluated successfully
- ✅ Scoring methodology implemented correctly
- ✅ API endpoints returning expected results
- ✅ Top performers identified (Gulfstream models leading)

### Demo Verification
- Interactive scoring demo at `/scoring-demo`
- Real-time priority adjustment
- Live API integration
- Visual score breakdowns

## Performance Characteristics

### Top Performing Aircraft (Sample)
1. **G550 (Gulfstream)** - 93.4% final score
2. **G-V (Gulfstream)** - 93.0% final score  
3. **G650 (Gulfstream)** - 92.5% final score
4. **Global Express (Bombardier)** - 92.5% final score
5. **G650ER (Gulfstream)** - 92.5% final score

### Score Distribution
- High-performance aircraft typically score 80-95%
- Mid-range aircraft score 40-70%
- Entry-level aircraft score 20-50%
- Poor value aircraft score below 20%

## Benefits

1. **Objective Foundation**: Uses verified spreadsheet performance metrics
2. **Personalized Results**: Incorporates individual user priorities
3. **Transparent Methodology**: Clear, explainable scoring steps
4. **Comprehensive Coverage**: Evaluates all 316 aircraft in database
5. **Interactive Experience**: Real-time score updates and filtering
6. **Value-Focused**: Emphasizes performance-per-dollar efficiency

## Future Enhancements

1. **Machine Learning**: Historical user preferences for improved recommendations
2. **Market Conditions**: Real-time pricing and availability integration
3. **Advanced Filters**: Operating cost categories, maintenance requirements
4. **Comparison Tools**: Side-by-side aircraft comparisons with scoring
5. **Export Capabilities**: PDF reports with detailed score analysis 