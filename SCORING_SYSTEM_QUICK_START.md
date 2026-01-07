# Aircraft Scoring System - Quick Start Guide

## 🚀 Getting Started

The aircraft scoring system is now live and ready to use! Here's how to access all the features:

### 🌐 **Live Demo**
Visit: **http://localhost:5012/scoring-demo**
- Interactive priority sliders
- Real-time score calculations  
- Top 10 aircraft recommendations
- Visual score breakdowns

### 📊 **API Endpoints**

#### Primary Scoring API
```bash
POST /api/aircraft-scoring
```

**Example Request:**
```bash
curl -X POST http://localhost:5012/api/aircraft-scoring \
  -H "Content-Type: application/json" \
  -d '{
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
      "passengers": 8
    }
  }'
```

#### Other Useful Endpoints
- `GET /api/scoring-methodology` - Get scoring information
- `POST /api/calculate-priority-ranking` - Legacy compatibility
- `GET /aircraft-listings?sort=score_desc` - Browse aircraft by score

### 🎯 **How to Use Priorities**

Set weights (0-50) for what matters most to you:

| Priority | Description | Weight Example |
|----------|-------------|----------------|
| **Price** | Lower is better | 30% |
| **Range** | Higher is better | 25% |
| **Speed** | Higher is better | 20% |
| **Passengers** | More capacity | 15% |
| **Operating Cost** | Lower hourly cost | 10% |

**Total should add up to 100%**

### 📈 **Understanding Scores**

#### Score Components:
1. **Spreadsheet Score (0-100%)**: Objective performance per dollar
2. **Priority Score (0-100%)**: How well it matches your preferences  
3. **Combined Score**: Average of spreadsheet + priority
4. **Final Score**: Average of combined + all-around/$ metric

#### Score Ratings:
- **80-100%** = Excellent (Outstanding value)
- **60-79%** = Very Good (Strong performer)
- **40-59%** = Good (Solid choice)
- **20-39%** = Fair (Basic option)
- **0-19%** = Poor (Below average)

### 🏆 **Current Top Performers**

Based on our scoring system, these aircraft consistently rank highest:

1. **Gulfstream G550** - 93.4% avg score
2. **Gulfstream G-V** - 93.0% avg score  
3. **Gulfstream G650** - 92.5% avg score
4. **Bombardier Global Express** - 92.5% avg score
5. **Gulfstream G650ER** - 92.5% avg score

### 🔧 **Testing the System**

Run the test suite:
```bash
python test_scoring_system.py
```

Expected output:
```
✅ All tests passed! The scoring system is working correctly.
```

### 💡 **Pro Tips**

1. **Adjust Priorities**: Change weights to see how rankings shift
2. **Budget Constraints**: Set realistic budget limits
3. **Mission Requirements**: Specify minimum range/passengers needed
4. **Compare Scores**: Look at score breakdowns to understand why aircraft rank differently
5. **Value Focus**: High all-around/$ scores indicate exceptional value

### 🔍 **Example Scenarios**

#### Business Travel Priority:
```json
{
  "priorities": {
    "speed": 35,
    "range": 30, 
    "price": 20,
    "passengers": 15
  }
}
```

#### Cost-Conscious Priority:
```json
{
  "priorities": {
    "price": 40,
    "total_hourly_cost": 30,
    "range": 20,
    "passengers": 10
  }
}
```

#### Family/Group Travel:
```json
{
  "priorities": {
    "passengers": 35,
    "price": 25,
    "range": 25,
    "speed": 15
  }
}
```

### 📞 **Need Help?**

- Check `/scoring-demo` for interactive examples
- Review `AIRCRAFT_SCORING_IMPLEMENTATION.md` for technical details
- Run test suite to verify system functionality
- All 316 aircraft are evaluated automatically

---

**🎉 The scoring system is live and ready to help you find the perfect aircraft for your needs!** 