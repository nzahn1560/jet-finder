"""
Match Tool Scoring Engine
Ranks aircraft listings by computing percentile-based match scores across multiple categories.
"""

import numpy as np
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class BuyerProfile:
    """Buyer's search criteria and weights"""
    performance_profile_id: int
    min_range: Optional[int] = None
    min_speed: Optional[int] = None
    max_price: Optional[float] = None
    min_passengers: Optional[int] = None
    max_total_time: Optional[int] = None
    max_engine_time: Optional[int] = None
    min_interior_year: Optional[int] = None
    min_paint_year: Optional[int] = None
    min_avionics_value: Optional[float] = None
    
    # Category weights (should sum to 1.0)
    weight_performance: float = 0.25
    weight_condition: float = 0.25
    weight_cosmetic: float = 0.15
    weight_avionics: float = 0.10
    weight_value: float = 0.25


class MatchScorer:
    """Compute match scores for aircraft listings"""
    
    def __init__(self):
        self.percentile_cache = {}
    
    def calculate_percentile_score(
        self, 
        value: float, 
        all_values: List[float], 
        higher_is_better: bool = True
    ) -> float:
        """
        Convert a value to 0-100 percentile score relative to the dataset.
        
        Args:
            value: The value to score
            all_values: All values in the filtered dataset
            higher_is_better: If True, higher values get higher scores (e.g., range)
                             If False, lower values get higher scores (e.g., price, hours)
        
        Returns:
            Score from 0-100 where 100 is best
        """
        if not all_values or len(all_values) == 1:
            return 50.0  # Default middle score
        
        # Remove None/NaN values
        clean_values = [v for v in all_values if v is not None and not np.isnan(v)]
        if not clean_values:
            return 50.0
        
        # Calculate percentile (0-100)
        percentile = np.percentile(clean_values, [0, 25, 50, 75, 100])
        
        if value < percentile[0]:
            rank = 0
        elif value > percentile[4]:
            rank = 100
        else:
            # Linear interpolation between percentiles
            for i in range(4):
                if percentile[i] <= value <= percentile[i + 1]:
                    range_size = percentile[i + 1] - percentile[i]
                    if range_size == 0:
                        rank = i * 25
                    else:
                        rank = i * 25 + ((value - percentile[i]) / range_size) * 25
                    break
        
        # Invert if lower is better
        if not higher_is_better:
            rank = 100 - rank
        
        return max(0, min(100, rank))
    
    def score_performance_category(
        self, 
        aircraft: Dict[str, Any], 
        all_aircraft: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Score performance metrics: range, speed, ceiling, passengers, etc."""
        scores = {}
        
        # Range (higher is better)
        if 'range' in aircraft and aircraft['range']:
            all_ranges = [a.get('range', 0) for a in all_aircraft if a.get('range')]
            scores['range'] = self.calculate_percentile_score(
                aircraft['range'], all_ranges, higher_is_better=True
            )
        
        # Speed (higher is better)
        if 'speed' in aircraft and aircraft['speed']:
            all_speeds = [a.get('speed', 0) for a in all_aircraft if a.get('speed')]
            scores['speed'] = self.calculate_percentile_score(
                aircraft['speed'], all_speeds, higher_is_better=True
            )
        
        # Max Altitude (higher is better)
        if 'max_altitude' in aircraft and aircraft['max_altitude']:
            all_altitudes = [a.get('max_altitude', 0) for a in all_aircraft if a.get('max_altitude')]
            scores['altitude'] = self.calculate_percentile_score(
                aircraft['max_altitude'], all_altitudes, higher_is_better=True
            )
        
        # Passengers (higher is better)
        if 'passengers' in aircraft and aircraft['passengers']:
            all_pax = [a.get('passengers', 0) for a in all_aircraft if a.get('passengers')]
            scores['passengers'] = self.calculate_percentile_score(
                aircraft['passengers'], all_pax, higher_is_better=True
            )
        
        # Cabin Volume (higher is better)
        if 'cabin_volume' in aircraft and aircraft['cabin_volume']:
            all_cabin = [a.get('cabin_volume', 0) for a in all_aircraft if a.get('cabin_volume')]
            scores['cabin_volume'] = self.calculate_percentile_score(
                aircraft['cabin_volume'], all_cabin, higher_is_better=True
            )
        
        # Average performance score
        category_score = np.mean(list(scores.values())) if scores else 50.0
        
        return {
            'category_score': category_score,
            'metrics': scores
        }
    
    def score_condition_category(
        self, 
        aircraft: Dict[str, Any], 
        all_aircraft: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Score condition metrics: total time, engine time relative to TBO"""
        scores = {}
        
        # Total Time (lower is better)
        if 'total_time' in aircraft and aircraft.get('total_time') is not None:
            all_times = [a.get('total_time', 0) for a in all_aircraft if a.get('total_time') is not None]
            scores['total_time'] = self.calculate_percentile_score(
                aircraft['total_time'], all_times, higher_is_better=False
            )
        
        # Engine Time as % of TBO (lower is better)
        if all(['engine1_time' in aircraft, 'engine1_tbo' in aircraft, 
                aircraft.get('engine1_time') is not None, aircraft.get('engine1_tbo')]):
            tbo = aircraft['engine1_tbo']
            if tbo > 0:
                engine_pct = (aircraft['engine1_time'] / tbo) * 100
                all_engine_pcts = []
                for a in all_aircraft:
                    if (a.get('engine1_time') is not None and a.get('engine1_tbo') and 
                        a['engine1_tbo'] > 0):
                        all_engine_pcts.append((a['engine1_time'] / a['engine1_tbo']) * 100)
                
                if all_engine_pcts:
                    scores['engine1_condition'] = self.calculate_percentile_score(
                        engine_pct, all_engine_pcts, higher_is_better=False
                    )
        
        # Year (newer is better)
        if 'year' in aircraft and aircraft['year']:
            all_years = [a.get('year', 0) for a in all_aircraft if a.get('year')]
            scores['year'] = self.calculate_percentile_score(
                aircraft['year'], all_years, higher_is_better=True
            )
        
        category_score = np.mean(list(scores.values())) if scores else 50.0
        
        return {
            'category_score': category_score,
            'metrics': scores
        }
    
    def score_cosmetic_category(
        self, 
        aircraft: Dict[str, Any], 
        all_aircraft: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Score cosmetic metrics: interior year, paint year"""
        scores = {}
        
        # Interior Year (newer is better)
        if 'interior_year' in aircraft and aircraft.get('interior_year'):
            all_interior = [a.get('interior_year', 0) for a in all_aircraft if a.get('interior_year')]
            scores['interior'] = self.calculate_percentile_score(
                aircraft['interior_year'], all_interior, higher_is_better=True
            )
        
        # Paint Year (newer is better)
        if 'paint_year' in aircraft and aircraft.get('paint_year'):
            all_paint = [a.get('paint_year', 0) for a in all_aircraft if a.get('paint_year')]
            scores['paint'] = self.calculate_percentile_score(
                aircraft['paint_year'], all_paint, higher_is_better=True
            )
        
        category_score = np.mean(list(scores.values())) if scores else 50.0
        
        return {
            'category_score': category_score,
            'metrics': scores
        }
    
    def score_avionics_category(
        self, 
        aircraft: Dict[str, Any], 
        all_aircraft: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Score avionics: estimated value of avionics package"""
        scores = {}
        
        # Avionics Value Estimate (higher is better)
        if 'avionics_value_estimate' in aircraft and aircraft.get('avionics_value_estimate'):
            all_avionics = [a.get('avionics_value_estimate', 0) for a in all_aircraft 
                           if a.get('avionics_value_estimate')]
            scores['avionics_value'] = self.calculate_percentile_score(
                aircraft['avionics_value_estimate'], all_avionics, higher_is_better=True
            )
        
        category_score = np.mean(list(scores.values())) if scores else 50.0
        
        return {
            'category_score': category_score,
            'metrics': scores
        }
    
    def score_value_category(
        self, 
        aircraft: Dict[str, Any], 
        all_aircraft: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Score overall value: price relative to performance ($/$ scores)"""
        scores = {}
        
        # Use the all-around/$ score if available
        if 'best_all_around_dollar' in aircraft and aircraft.get('best_all_around_dollar'):
            all_values = [a.get('best_all_around_dollar', 0) for a in all_aircraft 
                         if a.get('best_all_around_dollar')]
            scores['all_around_value'] = self.calculate_percentile_score(
                aircraft['best_all_around_dollar'], all_values, higher_is_better=True
            )
        
        # Price (lower is better, but relative to features)
        if 'price' in aircraft and aircraft.get('price'):
            all_prices = [a.get('price', 0) for a in all_aircraft if a.get('price')]
            scores['price'] = self.calculate_percentile_score(
                aircraft['price'], all_prices, higher_is_better=False
            )
        
        category_score = np.mean(list(scores.values())) if scores else 50.0
        
        return {
            'category_score': category_score,
            'metrics': scores
        }
    
    def compute_match_score(
        self, 
        aircraft: Dict[str, Any], 
        all_aircraft: List[Dict[str, Any]],
        buyer_profile: BuyerProfile
    ) -> Dict[str, Any]:
        """
        Compute comprehensive match score for an aircraft.
        
        Returns:
            Dict with total_score (0-100), category scores, and top reasons
        """
        # Score each category
        performance = self.score_performance_category(aircraft, all_aircraft)
        condition = self.score_condition_category(aircraft, all_aircraft)
        cosmetic = self.score_cosmetic_category(aircraft, all_aircraft)
        avionics = self.score_avionics_category(aircraft, all_aircraft)
        value = self.score_value_category(aircraft, all_aircraft)
        
        # Calculate weighted average
        weighted_score = (
            performance['category_score'] * buyer_profile.weight_performance +
            condition['category_score'] * buyer_profile.weight_condition +
            cosmetic['category_score'] * buyer_profile.weight_cosmetic +
            avionics['category_score'] * buyer_profile.weight_avionics +
            value['category_score'] * buyer_profile.weight_value
        )
        
        # Blend with all-around/$ score (70% weighted categories + 30% all-around value)
        if value['metrics'].get('all_around_value'):
            total_score = weighted_score * 0.7 + value['metrics']['all_around_value'] * 0.3
        else:
            total_score = weighted_score
        
        # Generate top reasons (3-5 strongest categories/metrics)
        all_scores = {
            'Performance': performance['category_score'],
            'Condition': condition['category_score'],
            'Cosmetic': cosmetic['category_score'],
            'Avionics': avionics['category_score'],
            'Value': value['category_score']
        }
        
        # Sort by score and take top 3
        top_categories = sorted(all_scores.items(), key=lambda x: x[1], reverse=True)[:3]
        
        top_reasons = []
        for category, score in top_categories:
            if score >= 70:
                reason_text = f"Excellent {category.lower()} ({score:.0f}/100)"
            elif score >= 50:
                reason_text = f"Good {category.lower()} ({score:.0f}/100)"
            else:
                continue
            top_reasons.append(reason_text)
        
        # Add specific metric highlights
        if performance['metrics'].get('range', 0) >= 80:
            top_reasons.append(f"Exceptional range: {aircraft.get('range', 0):,} nm")
        if condition['metrics'].get('total_time', 100) >= 80:
            top_reasons.append(f"Low airframe time: {aircraft.get('total_time', 0):,} hrs")
        if value['metrics'].get('price', 0) >= 70:
            top_reasons.append("Excellent value for money")
        
        return {
            'total_score': round(total_score, 1),
            'categories': {
                'performance': round(performance['category_score'], 1),
                'condition': round(condition['category_score'], 1),
                'cosmetic': round(cosmetic['category_score'], 1),
                'avionics': round(avionics['category_score'], 1),
                'value': round(value['category_score'], 1)
            },
            'detailed_metrics': {
                'performance': performance['metrics'],
                'condition': condition['metrics'],
                'cosmetic': cosmetic['metrics'],
                'avionics': avionics['metrics'],
                'value': value['metrics']
            },
            'top_reasons': top_reasons[:5]  # Max 5 reasons
        }
    
    def rank_aircraft_by_match(
        self, 
        aircraft_list: List[Dict[str, Any]],
        buyer_profile: BuyerProfile
    ) -> List[Dict[str, Any]]:
        """
        Rank all aircraft by match score and add match data to each.
        
        Returns:
            List of aircraft sorted by match score (highest first)
        """
        # Compute match scores for all aircraft
        scored_aircraft = []
        for aircraft in aircraft_list:
            match_data = self.compute_match_score(aircraft, aircraft_list, buyer_profile)
            aircraft_with_score = {
                **aircraft,
                'match_score': match_data['total_score'],
                'match_categories': match_data['categories'],
                'match_reasons': match_data['top_reasons'],
                'match_details': match_data['detailed_metrics']
            }
            scored_aircraft.append(aircraft_with_score)
        
        # Sort by match score (highest first)
        scored_aircraft.sort(key=lambda x: x['match_score'], reverse=True)
        
        return scored_aircraft
