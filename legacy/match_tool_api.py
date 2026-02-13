"""
Match Tool API Endpoints V2
Provides REST API for peer-group match scoring and aircraft ranking
"""

from flask import Blueprint, request, jsonify
from match_scoring_v2 import (
    calculate_match_score_v2,
    rank_aircraft_by_best_match
)
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

match_tool_bp = Blueprint('match_tool', __name__, url_prefix='/api/match-tool')


@match_tool_bp.route('/rank', methods=['POST'])
def rank_aircraft():
    """
    Rank aircraft by Best Match Score (peer-group comparison)
    
    POST /api/match-tool/rank
    Body: {
        "aircraft": [...],  # List of aircraft to rank
        "weights": {
            "performance": 0.25,
            "condition": 0.25,
            "cosmetic": 0.15,
            "avionics": 0.15,
            "value": 0.20
        }
    }
    
    Returns: {
        "ranked_aircraft": [...],  # Aircraft sorted by best_match_score
        "count": 42
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'aircraft' not in data:
            return jsonify({'error': 'Missing aircraft data'}), 400
        
        aircraft_list = data['aircraft']
        weights = data.get('weights', {
            'performance': 0.25,
            'condition': 0.25,
            'cosmetic': 0.15,
            'avionics': 0.15,
            'value': 0.20
        })
        
        # Rank aircraft using V2 scoring
        ranked_aircraft = rank_aircraft_by_best_match(aircraft_list, weights)
        
        logger.info(f"Ranked {len(ranked_aircraft)} aircraft by Best Match Score")
        
        return jsonify({
            'ranked_aircraft': ranked_aircraft,
            'count': len(ranked_aircraft),
            'weights_used': weights
        })
    
    except Exception as e:
        logger.error(f"Error ranking aircraft: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@match_tool_bp.route('/score/<int:aircraft_id>', methods=['POST'])
def get_aircraft_score(aircraft_id):
    """
    Get match score for a specific aircraft using V2 peer-group scoring
    
    POST /api/match-tool/score/<aircraft_id>
    Body: {
        "aircraft": {...},  # The aircraft to score
        "all_aircraft": [...],  # Full dataset for peer-group calculation
        "weights": {...}  # Optional custom weights
    }
    
    Returns: {
        "aircraft_id": 42,
        "match_score": 78.5,
        "all_around_score": 82.1,
        "best_match_score": 80.3,
        "categories": {
            "performance": {"score": 85, "stars": 5, "percentile": 85},
            ...
        },
        "top_reasons": [...]
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'aircraft' not in data or 'all_aircraft' not in data:
            return jsonify({'error': 'Missing required data'}), 400
        
        aircraft = data['aircraft']
        all_aircraft = data['all_aircraft']
        weights = data.get('weights')
        
        # Compute match score using V2
        match_data = calculate_match_score_v2(aircraft, all_aircraft, weights)
        
        return jsonify({
            'aircraft_id': aircraft_id,
            **match_data
        })
    
    except Exception as e:
        logger.error(f"Error scoring aircraft {aircraft_id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@match_tool_bp.route('/categories', methods=['GET'])
def get_category_definitions():
    """
    Get definitions of scoring categories and their weights
    
    GET /api/match-tool/categories
    
    Returns: {
        "categories": [
            {
                "name": "Performance",
                "description": "Range, speed, altitude, passengers",
                "default_weight": 0.25,
                "metrics": [...]
            },
            ...
        ]
    }
    """
    categories = [
        {
            'name': 'Performance',
            'key': 'performance',
            'description': 'Aircraft capabilities: range, speed, altitude, passengers, cabin volume',
            'default_weight': 0.25,
            'metrics': [
                {'key': 'range', 'label': 'Range', 'unit': 'nm', 'higher_is_better': True},
                {'key': 'speed', 'label': 'Cruise Speed', 'unit': 'kts', 'higher_is_better': True},
                {'key': 'altitude', 'label': 'Max Altitude', 'unit': 'ft', 'higher_is_better': True},
                {'key': 'passengers', 'label': 'Passenger Capacity', 'unit': 'pax', 'higher_is_better': True},
                {'key': 'cabin_volume', 'label': 'Cabin Volume', 'unit': 'cu ft', 'higher_is_better': True}
            ]
        },
        {
            'name': 'Condition/Time',
            'key': 'condition',
            'description': 'Airframe and engine condition based on hours and TBO',
            'default_weight': 0.25,
            'metrics': [
                {'key': 'total_time', 'label': 'Total Airframe Time', 'unit': 'hrs', 'higher_is_better': False},
                {'key': 'engine1_condition', 'label': 'Engine Condition (% TBO)', 'unit': '%', 'higher_is_better': False},
                {'key': 'year', 'label': 'Year of Manufacture', 'unit': 'year', 'higher_is_better': True}
            ]
        },
        {
            'name': 'Cosmetic',
            'key': 'cosmetic',
            'description': 'Interior and exterior condition',
            'default_weight': 0.15,
            'metrics': [
                {'key': 'interior', 'label': 'Interior Refurb Year', 'unit': 'year', 'higher_is_better': True},
                {'key': 'paint', 'label': 'Paint Year', 'unit': 'year', 'higher_is_better': True}
            ]
        },
        {
            'name': 'Avionics',
            'key': 'avionics',
            'description': 'Avionics package value and capability',
            'default_weight': 0.10,
            'metrics': [
                {'key': 'avionics_value', 'label': 'Avionics Value Estimate', 'unit': '$', 'higher_is_better': True}
            ]
        },
        {
            'name': 'Value',
            'key': 'value',
            'description': 'Overall value proposition and price relative to features',
            'default_weight': 0.25,
            'metrics': [
                {'key': 'all_around_value', 'label': 'All-Around $/$ Score', 'unit': 'score', 'higher_is_better': True},
                {'key': 'price', 'label': 'Purchase Price', 'unit': '$', 'higher_is_better': False}
            ]
        }
    ]
    
    return jsonify({
        'categories': categories,
        'total_weight': 1.0
    })


# Removed filter_aircraft_by_profile - no longer needed with V2 scoring


@match_tool_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'match-tool-api',
        'version': '1.0.0'
    })
