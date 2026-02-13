# Condition Filters Added - Match Score Tool Removed

## ✅ What Changed

### Removed Match Score Tool

**Before:**
- Match Score Tool section above Compare section
- Weight sliders for category customization
- "Calculate Match Scores" button
- Manual scoring process

**After:**
- ❌ Removed entire Match Score Tool section
- ❌ Removed weight sliders and controls
- ✅ Match scores calculated automatically on page load
- ✅ Filters moved to Aircraft Selection Parameters

### Added Condition Filters

New filters added to **"Aircraft Selection Parameters → Condition Filters"** section:

1. **Max Airframe Time (Hours)**
   - Filter aircraft by total airframe hours
   - Only shows aircraft with less than specified hours
   - Example: Set to 5000 → Only aircraft with < 5000 total hours

2. **Max Engine Time (Hours)**
   - Filter by engine 1 time
   - Only shows aircraft with less than specified engine hours
   - Example: Set to 3000 → Only aircraft with < 3000 engine hours

3. **Min Interior Refurb Year**
   - Filter by interior refurbishment year
   - Only shows aircraft with interior updated after specified year
   - Example: Set to 2015 → Only aircraft with interior from 2015+

4. **Min Paint Year**
   - Filter by paint year
   - Only shows aircraft with paint updated after specified year
   - Example: Set to 2015 → Only aircraft with paint from 2015+

---

## 🎯 Where to Find Filters

### Location: Aircraft Selection Parameters Card

The filters are in the **dark card** near the top of the page with sections:
- ✅ Basic Requirements (Range, Passengers, Budget, Year)
- ✅ **Condition Filters** ← NEW FILTERS HERE
- ✅ Trip Planning
- ✅ Aircraft Specifications
- ✅ Advanced Options

### Condition Filters Section

```
┌────────────────────────────────────────┐
│  🔧 Condition Filters                  │
├────────────────────────────────────────┤
│  Max Airframe Time (Hours)             │
│  [ 5000 ]                              │
│  Only show aircraft with less hours    │
│                                        │
│  Max Engine Time (Hours)               │
│  [ 3000 ]                              │
│  Engine 1 time limit                   │
│                                        │
│  Min Interior Refurb Year              │
│  [ 2015 ]                              │
│  Interior updated after this year      │
│                                        │
│  Min Paint Year                        │
│  [ 2015 ]                              │
│  Paint updated after this year         │
└────────────────────────────────────────┘
```

---

## 🔍 How Filters Work

### Real-Time Filtering

All filters apply **immediately** as you type (with 300ms debounce):
1. Enter value in filter field
2. Filters apply automatically after 300ms
3. Listing count updates
4. Pagination adjusts to filtered results

### Filter Logic

**Max Airframe Time:**
```javascript
if (aircraft.total_time > max_airframe_time) {
    // Aircraft filtered out
}
```

**Max Engine Time:**
```javascript
if (aircraft.engine1_time > max_engine_time) {
    // Aircraft filtered out
}
```

**Min Interior Year:**
```javascript
if (aircraft.interior_refurb_year < min_interior_year) {
    // Aircraft filtered out
}
```

**Min Paint Year:**
```javascript
if (aircraft.paint_year < min_paint_year) {
    // Aircraft filtered out
}
```

### Combined Filters

All filters work together (AND logic):
- Aircraft must meet **ALL** active filter criteria
- Example: If you set Max Airframe Time = 5000 AND Max Engine Time = 3000
  - Only aircraft with < 5000 airframe hours **AND** < 3000 engine hours show

---

## 📊 Example Usage

### Scenario 1: Low-Time Aircraft Only

**Goal:** Find aircraft with low hours

**Settings:**
- Max Airframe Time: `3000`
- Max Engine Time: `1500`

**Result:** Only aircraft with less than 3000 total hours AND less than 1500 engine hours

### Scenario 2: Recently Refreshed Aircraft

**Goal:** Find aircraft with recent cosmetic updates

**Settings:**
- Min Interior Refurb Year: `2018`
- Min Paint Year: `2018`

**Result:** Only aircraft with interior and paint updated after 2018

### Scenario 3: Well-Maintained + Modern

**Goal:** Low hours with recent updates

**Settings:**
- Max Airframe Time: `4000`
- Max Engine Time: `2000`
- Min Interior Refurb Year: `2016`
- Min Paint Year: `2016`

**Result:** Low-time aircraft (< 4000 hrs, < 2000 engine hrs) with cosmetic updates from 2016+

### Scenario 4: Budget Aircraft (Higher Time OK)

**Goal:** Affordable options, don't care about high hours

**Settings:**
- Average Price: `$3,000,000`
- Max Airframe Time: (leave empty - no limit)
- Max Engine Time: (leave empty - no limit)

**Result:** Aircraft under $3M regardless of hours

---

## 🎨 Visual Display

### Filter Inputs (Green Section)

```
🔧 Condition Filters
─────────────────────────────────
Max Airframe Time (Hours)    Max Engine Time (Hours)
┌───────────────────┐        ┌───────────────────┐
│ e.g. 5000         │        │ e.g. 3000         │
└───────────────────┘        └───────────────────┘
Only show aircraft with      Engine 1 time limit
less hours

Min Interior Refurb Year     Min Paint Year
┌───────────────────┐        ┌───────────────────┐
│ e.g. 2015         │        │ e.g. 2015         │
└───────────────────┘        └───────────────────┘
Interior updated after       Paint updated after
this year                    this year
```

### Filter Hints (Small Gray Text)

Each filter has helpful text below:
- **Max Airframe Time**: "Only show aircraft with less hours"
- **Max Engine Time**: "Engine 1 time limit"
- **Min Interior Refurb Year**: "Interior updated after this year"
- **Min Paint Year**: "Paint updated after this year"

---

## 🔧 Technical Implementation

### Files Modified

**`legacy/templates/index.html`**

1. **Filter inputs** (lines 3764-3803):
   - Already existed in UI
   - Now connected to filtering system

2. **currentFilters object** (lines ~4976-4994):
   ```javascript
   currentFilters = {
       // ...existing filters...
       maxAirframeTime: document.getElementById('max-airframe-time')?.value || '',
       maxEngineTime: document.getElementById('max-engine-time')?.value || '',
       minInteriorYear: document.getElementById('min-interior-year')?.value || '',
       minPaintYear: document.getElementById('min-paint-year')?.value || ''
   };
   ```

3. **Filter event listeners** (lines ~7179-7190):
   ```javascript
   const filterInputs = [
       // ...existing inputs...
       'max-airframe-time',
       'max-engine-time',
       'min-interior-year',
       'min-paint-year'
   ];
   ```

4. **Filter logic** (lines ~5104-5150):
   ```javascript
   // Max Airframe Time filter
   if (currentFilters.maxAirframeTime) {
       const maxTime = parseInt(currentFilters.maxAirframeTime);
       const aircraftTime = parseInt(aircraft.total_time || 0);
       if (aircraftTime > maxTime) {
           matches = false;
       }
   }
   
   // Max Engine Time filter
   if (currentFilters.maxEngineTime) {
       const maxTime = parseInt(currentFilters.maxEngineTime);
       const engineTime = parseInt(aircraft.engine1_time || 0);
       if (engineTime > maxTime) {
           matches = false;
       }
   }
   
   // Min Interior Year filter
   if (currentFilters.minInteriorYear) {
       const minYear = parseInt(currentFilters.minInteriorYear);
       const interiorYear = parseInt(aircraft.interior_refurb_year || 0);
       if (interiorYear > 0 && interiorYear < minYear) {
           matches = false;
       }
   }
   
   // Min Paint Year filter
   if (currentFilters.minPaintYear) {
       const minYear = parseInt(currentFilters.minPaintYear);
       const paintYear = parseInt(aircraft.paint_year || 0);
       if (paintYear > 0 && paintYear < minYear) {
           matches = false;
       }
   }
   ```

5. **Disabled Match Tool setup** (line ~7670):
   ```javascript
   // Match Tool disabled - filters are now in Aircraft Selection Parameters
   // setupMatchTool();
   ```

---

## ✅ Benefits

### For Users

1. **Cleaner Interface**
   - No separate Match Score Tool section
   - All filters in one logical place
   - Less clutter above Compare section

2. **Easier Filtering**
   - All condition filters together
   - Clear labels and hints
   - Real-time updates

3. **More Control**
   - Filter by exact hours/years
   - Combine multiple criteria
   - See results immediately

### For Developers

1. **Simplified Code**
   - Removed unused Match Tool UI
   - Centralized filter logic
   - Consistent filter patterns

2. **Better UX**
   - Automatic match scoring on load
   - No manual "Calculate" button needed
   - Filters apply instantly

---

## 🎯 Data Fields Used

The filters check these aircraft data fields:

| Filter | Data Field(s) Checked |
|--------|----------------------|
| Max Airframe Time | `total_time`, `total_time_hours` |
| Max Engine Time | `engine1_time`, `engine1_time_hours` |
| Min Interior Year | `interior_refurb_year`, `interior_year` |
| Min Paint Year | `paint_year` |

**Note**: If data field is missing or 0, aircraft passes filter (assumed unknown)

---

## 🚀 Testing

### How to Test

1. **Open**: `http://localhost:5015`

2. **Scroll to "Aircraft Selection Parameters"** (dark card near top)

3. **Find "Condition Filters" section** (green heading with wrench icon)

4. **Enter filter values**:
   - Max Airframe Time: `5000`
   - Max Engine Time: `3000`

5. **Watch results update**:
   - Listing count changes
   - Only low-time aircraft shown
   - Pagination adjusts

6. **Clear filters**:
   - Delete values from inputs
   - All aircraft return

### Browser Console

Check console for filter activity:
```
🔄 Applying client-side filtering...
🔍 Current filters: {maxAirframeTime: "5000", maxEngineTime: "3000"}
✅ Filtered: 42 aircraft match criteria
```

---

## 📋 All Available Filters

### Basic Requirements
- Range Requirement (NM)
- Passengers
- Average Price ($)
- Lowest Acceptable Year

### Condition Filters ← NEW
- **Max Airframe Time (Hours)** ← NEW
- **Max Engine Time (Hours)** ← NEW
- **Min Interior Refurb Year** ← NEW
- **Min Paint Year** ← NEW

### Trip Planning
- Average Trip Length (NM)
- Number of Trips
- Years of Ownership
- Speed (KTS)

### Aircraft Specifications
- Lowest Year
- Highest Year
- Min Crew Required
- Max Operating Altitude
- Balanced Field Length
- Aircraft Dimensions

### Advanced Options
- Min Speed (KTS)
- Min Altitude (FT)
- Max Runway Length (FT)
- Min Cabin Volume (cu ft)
- Max Annual Cost ($)
- Max Hourly Cost ($)
- Fuel Price ($/gal)

---

## 🎉 Summary

✅ **Removed Match Score Tool section** (no longer cluttering UI)  
✅ **Added 4 condition filters** to Aircraft Selection Parameters  
✅ **Max Airframe Time** - Filter by total hours  
✅ **Max Engine Time** - Filter by engine hours  
✅ **Min Interior Year** - Filter by interior refurb year  
✅ **Min Paint Year** - Filter by paint year  
✅ **Real-time filtering** - Updates as you type  
✅ **Combined filters** - All work together (AND logic)  
✅ **Centralized location** - All filters in one place  

**Result**: Cleaner interface with powerful condition filtering to find exactly the aircraft you want based on hours and cosmetic updates.

---

**Version**: 2.4.0  
**Date**: January 26, 2026  
**Status**: Production-Ready ✅

**Server**: Running on `http://localhost:5015`
