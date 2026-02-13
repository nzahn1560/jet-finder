# Strict Peer-Group Comparison - Implementation Complete

## ✅ What Changed

### STRICT Same-Model Comparison Only

The match scoring system now **ONLY compares aircraft within the exact same performance profile** (same model).

**Before:**
- Compared to same model
- Fallback to same category if < 5 in model
- Fallback to all aircraft if < 3 in category

**After (Now):**
- **ONLY** compares to exact same model
- **NO fallbacks** to category or global
- If only 1 aircraft of that model → scores reflect that (50th percentile/3 stars)

---

## 🎯 How It Works

### Performance Profile = Aircraft Model

Each aircraft's **performance profile** is determined by its **exact model name**:
- `Cessna Citation CJ3` → Only compared to other CJ3s
- `Gulfstream G650` → Only compared to other G650s
- `Pilatus PC-12` → Only compared to other PC-12s
- `Bombardier Global 7500` → Only compared to other Global 7500s

### Peer Group Logic

```python
def get_peer_group(aircraft, all_aircraft):
    """
    STRICT: Only exact model matches (same performance profile)
    NO category fallback
    NO global fallback
    """
    model = aircraft.get('aircraft_name')
    
    # Return ONLY aircraft with exact same model
    peer_group = [a for a in all_aircraft if a.get('aircraft_name') == model]
    
    # If no peers found, return just this aircraft
    if not peer_group:
        peer_group = [aircraft]
    
    return peer_group
```

### Scoring Within Peer Group

**Example: Citation CJ3**
- Dataset has 8 CJ3 listings
- Each CJ3 compared **only** to the other 7 CJ3s
- Scores reflect relative position within those 8 CJ3s

**Example: Unique Aircraft**
- Dataset has 1 Gulfstream G280
- No other G280s to compare to
- Scores default to 50th percentile (3 stars)

---

## 📊 What This Means For Scores

### Multiple Aircraft of Same Model

**Cessna Citation CJ3** (8 aircraft in dataset)
- Aircraft #1: 2018, 500 hrs, excellent → **5 stars Condition**
- Aircraft #2: 2015, 1200 hrs, good → **4 stars Condition**
- Aircraft #3: 2012, 2000 hrs, fair → **3 stars Condition**
- Aircraft #4: 2010, 3500 hrs, average → **2 stars Condition**

**Each CJ3 ranked against other CJ3s:**
- Top 20% of CJ3s → 5 stars
- 60-80% of CJ3s → 4 stars
- 40-60% of CJ3s → 3 stars
- 20-40% of CJ3s → 2 stars
- Bottom 20% of CJ3s → 1 star

### Single Aircraft of Model

**Gulfstream G280** (only 1 in dataset)
- No peers to compare to
- All categories default to **3 stars** (50th percentile)
- Reflects "average" since no comparison data

### Why This Is Better

**Before (with fallbacks):**
- CJ3 compared to all Citations → mixing different performance capabilities
- Not apples-to-apples comparison
- Scores didn't reflect true peer standing

**After (strict):**
- CJ3 compared **only** to other CJ3s → exact performance peers
- Apples-to-apples comparison
- Scores show true standing within same aircraft model

---

## 🔍 Category Scoring Details

### 1. Performance (25% weight)
- Range, speed, altitude, passengers, cabin volume
- **Same model = same specs** (from manufacturer)
- Usually all same model get similar performance scores
- Differences only if listing data has variations

### 2. Condition (25% weight)
- **Airframe time**: Lower hours → Higher rank within model
- **Engine hours vs TBO**: Lower % used → Higher rank
- **Year**: Newer → Higher rank
- **Compared only to same model peers**

Example CJ3s:
- 2020 CJ3, 300 hrs → Top condition in CJ3 group
- 2012 CJ3, 2500 hrs → Lower condition in CJ3 group

### 3. Interior/Exterior (15% weight)
- Interior refurb year (newer better)
- Paint year (newer better)
- Manual 1-5 scores if provided
- **Compared only to same model peers**

Example CJ3s:
- Interior redone 2023 → Top cosmetic in CJ3 group
- Interior redone 2015 → Lower cosmetic in CJ3 group

### 4. Avionics (15% weight)
- Avionics value estimate
- Higher value → Higher rank within model
- **Compared only to same model peers**

Example CJ3s:
- $500k avionics package → Top avionics in CJ3 group
- $200k avionics package → Lower avionics in CJ3 group

### 5. Value (20% weight)
- Performance/price ratio
- Better value = higher performance per dollar
- **Compared only to same model peers**

Example CJ3s:
- $5M for 2020 model → Good value in CJ3 group
- $6.5M for 2015 model → Poor value in CJ3 group

---

## 💡 "Top Reasons" Now Show Peer Context

**Before:**
- "Excellent performance specs (5/5 ⭐)"
- Generic statements

**After:**
- "Compared to 8 other Citation CJ3"
- "Better condition than 75% of peers"
- "Top 10% for performance in model"
- "Above-average avionics for CJ3"

Shows **relative standing within peer group**.

---

## 📈 Example Comparisons

### Scenario 1: Popular Model (Many Peers)

**King Air 350** - 12 aircraft in dataset

Aircraft A (2020, 400 hrs, $5.2M):
- Condition: ⭐⭐⭐⭐⭐ (5/5) - "Better condition than 90% of King Air 350s"
- Value: ⭐⭐⭐ (3/5) - "Average value for King Air 350"
- Avionics: ⭐⭐⭐⭐ (4/5) - "Above-average avionics for King Air 350"

Aircraft B (2010, 3000 hrs, $3.8M):
- Condition: ⭐⭐ (2/5) - "Higher hours than average for model"
- Value: ⭐⭐⭐⭐⭐ (5/5) - "Best value in King Air 350 category"
- Avionics: ⭐⭐⭐ (3/5) - "Average avionics for King Air 350"

### Scenario 2: Rare Model (Few Peers)

**Dassault Falcon 8X** - 2 aircraft in dataset

Aircraft A (2019, 600 hrs, $42M):
- Condition: ⭐⭐⭐⭐ (4/5) - Compared to 1 other Falcon 8X
- Value: ⭐⭐⭐⭐ (4/5) - Better value than other Falcon 8X

Aircraft B (2016, 1200 hrs, $38M):
- Condition: ⭐⭐⭐ (3/5) - Higher hours than other Falcon 8X
- Value: ⭐⭐⭐⭐⭐ (5/5) - Best value of Falcon 8X listings

### Scenario 3: Unique Model (No Peers)

**Embraer Phenom 300E** - 1 aircraft in dataset

Aircraft A (2021, 250 hrs, $9.5M):
- All categories: ⭐⭐⭐ (3/5) - "Only Phenom 300E in dataset"
- No peer comparison available
- Scores reflect neutral/average

---

## 🔧 Technical Implementation

### Changes Made

**File**: `legacy/match_scoring_v2.py`

1. **`get_peer_group()` function**:
   ```python
   # BEFORE
   peer_group = same_model or same_category or all_aircraft
   
   # AFTER
   peer_group = same_model only (no fallbacks)
   ```

2. **`calculate_percentile_rank()` function**:
   - Added check for single-value arrays
   - Returns 50th percentile if no peers (can't rank)
   - More accurate numpy-based percentile calculation

3. **`calculate_match_score_v2()` function**:
   - Returns `peer_group_model` (aircraft model name)
   - Returns `comparison_note` (e.g., "Compared to 8 other Citation CJ3")
   - Clearer messaging about peer group

4. **`generate_top_reasons_v2()` function**:
   - First bullet: "Compared to X other [Model]"
   - Relative statements: "Better condition than Y% of peers"
   - Model-specific context

---

## ✅ Verification

### How To Check It's Working

1. **Open**: `http://localhost:5015`

2. **Find aircraft with multiple listings** (e.g., King Air 350, Citation CJ3)
   - Look at 2-3 listings of same model
   - Compare their star ratings
   - Newer/lower-hours should have higher Condition stars

3. **Check "Why This Match" section**:
   - Should say "Compared to X other [Model Name]"
   - Should give percentile-based reasons

4. **Find unique aircraft** (only 1 of that model)
   - Should mostly show 3 stars
   - Should say "Only [Model] in dataset"

5. **Browser Console**:
   ```
   🎯 Calculating match scores for all aircraft on page load...
   ✅ Match scores calculated for 314 aircraft
   Sample aircraft with scores: {...peer_group_size: 8, peer_group_model: "King Air 350"}
   ```

---

## 📊 Expected Results

### Models With Multiple Listings

**You'll see variation in stars:**
- Best condition CJ3 → 5 stars Condition
- Worst condition CJ3 → 1-2 stars Condition
- Each ranked against CJ3 peers only

### Unique Models

**You'll see mostly 3 stars:**
- No variation possible (no peers)
- Default to middle/average
- Fair representation of "unknown relative standing"

---

## 🎉 Summary

✅ **STRICT peer-group comparison implemented**  
✅ **NO fallback to category or global**  
✅ **Each aircraft compared ONLY to same model**  
✅ **Scores reflect true standing within performance profile**  
✅ **"Why This Match" shows peer context**  
✅ **Apples-to-apples comparison**  

**Result**: More accurate, meaningful scores that truly reflect how an aircraft compares to its direct peers (same model/performance profile).

---

**Version**: 2.2.0  
**Date**: January 26, 2026  
**Status**: Production-Ready ✅
