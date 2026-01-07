import requests
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AvinodeIntegration:
    """
    Avinode API integration for charter listings and booking
    """
    
    def __init__(self):
        self.api_key = os.environ.get('AVINODE_API_KEY')
        self.api_secret = os.environ.get('AVINODE_API_SECRET')
        self.base_url = "https://api.avinode.com"
        self.session = requests.Session()
        
        if self.api_key and self.api_secret:
            self.session.headers.update({
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            })
    
    def search_charter_aircraft(self, 
                               departure_airport: str,
                               arrival_airport: str,
                               departure_date: str,
                               passengers: int,
                               budget_range: Optional[str] = None) -> List[Dict]:
        """
        Search for available charter aircraft based on criteria
        """
        try:
            # Parse departure date
            dep_date = datetime.strptime(departure_date, '%Y-%m-%d')
            
            # Calculate flight distance (simplified)
            distance = self._calculate_distance(departure_airport, arrival_airport)
            
            # Estimate flight duration
            flight_hours = self._estimate_flight_hours(distance)
            
            # Search parameters
            search_params = {
                'departure_airport': departure_airport,
                'arrival_airport': arrival_airport,
                'departure_date': departure_date,
                'passengers': passengers,
                'flight_hours': flight_hours,
                'distance_nm': distance
            }
            
            # If we have real Avinode API credentials, make actual API call
            if self.api_key and self.api_secret:
                return self._real_avinode_search(search_params)
            else:
                # Return mock data for development
                return self._mock_avinode_search(search_params)
                
        except Exception as e:
            logger.error(f"Error searching charter aircraft: {e}")
            return []
    
    def get_aircraft_details(self, aircraft_id: str) -> Optional[Dict]:
        """
        Get detailed information about a specific aircraft
        """
        try:
            if self.api_key and self.api_secret:
                response = self.session.get(f"{self.base_url}/aircraft/{aircraft_id}")
                if response.status_code == 200:
                    return response.json()
            
            # Return mock data for development
            return self._mock_aircraft_details(aircraft_id)
            
        except Exception as e:
            logger.error(f"Error getting aircraft details: {e}")
            return None
    
    def create_charter_quote(self, 
                           aircraft_id: str,
                           departure_airport: str,
                           arrival_airport: str,
                           departure_date: str,
                           passengers: int,
                           customer_info: Dict) -> Optional[Dict]:
        """
        Create a charter quote/booking request
        """
        try:
            quote_data = {
                'aircraft_id': aircraft_id,
                'departure_airport': departure_airport,
                'arrival_airport': arrival_airport,
                'departure_date': departure_date,
                'passengers': passengers,
                'customer_info': customer_info,
                'quote_id': f"QT{datetime.now().strftime('%Y%m%d%H%M%S')}",
                'status': 'pending',
                'created_at': datetime.now().isoformat()
            }
            
            if self.api_key and self.api_secret:
                response = self.session.post(f"{self.base_url}/quotes", json=quote_data)
                if response.status_code == 201:
                    return response.json()
            
            # Return mock quote for development
            return self._mock_charter_quote(quote_data)
            
        except Exception as e:
            logger.error(f"Error creating charter quote: {e}")
            return None
    
    def get_quote_status(self, quote_id: str) -> Optional[Dict]:
        """
        Get the status of a charter quote
        """
        try:
            if self.api_key and self.api_secret:
                response = self.session.get(f"{self.base_url}/quotes/{quote_id}")
                if response.status_code == 200:
                    return response.json()
            
            # Return mock status for development
            return self._mock_quote_status(quote_id)
            
        except Exception as e:
            logger.error(f"Error getting quote status: {e}")
            return None
    
    def _calculate_distance(self, dep_airport: str, arr_airport: str) -> float:
        """
        Calculate approximate distance between airports (simplified)
        """
        # Mock distances for common routes
        route_distances = {
            ('LAX', 'JFK'): 2150,
            ('LAX', 'ORD'): 1740,
            ('JFK', 'LAX'): 2150,
            ('ORD', 'LAX'): 1740,
            ('MIA', 'JFK'): 1090,
            ('JFK', 'MIA'): 1090,
            ('SFO', 'JFK'): 2580,
            ('JFK', 'SFO'): 2580,
        }
        
        route = (dep_airport.upper(), arr_airport.upper())
        if route in route_distances:
            return route_distances[route]
        
        # Default distance calculation (very simplified)
        return 1000.0
    
    def _estimate_flight_hours(self, distance_nm: float) -> float:
        """
        Estimate flight hours based on distance
        """
        # Assume average speed of 450 knots
        return distance_nm / 450.0
    
    def _real_avinode_search(self, search_params: Dict) -> List[Dict]:
        """
        Real Avinode API search (placeholder for actual implementation)
        """
        try:
            response = self.session.get(f"{self.base_url}/aircraft/search", params=search_params)
            if response.status_code == 200:
                return response.json().get('aircraft', [])
            return []
        except Exception as e:
            logger.error(f"Real Avinode search error: {e}")
            return []
    
    def _mock_avinode_search(self, search_params: Dict) -> List[Dict]:
        """
        Mock Avinode search results for development
        """
        mock_aircraft = [
            {
                'id': 'AV001',
                'operator_name': 'Elite Aviation Services',
                'aircraft_type': 'Cessna Citation CJ3+',
                'manufacturer': 'Cessna',
                'model': 'Citation CJ3+',
                'year': 2018,
                'registration': 'N123AB',
                'location': search_params['departure_airport'],
                'hourly_rate': 3200,
                'passenger_capacity': 6,
                'range_nm': 2040,
                'cruise_speed': 478,
                'crew_status': 'available',
                'crew_names': ['Capt. John Smith', 'FO Sarah Johnson'],
                'last_updated': '2 min ago',
                'features': ['WiFi', 'Refreshments', 'Leather Seats'],
                'images': ['/static/images/aircraft/cessna_citation.jpg'],
                'availability': True,
                'estimated_total': search_params['flight_hours'] * 3200,
                'operator_rating': 4.8,
                'safety_rating': 4.9,
                'total_flights': 1250
            },
            {
                'id': 'AV002',
                'operator_name': 'Premier Charter Group',
                'aircraft_type': 'Gulfstream G280',
                'manufacturer': 'Gulfstream',
                'model': 'G280',
                'year': 2020,
                'registration': 'N456CD',
                'location': search_params['departure_airport'],
                'hourly_rate': 5800,
                'passenger_capacity': 8,
                'range_nm': 3600,
                'cruise_speed': 528,
                'crew_status': 'available',
                'crew_names': ['Capt. Mike Wilson', 'FO Lisa Chen'],
                'last_updated': '5 min ago',
                'features': ['Full Kitchen', 'WiFi', 'Entertainment System'],
                'images': ['/static/images/aircraft/gulfstream_g280.jpg'],
                'availability': True,
                'estimated_total': search_params['flight_hours'] * 5800,
                'operator_rating': 4.9,
                'safety_rating': 5.0,
                'total_flights': 890
            },
            {
                'id': 'AV003',
                'operator_name': 'Luxury Air Charter',
                'aircraft_type': 'Bombardier Challenger 350',
                'manufacturer': 'Bombardier',
                'model': 'Challenger 350',
                'year': 2019,
                'registration': 'N789EF',
                'location': search_params['departure_airport'],
                'hourly_rate': 4500,
                'passenger_capacity': 9,
                'range_nm': 3200,
                'cruise_speed': 528,
                'crew_status': 'standby',
                'crew_names': ['Capt. Robert Davis', 'FO Amanda Brown'],
                'last_updated': '10 min ago',
                'features': ['Wide Cabin', 'WiFi', 'Catering Available'],
                'images': ['/static/images/aircraft/challenger_350.jpg'],
                'availability': True,
                'estimated_total': search_params['flight_hours'] * 4500,
                'operator_rating': 4.7,
                'safety_rating': 4.8,
                'total_flights': 1100
            },
            {
                'id': 'AV004',
                'operator_name': 'Executive Flight Services',
                'aircraft_type': 'Embraer Legacy 450',
                'manufacturer': 'Embraer',
                'model': 'Legacy 450',
                'year': 2021,
                'registration': 'N012GH',
                'location': search_params['departure_airport'],
                'hourly_rate': 4200,
                'passenger_capacity': 8,
                'range_nm': 2900,
                'cruise_speed': 464,
                'crew_status': 'available',
                'crew_names': ['Capt. Carlos Rodriguez', 'FO Jennifer Taylor'],
                'last_updated': '1 min ago',
                'features': ['Quiet Cabin', 'WiFi', 'Baggage Space'],
                'images': ['/static/images/aircraft/legacy_450.jpg'],
                'availability': True,
                'estimated_total': search_params['flight_hours'] * 4200,
                'operator_rating': 4.6,
                'safety_rating': 4.7,
                'total_flights': 750
            },
            {
                'id': 'AV005',
                'operator_name': 'Corporate Aviation Solutions',
                'aircraft_type': 'Hawker Beechcraft King Air 350i',
                'manufacturer': 'Hawker Beechcraft',
                'model': 'King Air 350i',
                'year': 2017,
                'registration': 'N345IJ',
                'location': search_params['departure_airport'],
                'hourly_rate': 2800,
                'passenger_capacity': 11,
                'range_nm': 1800,
                'cruise_speed': 359,
                'crew_status': 'available',
                'crew_names': ['Capt. Thomas Anderson', 'FO Maria Gonzalez'],
                'last_updated': '7 min ago',
                'features': ['Large Cabin', 'Cargo Space', 'WiFi'],
                'images': ['/static/images/aircraft/king_air_350i.jpg'],
                'availability': True,
                'estimated_total': search_params['flight_hours'] * 2800,
                'operator_rating': 4.5,
                'safety_rating': 4.6,
                'total_flights': 950
            }
        ]
        
        # Filter by passenger capacity
        filtered_aircraft = [
            aircraft for aircraft in mock_aircraft 
            if aircraft['passenger_capacity'] >= search_params['passengers']
        ]
        
        # Add scoring based on Jet Finder logic
        for aircraft in filtered_aircraft:
            aircraft['match_score'] = self._calculate_match_score(aircraft, search_params)
        
        # Sort by match score
        filtered_aircraft.sort(key=lambda x: x['match_score'], reverse=True)
        
        return filtered_aircraft
    
    def _mock_aircraft_details(self, aircraft_id: str) -> Optional[Dict]:
        """
        Mock aircraft details for development
        """
        mock_details = {
            'AV001': {
                'id': 'AV001',
                'operator_name': 'Elite Aviation Services',
                'aircraft_type': 'Cessna Citation CJ3+',
                'manufacturer': 'Cessna',
                'model': 'Citation CJ3+',
                'year': 2018,
                'registration': 'N123AB',
                'serial_number': '525B-1234',
                'total_time': 1245,
                'engine_time': 1245,
                'last_maintenance': '2024-01-15',
                'next_maintenance': '2024-04-15',
                'interior_condition': 'Excellent',
                'exterior_condition': 'Excellent',
                'avionics': 'Garmin G3000',
                'cabin_height': 4.8,
                'cabin_width': 5.1,
                'cabin_length': 15.2,
                'baggage_capacity': 50,
                'fuel_capacity': 5000,
                'certifications': ['Part 135', 'Part 91K'],
                'insurance': 'Fully Insured',
                'crew_qualifications': ['ATP', 'Type Rated'],
                'safety_rating': 4.9,
                'operator_rating': 4.8,
                'total_flights': 1250,
                'images': [
                    '/static/images/aircraft/cessna_citation.jpg',
                    '/static/images/aircraft/cessna_citation_cockpit.jpg',
                    '/static/images/aircraft/cessna_citation_cabin.jpg'
                ]
            }
        }
        
        return mock_details.get(aircraft_id)
    
    def _mock_charter_quote(self, quote_data: Dict) -> Dict:
        """
        Mock charter quote response for development
        """
        quote_data.update({
            'status': 'pending',
            'estimated_response_time': '2-4 hours',
            'terms_conditions': [
                'Payment required within 24 hours of confirmation',
                'Cancellation policy applies',
                'Weather and operational delays may occur',
                'All flights subject to aircraft availability'
            ],
            'included_services': [
                'Professional flight crew',
                'Fuel and landing fees',
                'Basic catering',
                'WiFi (if available)',
                'Ground transportation coordination'
            ],
            'additional_services': [
                'Premium catering',
                'Ground transportation',
                'Hotel bookings',
                'Concierge services'
            ]
        })
        
        return quote_data
    
    def _mock_quote_status(self, quote_id: str) -> Dict:
        """
        Mock quote status for development
        """
        return {
            'quote_id': quote_id,
            'status': 'confirmed',
            'aircraft_confirmed': True,
            'crew_assigned': True,
            'estimated_departure_time': '09:00',
            'estimated_arrival_time': '17:00',
            'total_cost': 25600,
            'payment_status': 'pending',
            'confirmation_number': f'CONF{quote_id}',
            'updated_at': datetime.now().isoformat()
        }
    
    def _calculate_match_score(self, aircraft: Dict, search_params: Dict) -> float:
        """
        Calculate match score based on Jet Finder logic
        """
        score = 0.0
        
        # Passenger capacity match (40% weight)
        passenger_ratio = min(aircraft['passenger_capacity'] / search_params['passengers'], 1.0)
        score += passenger_ratio * 40
        
        # Range capability (30% weight)
        distance = search_params['distance_nm']
        if aircraft['range_nm'] >= distance:
            range_score = min(aircraft['range_nm'] / distance, 2.0)  # Cap at 2x required
            score += (range_score / 2.0) * 30
        
        # Price efficiency (20% weight)
        hourly_cost = aircraft['hourly_rate']
        if hourly_cost <= 3000:
            price_score = 1.0
        elif hourly_cost <= 5000:
            price_score = 0.8
        elif hourly_cost <= 8000:
            price_score = 0.6
        else:
            price_score = 0.4
        score += price_score * 20
        
        # Crew availability (10% weight)
        if aircraft['crew_status'] == 'available':
            score += 10
        elif aircraft['crew_status'] == 'standby':
            score += 7
        else:
            score += 3
        
        return min(score, 100.0)

# Global instance
avinode_client = AvinodeIntegration() 