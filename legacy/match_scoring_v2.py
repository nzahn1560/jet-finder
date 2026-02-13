"""
Match Scoring System V2 - Peer-Group Comparison
Compares listings within similar aircraft peer groups and produces:
- Category scores (1-5 stars): Performance, Condition, Cosmetic, Avionics, Value
- Total Match Score (0-100)
- Best Match Score = avg(Match Score, All-Around/$ Score)
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional

def get_peer_group(aircraft: Dict, all_aircraft: List[Dict]) -> List[Dict]:
    """
    Get peer group for comparison (ONLY same performance profile/model)
    
    Performance profile = exact aircraft model match
    NO fallbacks - if not enough peers, scoring will reflect actual peer count
    
    Args:
        aircraft: Target aircraft
        all_aircraft: All available aircraft
    
    Returns:
        List of aircraft with the EXACT same model (performance profile)
    """
    # Get aircraft model (performance profile identifier)
    model = (aircraft.get('aircraft_name') or aircraft.get('name', '')).strip()
    
    if not model:
        # If no model, can't determine peer group - return just this aircraft
        return [aircraft]
    
    # STRICT: Only exact model matches (same performance profile)
    peer_group = [
        a for a in all_aircraft 
        if (a.get('aircraft_name') or a.get('name', '')).strip() == model
    ]
    
    # Ensure at least the target aircraft is in the group
    if not peer_group:
        peer_group = [aircraft]
    
    return peer_group

def calculate_percentile_rank(value: float, peer_values: List[float], higher_is_better: bool = True) -> float:
    """
    Calculate percentile rank (0-100) within peer group
    
    Args:
        value: Value to rank
        peer_values: All values in peer group
        higher_is_better: If True, higher values get higher percentiles
    
    Returns:
        Percentile (0-100)
    """
    if not peer_values or value is None:
        return 50.0  # Neutral if no data
    
    peer_values = [v for v in peer_values if v is not None and not np.isnan(v)]
    if not peer_values:
        return 50.0
    
    # If only one value (no peers to compare to), return middle score
    if len(peer_values) == 1:
        return 50.0
    
    # Calculate percentile using numpy for accuracy
    peer_values_sorted = sorted(peer_values)
    
    # Find position of value in sorted peer group
    position = np.searchsorted(peer_values_sorted, value, side='right')
    
    # Calculate percentile (0-100)
    percentile = (position / len(peer_values_sorted)) * 100
    
    # Invert for "lower is better" metrics
    if not higher_is_better:
        percentile = 100 - percentile
    
    return float(np.clip(percentile, 0, 100))

def percentile_to_stars(percentile: float) -> int:
    """
    Convert percentile (0-100) to 1-5 star rating
    
    0-20%   → 1 star
    20-40%  → 2 stars
    40-60%  → 3 stars
    60-80%  → 4 stars
    80-100% → 5 stars
    """
    if percentile >= 80:
        return 5
    elif percentile >= 60:
        return 4
    elif percentile >= 40:
        return 3
    elif percentile >= 20:
        return 2
    else:
        return 1

def calculate_performance_score(aircraft: Dict, peer_group: List[Dict]) -> Dict[str, float]:
    """
    Calculate Performance category score
    Metrics: range, speed, altitude, passengers, cabin_volume
    Higher is better
    """
    metrics = ['range', 'speed', 'max_altitude', 'passengers', 'cabin_volume']
    percentiles = []
    
    for metric in metrics:
        value = float(aircraft.get(metric, 0) or 0)
        peer_values = [float(a.get(metric, 0) or 0) for a in peer_group]
        
        if value > 0:
            percentile = calculate_percentile_rank(value, peer_values, higher_is_better=True)
            percentiles.append(percentile)
    
    avg_percentile = np.mean(percentiles) if percentiles else 50.0
    
    return {
        'percentile': avg_percentile,
        'score_0_100': avg_percentile,
        'stars': percentile_to_stars(avg_percentile)
    }

def calculate_condition_score(aircraft: Dict, peer_group: List[Dict]) -> Dict[str, float]:
    """
    Calculate Condition category score
    Metrics: total_time (lower better), engine times vs TBO (lower better), year (higher better)
    """
    percentiles = []
    
    # Total time (lower is better)
    total_time = float(aircraft.get('total_time_hours') or aircraft.get('total_time', 0) or 0)
    if total_time > 0:
        peer_times = [float(a.get('total_time_hours') or a.get('total_time', 0) or 0) for a in peer_group]
        peer_times = [t for t in peer_times if t > 0]
        if peer_times:
            percentile = calculate_percentile_rank(total_time, peer_times, higher_is_better=False)
            percentiles.append(percentile)
    
    # Engine 1 time vs TBO (lower % used is better)
    engine1_time = float(aircraft.get('engine1_time_hours') or aircraft.get('engine1_time', 0) or 0)
    engine1_tbo = float(aircraft.get('engine1_tbo_hours') or aircraft.get('engine1_tbo', 3500) or 3500)
    if engine1_time > 0 and engine1_tbo > 0:
        engine_pct_used = (engine1_time / engine1_tbo) * 100
        peer_pcts = []
        for a in peer_group:
            e_time = float(a.get('engine1_time_hours') or a.get('engine1_time', 0) or 0)
            e_tbo = float(a.get('engine1_tbo_hours') or a.get('engine1_tbo', 3500) or 3500)
            if e_time > 0 and e_tbo > 0:
                peer_pcts.append((e_time / e_tbo) * 100)
        if peer_pcts:
            percentile = calculate_percentile_rank(engine_pct_used, peer_pcts, higher_is_better=False)
            percentiles.append(percentile)
    
    # Year (newer is better)
    year = int(aircraft.get('year', 0) or 0)
    if year > 0:
        peer_years = [int(a.get('year', 0) or 0) for a in peer_group]
        peer_years = [y for y in peer_years if y > 0]
        if peer_years:
            percentile = calculate_percentile_rank(year, peer_years, higher_is_better=True)
            percentiles.append(percentile)
    
    avg_percentile = np.mean(percentiles) if percentiles else 50.0
    
    return {
        'percentile': avg_percentile,
        'score_0_100': avg_percentile,
        'stars': percentile_to_stars(avg_percentile)
    }

def calculate_cosmetic_score(aircraft: Dict, peer_group: List[Dict]) -> Dict[str, float]:
    """
    Calculate Cosmetic category score
    Metrics: interior condition, paint condition, interior year, paint year
    Manual scores (1-5) take priority, otherwise use years
    """
    percentiles = []
    
    # Interior score (manual if available)
    interior_manual = aircraft.get('interior_score_manual')
    if interior_manual:
        # Convert 1-5 to percentile
        percentile = ((float(interior_manual) - 1) / 4) * 100
        percentiles.append(percentile)
    else:
        # Use interior year
        interior_year = int(aircraft.get('interior_refurb_year') or aircraft.get('interior_year', 0) or 0)
        if interior_year > 0:
            peer_years = [int(a.get('interior_refurb_year') or a.get('interior_year', 0) or 0) for a in peer_group]
            peer_years = [y for y in peer_years if y > 0]
            if peer_years:
                percentile = calculate_percentile_rank(interior_year, peer_years, higher_is_better=True)
                percentiles.append(percentile)
    
    # Paint score (manual if available)
    paint_manual = aircraft.get('paint_score_manual')
    if paint_manual:
        percentile = ((float(paint_manual) - 1) / 4) * 100
        percentiles.append(percentile)
    else:
        # Use paint year
        paint_year = int(aircraft.get('paint_year', 0) or 0)
        if paint_year > 0:
            peer_years = [int(a.get('paint_year', 0) or 0) for a in peer_group]
            peer_years = [y for y in peer_years if y > 0]
            if peer_years:
                percentile = calculate_percentile_rank(paint_year, peer_years, higher_is_better=True)
                percentiles.append(percentile)
    
    avg_percentile = np.mean(percentiles) if percentiles else 50.0
    
    return {
        'percentile': avg_percentile,
        'score_0_100': avg_percentile,
        'stars': percentile_to_stars(avg_percentile)
    }

def calculate_avionics_score(aircraft: Dict, peer_group: List[Dict]) -> Dict[str, float]:
    """
    Calculate Avionics category score
    Metrics: avionics value estimate (higher is better)
    """
    avionics_value = float(aircraft.get('avionics_value_estimate') or aircraft.get('avionics_value_est', 0) or 0)
    
    if avionics_value > 0:
        peer_values = [float(a.get('avionics_value_estimate') or a.get('avionics_value_est', 0) or 0) for a in peer_group]
        peer_values = [v for v in peer_values if v > 0]
        
        if peer_values:
            percentile = calculate_percentile_rank(avionics_value, peer_values, higher_is_better=True)
        else:
            percentile = 50.0
    else:
        # Default to median if no data
        percentile = 50.0
    
    return {
        'percentile': percentile,
        'score_0_100': percentile,
        'stars': percentile_to_stars(percentile)
    }

def calculate_value_score(aircraft: Dict, peer_group: List[Dict]) -> Dict[str, float]:
    """
    Calculate Value category score
    Better value = higher score
    Formula: performance_index / price (normalized)
    """
    price = float(aircraft.get('listing_price') or aircraft.get('price', 0) or 0)
    
    if price <= 0:
        return {'percentile': 50.0, 'score_0_100': 50.0, 'stars': 3}
    
    # Calculate performance index (simple: range + speed)
    range_nm = float(aircraft.get('range', 0) or 0)
    speed_kts = float(aircraft.get('speed', 0) or 0)
    perf_index = range_nm + speed_kts
    
    if perf_index > 0:
        value_index = perf_index / price * 1000000  # Scale for readability
    else:
        value_index = 0
    
    # Compare within peer group
    peer_value_indices = []
    for a in peer_group:
        p_price = float(a.get('listing_price') or a.get('price', 0) or 0)
        p_range = float(a.get('range', 0) or 0)
        p_speed = float(a.get('speed', 0) or 0)
        p_perf = p_range + p_speed
        
        if p_price > 0 and p_perf > 0:
            peer_value_indices.append(p_perf / p_price * 1000000)
    
    if peer_value_indices:
        percentile = calculate_percentile_rank(value_index, peer_value_indices, higher_is_better=True)
    else:
        percentile = 50.0
    
    return {
        'percentile': percentile,
        'score_0_100': percentile,
        'stars': percentile_to_stars(percentile)
    }

def calculate_match_score_v2(aircraft: Dict, all_aircraft: List[Dict], weights: Optional[Dict] = None) -> Dict:
    """
    Calculate complete match score with STRICT peer-group comparison
    Compares ONLY within same performance profile (exact model match)
    
    Args:
        aircraft: Aircraft to score
        all_aircraft: All available aircraft
        weights: Optional category weights (default: balanced)
    
    Returns:
        Dict with scores, categories, and best_match_score
    """
    # Default weights
    if not weights:
        weights = {
            'performance': 0.25,
            'condition': 0.25,
            'cosmetic': 0.15,
            'avionics': 0.15,
            'value': 0.20
        }
    
    # Get peer group (ONLY same performance profile/model)
    peer_group = get_peer_group(aircraft, all_aircraft)
    
    # Calculate category scores (compared only to same model)
    categories = {
        'performance': calculate_performance_score(aircraft, peer_group),
        'condition': calculate_condition_score(aircraft, peer_group),
        'cosmetic': calculate_cosmetic_score(aircraft, peer_group),
        'avionics': calculate_avionics_score(aircraft, peer_group),
        'value': calculate_value_score(aircraft, peer_group)
    }
    
    # Calculate weighted match score (0-100)
    match_score = sum(
        categories[cat]['score_0_100'] * weights[cat]
        for cat in categories.keys()
    )
    
    # Get existing All-Around/$ Score (if available)
    all_around_score = float(aircraft.get('normalized_performance_dollar', 0) or 0)
    if all_around_score > 0:
        # Normalize to 0-100 if needed
        if all_around_score > 100:
            all_around_score = min(100, all_around_score / 10)  # Rough scaling
    else:
        all_around_score = 50.0  # Default if not available
    
    # Calculate Best Match Score = avg(match_score, all_around_score)
    best_match_score = (match_score + all_around_score) / 2
    
    # Generate top reasons
    top_reasons = generate_top_reasons_v2(categories, aircraft, peer_group)
    
    # Get model name for display
    model_name = (aircraft.get('aircraft_name') or aircraft.get('name', 'Unknown')).strip()
    
    return {
        'match_score': round(match_score, 1),
        'all_around_score': round(all_around_score, 1),
        'best_match_score': round(best_match_score, 1),
        'categories': {
            cat: {
                'score': round(data['score_0_100'], 1),
                'stars': data['stars'],
                'percentile': round(data['percentile'], 1)
            }
            for cat, data in categories.items()
        },
        'top_reasons': top_reasons,
        'peer_group_size': len(peer_group),
        'peer_group_model': model_name,
        'comparison_note': f"Compared to {len(peer_group)} other {model_name} aircraft" if len(peer_group) > 1 else f"Only {model_name} in dataset"
    }

def generate_top_reasons_v2(categories: Dict, aircraft: Dict, peer_group: List[Dict]) -> List[str]:
    """
    Generate human-readable top reasons based on category scores within peer group
    """
    reasons = []
    model_name = (aircraft.get('aircraft_name') or aircraft.get('name', 'aircraft')).strip()
    peer_count = len(peer_group)
    
    # Sort categories by stars
    sorted_cats = sorted(categories.items(), key=lambda x: x[1]['stars'], reverse=True)
    
    # Add peer group context
    if peer_count > 1:
        reasons.append(f"Compared to {peer_count} other {model_name}")
    
    # Top 2-3 categories
    for cat_name, cat_data in sorted_cats[:3]:
        stars = cat_data['stars']
        percentile = cat_data.get('percentile', 50)
        
        if stars >= 4:
            if cat_name == 'performance':
                reasons.append(f"Top {int(100-percentile)}% for performance in model")
            elif cat_name == 'condition':
                reasons.append(f"Better condition than {int(percentile)}% of peers")
            elif cat_name == 'cosmetic':
                reasons.append(f"Superior interior/exterior vs peers")
            elif cat_name == 'avionics':
                reasons.append(f"Above-average avionics for {model_name}")
            elif cat_name == 'value':
                reasons.append(f"Best value in {model_name} category")
        elif stars <= 2:
            # Mention low scores too for transparency
            if cat_name == 'condition':
                reasons.append(f"Higher hours than average for model")
            elif cat_name == 'value':
                reasons.append(f"Premium price point for {model_name}")
    
    # Add specific highlights
    year = int(aircraft.get('year', 0) or 0)
    if year >= 2015:
        reasons.append(f"Newer {model_name} ({year})")
    
    return reasons[:4]  # Limit to 4 reasons

def rank_aircraft_by_best_match(aircraft_list: List[Dict], weights: Optional[Dict] = None) -> List[Dict]:
    """
    Rank all aircraft by Best Match Score
    
    Args:
        aircraft_list: List of aircraft to rank
        weights: Optional category weights
    
    Returns:
        Sorted list with match scores attached
    """
    # Calculate scores for all aircraft
    for aircraft in aircraft_list:
        scores = calculate_match_score_v2(aircraft, aircraft_list, weights)
        aircraft['match_score'] = scores['match_score']
        aircraft['all_around_score'] = scores['all_around_score']
        aircraft['best_match_score'] = scores['best_match_score']
        aircraft['match_categories'] = scores['categories']
        aircraft['match_reasons'] = scores['top_reasons']
        aircraft['peer_group_size'] = scores['peer_group_size']
    
    # Sort by best_match_score DESC
    aircraft_list.sort(key=lambda x: x.get('best_match_score', 0), reverse=True)
    
    return aircraft_list
