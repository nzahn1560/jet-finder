from typing import Dict, List, Any, Tuple


def map_category_to_charter_type(category: str) -> str:
    key = (category or '').lower().replace(' ', '_')
    if key in ['turboprop']:
        return 'turboprop'
    if key in ['light_jet', 'lightjet', 'light']:
        return 'light_jet'
    if key in ['midsize_jet', 'midsize', 'medium_jet']:
        return 'midsize_jet'
    if key in ['super_midsize_jet', 'super_midsize']:
        return 'super_midsize_jet'
    if key in ['heavy_jet', 'heavy']:
        return 'heavy_jet'
    if key in ['ultra_long_range', 'ultra_long_range_jet', 'ultra_long']:
        return 'ultra_long_range'
    return 'light_jet'


HOURLY_RATES: Dict[str, int] = {
    'turboprop': 2200,
    'light_jet': 3200,
    'midsize_jet': 4500,
    'super_midsize_jet': 5800,
    'heavy_jet': 8500,
    'ultra_long_range': 12000,
}


def estimate_charter(distance_nm: float, aircraft_type_key: str) -> Dict[str, Any]:
    flight_hours = distance_nm / 450.0
    hourly_rate = HOURLY_RATES.get(aircraft_type_key, HOURLY_RATES['light_jet'])
    base_total = flight_hours * hourly_rate
    commission_percent = 10
    commission_amount = base_total * (commission_percent / 100.0)
    total_with_commission = base_total + commission_amount
    return {
        'distance_nm': int(round(distance_nm)),
        'flight_hours': round(flight_hours, 1),
        'hourly_rate': hourly_rate,
        'base_total': int(round(base_total)),
        'commission_percent': commission_percent,
        'commission_amount': int(round(commission_amount)),
        'total_with_commission': int(round(total_with_commission)),
    }


def recommend_for_route(
    aircraft_data: List[Dict[str, Any]],
    dep_code: str,
    arr_code: str,
    passengers: int,
    categorize_fn,
    distance_fn,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    # Compute distance
    distance = distance_fn(dep_code, arr_code)
    required_range = int(distance * 1.2)

    # Filter aircraft
    suitable: List[Dict[str, Any]] = []
    for ac in aircraft_data:
        if ac.get('passengers', 0) < passengers:
            continue
        if ac.get('range', 0) < required_range:
            continue
        suitable.append(ac)

    suitable.sort(key=lambda ac: (ac.get('display_score', 50), ac.get('price', 0) or 0))
    top = suitable[:12]

    recommendations: List[Dict[str, Any]] = []
    for ac in top:
        category = categorize_fn(ac)
        type_key = map_category_to_charter_type(category)
        estimates = estimate_charter(distance, type_key)
        recommendations.append({
            'id': ac.get('id'),
            'manufacturer': ac.get('manufacturer'),
            'model': ac.get('model') or ac.get('aircraft_name'),
            'year': ac.get('year'),
            'passenger_capacity': ac.get('passengers'),
            'range_nm': ac.get('range'),
            'cruise_speed': ac.get('speed'),
            'category': category,
            'charter_type': type_key,
            'estimates': estimates,
        })

    meta = {
        'distance_nm': int(distance),
        'required_range_nm': required_range,
        'commission_policy': {'percent': 10, 'applies_to': 'total charter price'},
    }

    return recommendations, meta


