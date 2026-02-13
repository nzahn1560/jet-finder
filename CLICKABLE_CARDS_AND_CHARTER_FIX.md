# Clickable Cards & Cost to Charter Fix

## ✅ Changes Implemented

### 1. Entire Card is Now Clickable

**Before:**
- Small "Full Screen" button next to location info
- Only button was clickable
- Not intuitive that you could see more details

**After:**
- ✅ **Click anywhere on the card** to open full-screen view
- ✅ Removed "Full Screen" button (no longer needed)
- ✅ Added `cursor: pointer` to indicate clickability
- ✅ Hover effect shows card is interactive
- ✅ Compare button (+) and Contact Seller still work independently

**Interaction:**
```
┌────────────────────────────────────┐
│ [Aircraft Image]                   │  ← Click anywhere
│ 2020 Cessna Citation CJ3    [+]   │  ← Except + button
│ Location · Engine Type             │  ← Click here too
│ ────────────────────────────────   │
│ $5,000,000                         │  ← Click here too
│ 85% ALL-AROUND RANK                │  ← Click here too
│ Range: 2000nm  Speed: 450kts       │  ← Click here too
│ ────────────────────────────────   │
│ [Contact Seller]                   │  ← Except this button
└────────────────────────────────────┘

All areas open full-screen EXCEPT:
- Circular + button (adds to compare)
- Contact Seller button (opens email)
```

**Implementation:**
- Added `onclick="viewFullScreen(${aircraft.id})"` to `.aircraft-content` div
- Added `onclick="event.stopPropagation();"` to Compare and Contact buttons
- Added `cursor: pointer` CSS to `.aircraft-content`
- Removed separate "Full Screen" button

---

### 2. Fixed Cost to Charter Calculation

**Problem:**
- Cost to Charter was showing $0 for all aircraft
- Formula had incorrect parameter mapping from Excel

**Root Cause:**
The JavaScript code was using wrong parameters:
```javascript
// BEFORE (WRONG):
const AQ2 = (((BL2 * params.L2) * AD2) * params.H2) + (AE2 * params.H2);

Where:
- L2 = costToCharter input (CIRCULAR REFERENCE!)
- H2 = yearsOfOwnership (WRONG - not charter trips!)
```

**Excel Formula Provided:**
```excel
=(((BL39*'User Inputs'!$L$2)*AD39)*'User Inputs'!$H$2)+(AE39*'User Inputs'!$H$2)
```

**Correct Mapping:**
- **BL** (BL39) = `BL2` = hourly variable cost (`AK2 / 450`)
- **L** (User Inputs L$2) = Should be **`R2`** = `charterRatePercentage / 100`
- **AD** (AD39) = `AD2` = total trip time (`AC2 * G2`)
- **H** (User Inputs H$2) = Should be **`T2`** = `charterTrips` (number of charter trips)
- **AE** (AE39) = `AE2` = passenger revenue (`(Q2 * P2) * AD2`)

**Fixed Formula:**
```javascript
// AFTER (CORRECT):
const AQ2 = (((BL2 * params.R2) * AD2) * params.T2) + (AE2 * params.T2);

Where:
- R2 = charterRatePercentage (correct!)
- T2 = charterTrips (correct!)
```

**Formula Breakdown:**
```
Cost to Charter = 
  (Hourly Variable Cost × Charter Rate % × Total Trip Time × Charter Trips) 
  + (Passenger Revenue × Charter Trips)

Example:
- Hourly Variable Cost (BL2) = $800
- Charter Rate % (R2) = 50% = 0.5
- Total Trip Time (AD2) = 120 hours/year  
- Charter Trips (T2) = 24 trips
- Passenger Revenue (AE2) = $5,000

Cost to Charter = (($800 × 0.5) × 120 × 24) + ($5,000 × 24)
                = ($400 × 120 × 24) + ($120,000)
                = $1,152,000 + $120,000
                = $1,272,000
```

**Where to Set Charter Values:**
These inputs are in the "Aircraft Selection Parameters" section:
- **Charter Rate Percentage**: `charterRatePercentage` input
- **Charter Trips**: `charterTrips` input (or `number-of-trips` if charter-specific not set)
- **Planned Passengers**: `plannedPax` input
- **Passenger Pay**: `passengerPay` input

---

## 🔧 Technical Details

### Files Modified

**`legacy/templates/index.html`**

#### Change 1: Made Card Clickable (lines ~6000-6020)

**Before:**
```html
<div class="aircraft-content" style="padding: 20px;">
    <div style="display: flex;">
        <h5>${listingTitle}</h5>
        <button class="add-to-compare-btn">...</button>
    </div>
    <div class="text-muted">
        Location · Engine
        <button onclick="viewFullScreen(...)">Full Screen</button>
    </div>
```

**After:**
```html
<div class="aircraft-content" style="padding: 20px; cursor: pointer;" 
     onclick="viewFullScreen(${aircraft.id})">
    <div style="display: flex;">
        <h5>${listingTitle}</h5>
        <button class="add-to-compare-btn" 
                onclick="event.stopPropagation();">...</button>
    </div>
    <div class="text-muted">
        Location · Engine
        <!-- Full Screen button removed -->
    </div>
```

#### Change 2: Fixed Cost to Charter Formula (line ~6686)

**Before:**
```javascript
const AQ2 = (((BL2 * params.L2) * AD2) * params.H2) + (AE2 * params.H2);
```

**After:**
```javascript
// Fixed Cost to Charter formula: uses charterRatePercentage (R2) and charterTrips (T2)
const AQ2 = (((BL2 * params.R2) * AD2) * params.T2) + (AE2 * params.T2);
```

#### Change 3: Prevent Button Click Propagation (line ~6120)

**Contact Seller Button:**
```html
<a href="mailto:..." 
   onclick="event.stopPropagation();">
    Contact Seller
</a>
```

#### Change 4: Added CSS for Clickable Cards (lines ~765-862)

```css
.aircraft-card {
    transition: all 0.3s ease;
}

.aircraft-card:hover {
    transform: translateY(-8px);
    box-shadow: 0 16px 48px rgba(240, 85, 69, 0.3);
    border-color: #F05545;
}

.aircraft-content {
    cursor: pointer;
    transition: background 0.2s ease;
}
```

---

## 🎯 User Experience

### Clicking on Cards

**What happens when you click:**
1. **Anywhere on card** → Opens full-screen detailed view
2. **Circular + button** → Adds to/removes from compare (doesn't open full-screen)
3. **Contact Seller** → Opens email client (doesn't open full-screen)
4. **ESC key** → Closes full-screen view

**Visual Feedback:**
- Cursor changes to pointer when hovering over card
- Card lifts up on hover (translateY animation)
- Card shadow expands on hover
- Border color changes to brand orange on hover

### Cost to Charter Display

**Where it appears:**
1. **Listing cards** (in specs grid): "Cost to Charter: $1,272,000"
2. **Full-screen modal** (in Cost Analysis section): Shows cost prominently
3. **Compare section** (Column AQ): Compares charter costs across aircraft

**When it calculates:**
- Automatically when page loads
- Updates when user changes:
  - Charter Rate Percentage
  - Number of Charter Trips
  - Planned Passengers
  - Passenger Pay
  - Other trip/cost inputs

**If showing $0:**
- Check that charter inputs are set (charterRatePercentage, charterTrips > 0)
- Check that aircraft has valid hourly variable cost (total_variable_cost > 0)
- Check browser console for calculation errors

---

## 📊 Parameter Reference

### Charter Calculation Inputs

| Excel Column | JavaScript Param | User Input Field | Description |
|--------------|------------------|------------------|-------------|
| BL39 | `BL2` | (calculated) | Hourly variable cost ÷ 450 |
| User Inputs L$2 | `R2` | `charterRatePercentage` | Charter rate as % (e.g., 50%) |
| AD39 | `AD2` | (calculated) | Total trip time per year (hours) |
| User Inputs H$2 | `T2` | `charterTrips` | Number of charter trips per year |
| AE39 | `AE2` | (calculated) | Passenger revenue (passengerPay × plannedPax × tripTime) |

### How to Set Charter Inputs

**Location**: Aircraft Selection Parameters card

1. **Charter Rate Percentage**:
   - Field ID: `charterRatePercentage`
   - Default: 50%
   - Description: What % of charter market rate you'll charge

2. **Charter Trips**:
   - Field ID: `charterTrips`
   - Default: 0
   - Description: How many charter flights per year

3. **Planned Passengers**:
   - Field ID: `plannedPax`
   - Default: 0
   - Description: Average passengers per charter flight

4. **Passenger Pay**:
   - Field ID: `passengerPay`
   - Default: $0
   - Description: Revenue per passenger per trip

---

## ✅ Testing

### Test Clickable Cards

1. **Open**: `http://localhost:5015`
2. **Hover** over any aircraft card
   - Cursor should change to pointer
   - Card should lift up
   - Border should glow orange
3. **Click** anywhere on card (except buttons)
   - Full-screen modal should open
4. **Click** circular + button
   - Should add to compare (NOT open full-screen)
5. **Click** Contact Seller
   - Should open email (NOT open full-screen)

### Test Cost to Charter

1. **Set charter inputs** (Aircraft Selection Parameters):
   - Charter Rate Percentage: `50`
   - Number of Charter Trips: `24`
   - Planned Passengers: `4`
   - Passenger Pay: `500`

2. **Check listing cards**:
   - Should see "Cost to Charter: $XXX,XXX" (not $0)
   - Values should vary by aircraft

3. **Open full-screen view**:
   - Should see Cost to Charter in Cost Analysis section
   - Should match value on listing card

4. **Compare aircraft**:
   - Add 2-3 aircraft to compare
   - Select "Column AQ - Cost to Charter" from dropdown
   - Should see chart with different values (not all $0)

### Verify Formula

**Expected Behavior:**
- Aircraft with higher variable costs → higher charter cost
- More charter trips → proportionally higher cost
- More passengers + higher passenger pay → higher revenue (higher total)
- Setting charterTrips to 0 → Cost to Charter should be $0

---

## 🚀 Summary

### What Changed ✅

1. ✅ **Entire card is clickable** (opens full-screen view)
2. ✅ **Removed "Full Screen" button** (no longer needed)
3. ✅ **Fixed Cost to Charter calculation** (was $0, now accurate)
4. ✅ **Formula uses correct parameters** (charterRatePercentage, charterTrips)
5. ✅ **Compare and Contact buttons don't propagate clicks** (work independently)
6. ✅ **Added cursor pointer** to indicate clickability
7. ✅ **Hover effects** show card is interactive

### User Benefits 🎉

1. **More intuitive** - Click anywhere to see details
2. **Better UX** - No hunting for small button
3. **Accurate costs** - Charter costs now calculate correctly
4. **Cleaner design** - One less button cluttering the card
5. **Professional feel** - Smooth interactions with proper feedback

---

**Version**: 2.6.0  
**Date**: February 1, 2026  
**Status**: Production-Ready ✅

**Server**: Running on `http://localhost:5015`

**Test it now** - Click on any aircraft card to see the full-screen view! 🚀
