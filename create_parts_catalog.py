#!/usr/bin/env python3
"""
Aircraft Parts Catalog and Service Provider Matching System
Creates comprehensive parts database for aircraft maintenance and repair
"""

import json
import os
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from datetime import datetime

@dataclass
class AircraftPart:
    part_number: str
    name: str
    category: str
    manufacturer: str
    compatible_aircraft: List[str]
    description: str
    weight: Optional[float] = None
    dimensions: Optional[str] = None
    price_range: Optional[str] = None
    criticality: str = "standard"  # critical, important, standard
    maintenance_interval: Optional[int] = None  # hours
    certification: Optional[str] = None

@dataclass
class ServiceProvider:
    id: str
    name: str
    location: str
    coordinates: Dict[str, float]
    specialties: List[str]
    certifications: List[str]
    years_in_business: int
    average_rating: float
    total_reviews: int
    hourly_rate: Optional[float]
    parts_inventory: List[str]  # part numbers they have in stock
    service_radius: int  # miles
    contact_info: Dict[str, str]

def create_comprehensive_parts_catalog():
    """Create comprehensive parts catalog for major aircraft"""
    
    # Common engine parts
    engine_parts = [
        AircraftPart("ENG001", "Turbine Blade Set", "Engine", "Pratt & Whitney", 
                    ["Citation CJ3+", "Citation Sovereign+"], "High-pressure turbine blades", 
                    price_range="$15,000-$25,000", criticality="critical", maintenance_interval=2000),
        AircraftPart("ENG002", "Fuel Injection Nozzle", "Engine", "Rolls-Royce", 
                    ["Gulfstream G650", "Falcon 2000LXS"], "Primary fuel injection system",
                    price_range="$3,000-$5,000", criticality="critical", maintenance_interval=1500),
        AircraftPart("ENG003", "Compressor Disc", "Engine", "General Electric", 
                    ["Citation CJ3+", "Legacy 450"], "High-pressure compressor disc",
                    price_range="$20,000-$35,000", criticality="critical", maintenance_interval=3000),
        AircraftPart("ENG004", "Oil Pump Assembly", "Engine", "Honeywell", 
                    ["King Air 350i", "PC-12 NGX"], "Engine lubrication system pump",
                    price_range="$2,000-$4,000", criticality="important", maintenance_interval=1000),
        AircraftPart("ENG005", "Starter Generator", "Engine", "Safran", 
                    ["Challenger 350", "Citation Latitude"], "Engine start and power generation",
                    price_range="$8,000-$12,000", criticality="important", maintenance_interval=2500),
    ]
    
    # Avionics parts
    avionics_parts = [
        AircraftPart("AVI001", "Primary Flight Display", "Avionics", "Garmin", 
                    ["Citation CJ3+", "King Air 350i"], "Main pilot flight display",
                    price_range="$25,000-$40,000", criticality="critical"),
        AircraftPart("AVI002", "Autopilot Computer", "Avionics", "Honeywell", 
                    ["Gulfstream G650", "Challenger 350"], "Flight management system",
                    price_range="$15,000-$25,000", criticality="critical"),
        AircraftPart("AVI003", "Weather Radar Unit", "Avionics", "Bendix", 
                    ["Citation Sovereign+", "Legacy 450"], "Weather detection system",
                    price_range="$35,000-$50,000", criticality="important"),
        AircraftPart("AVI004", "GPS Navigation Unit", "Avionics", "Garmin", 
                    ["PC-12 NGX", "Citation Latitude"], "Satellite navigation system",
                    price_range="$20,000-$30,000", criticality="critical"),
        AircraftPart("AVI005", "Radio Transceiver", "Avionics", "Collins Aerospace", 
                    ["Falcon 2000LXS", "King Air 350i"], "Communication radio system",
                    price_range="$5,000-$8,000", criticality="important"),
    ]
    
    # Landing gear parts
    landing_gear_parts = [
        AircraftPart("LG001", "Main Landing Gear Strut", "Landing Gear", "Safran", 
                    ["Gulfstream G650", "Falcon 2000LXS"], "Primary landing gear shock strut",
                    price_range="$12,000-$18,000", criticality="critical", maintenance_interval=5000),
        AircraftPart("LG002", "Nose Wheel Assembly", "Landing Gear", "Honeywell", 
                    ["Citation CJ3+", "Citation Latitude"], "Nose landing gear wheel and tire",
                    price_range="$3,000-$5,000", criticality="important", maintenance_interval=1500),
        AircraftPart("LG003", "Brake Disc Assembly", "Landing Gear", "Meggitt", 
                    ["Challenger 350", "Legacy 450"], "Main gear brake system",
                    price_range="$4,000-$7,000", criticality="critical", maintenance_interval=2000),
        AircraftPart("LG004", "Landing Gear Actuator", "Landing Gear", "Parker", 
                    ["Citation Sovereign+", "King Air 350i"], "Gear retraction system",
                    price_range="$8,000-$12,000", criticality="critical", maintenance_interval=3000),
        AircraftPart("LG005", "Anti-Skid Control Unit", "Landing Gear", "Crane Aerospace", 
                    ["PC-12 NGX", "Citation CJ3+"], "Brake anti-skid system",
                    price_range="$6,000-$10,000", criticality="important", maintenance_interval=2500),
    ]
    
    # Interior parts
    interior_parts = [
        AircraftPart("INT001", "Pilot Seat Assembly", "Interior", "AmSafe", 
                    ["Citation CJ3+", "Citation Latitude"], "Adjustable pilot seat",
                    price_range="$8,000-$15,000", criticality="standard"),
        AircraftPart("INT002", "Passenger Seat Track", "Interior", "Zodiac Aerospace", 
                    ["Gulfstream G650", "Challenger 350"], "Seat mounting rail system",
                    price_range="$2,000-$4,000", criticality="standard"),
        AircraftPart("INT003", "Cabin Window Assembly", "Interior", "PPG Aerospace", 
                    ["Falcon 2000LXS", "Legacy 450"], "Pressurized cabin window",
                    price_range="$5,000-$8,000", criticality="important"),
        AircraftPart("INT004", "LED Cabin Light Strip", "Interior", "Astronics", 
                    ["Citation Sovereign+", "King Air 350i"], "Interior LED lighting",
                    price_range="$1,000-$2,000", criticality="standard"),
        AircraftPart("INT005", "Entertainment System Display", "Interior", "Panasonic", 
                    ["Gulfstream G650", "PC-12 NGX"], "Passenger entertainment screen",
                    price_range="$3,000-$6,000", criticality="standard"),
    ]
    
    # Structural parts
    structural_parts = [
        AircraftPart("STR001", "Wing Spar Assembly", "Structure", "Boeing", 
                    ["Citation CJ3+", "Citation Sovereign+"], "Primary wing structural beam",
                    price_range="$25,000-$40,000", criticality="critical"),
        AircraftPart("STR002", "Fuselage Frame", "Structure", "Airbus", 
                    ["Challenger 350", "Legacy 450"], "Cabin frame structure",
                    price_range="$15,000-$25,000", criticality="critical"),
        AircraftPart("STR003", "Control Surface Hinge", "Structure", "Triumph Group", 
                    ["Falcon 2000LXS", "Citation Latitude"], "Aileron/rudder mounting",
                    price_range="$3,000-$5,000", criticality="important"),
        AircraftPart("STR004", "Cabin Door Seal", "Structure", "Eaton", 
                    ["King Air 350i", "PC-12 NGX"], "Pressurization door seal",
                    price_range="$1,500-$3,000", criticality="important"),
        AircraftPart("STR005", "Baggage Door Actuator", "Structure", "Safran", 
                    ["Gulfstream G650", "Citation CJ3+"], "Cargo compartment door system",
                    price_range="$4,000-$7,000", criticality="standard"),
    ]
    
    all_parts = engine_parts + avionics_parts + landing_gear_parts + interior_parts + structural_parts
    
    return {part.part_number: asdict(part) for part in all_parts}

def create_service_providers():
    """Create network of service providers with specialties and inventory"""
    
    providers = [
        ServiceProvider(
            id="SP001",
            name="Elite Aviation Services",
            location="Van Nuys, CA",
            coordinates={"lat": 34.2098, "lng": -118.4896},
            specialties=["Engine Overhaul", "Avionics Upgrade", "Annual Inspection"],
            certifications=["FAA Part 145", "EASA 145", "IS-BAO"],
            years_in_business=25,
            average_rating=4.8,
            total_reviews=156,
            hourly_rate=185.0,
            parts_inventory=["ENG001", "ENG003", "AVI001", "AVI004", "LG002", "INT001"],
            service_radius=100,
            contact_info={"phone": "(818) 555-0123", "email": "service@eliteaviation.com"}
        ),
        ServiceProvider(
            id="SP002", 
            name="Atlantic Aircraft Maintenance",
            location="Teterboro, NJ",
            coordinates={"lat": 40.8501, "lng": -74.0606},
            specialties=["Gulfstream Specialist", "Paint Services", "Interior Refurbishment"],
            certifications=["FAA Part 145", "Gulfstream Authorized"],
            years_in_business=18,
            average_rating=4.6,
            total_reviews=89,
            hourly_rate=195.0,
            parts_inventory=["ENG002", "AVI002", "AVI003", "LG001", "INT002", "INT005"],
            service_radius=75,
            contact_info={"phone": "(201) 555-0456", "email": "info@atlanticaircraft.com"}
        ),
        ServiceProvider(
            id="SP003",
            name="Southwest Aviation Group", 
            location="Phoenix, AZ",
            coordinates={"lat": 33.4734, "lng": -112.0074},
            specialties=["Citation Specialist", "Avionics Installation", "Pre-Purchase Inspection"],
            certifications=["FAA Part 145", "Textron Authorized"],
            years_in_business=12,
            average_rating=4.7,
            total_reviews=67,
            hourly_rate=165.0,
            parts_inventory=["ENG004", "ENG005", "AVI005", "LG003", "LG005", "STR001"],
            service_radius=150,
            contact_info={"phone": "(602) 555-0789", "email": "service@swaviation.com"}
        ),
        ServiceProvider(
            id="SP004",
            name="Midwest Aircraft Solutions",
            location="Chicago, IL", 
            coordinates={"lat": 41.9742, "lng": -87.9073},
            specialties=["King Air Specialist", "Propeller Overhaul", "Emergency Repair"],
            certifications=["FAA Part 145", "Beechcraft Authorized"],
            years_in_business=30,
            average_rating=4.9,
            total_reviews=234,
            hourly_rate=175.0,
            parts_inventory=["ENG004", "AVI001", "AVI005", "LG004", "INT004", "STR004"],
            service_radius=125,
            contact_info={"phone": "(312) 555-0234", "email": "support@midwestaircraft.com"}
        ),
        ServiceProvider(
            id="SP005",
            name="Florida Jet Center",
            location="Miami, FL",
            coordinates={"lat": 25.7959, "lng": -80.2871},
            specialties=["Bombardier Specialist", "AOG Service", "Line Maintenance"],
            certifications=["FAA Part 145", "Bombardier Authorized", "24/7 Service"],
            years_in_business=15,
            average_rating=4.5,
            total_reviews=98,
            hourly_rate=190.0,
            parts_inventory=["ENG002", "ENG005", "AVI002", "LG001", "LG003", "STR002"],
            service_radius=80,
            contact_info={"phone": "(305) 555-0567", "email": "ops@floridajetcenter.com"}
        ),
        ServiceProvider(
            id="SP006",
            name="Pacific Northwest Aviation",
            location="Seattle, WA",
            coordinates={"lat": 47.4502, "lng": -122.3088},
            specialties=["Embraer Specialist", "Structural Repair", "Modification"],
            certifications=["FAA Part 145", "Embraer Authorized"],
            years_in_business=22,
            average_rating=4.6,
            total_reviews=134,
            hourly_rate=180.0,
            parts_inventory=["ENG003", "AVI003", "AVI004", "LG002", "INT003", "STR003"],
            service_radius=90,
            contact_info={"phone": "(206) 555-0890", "email": "service@pnwaviation.com"}
        ),
        ServiceProvider(
            id="SP007",
            name="Texas Aviation Specialists",
            location="Dallas, TX",
            coordinates={"lat": 32.8470, "lng": -96.8517},
            specialties=["Falcon Specialist", "Hot Section Inspection", "Warranty Work"],
            certifications=["FAA Part 145", "Dassault Authorized"],
            years_in_business=20,
            average_rating=4.8,
            total_reviews=178,
            hourly_rate=185.0,
            parts_inventory=["ENG001", "ENG002", "AVI002", "AVI003", "LG004", "STR005"],
            service_radius=110,
            contact_info={"phone": "(214) 555-0345", "email": "dallas@texasaviation.com"}
        ),
        ServiceProvider(
            id="SP008",
            name="Rocky Mountain Aircraft",
            location="Denver, CO",
            coordinates={"lat": 39.8617, "lng": -104.6731},
            specialties=["Pilatus Specialist", "High Altitude Service", "Cold Weather Prep"],
            certifications=["FAA Part 145", "Pilatus Authorized"],
            years_in_business=8,
            average_rating=4.7,
            total_reviews=45,
            hourly_rate=170.0,
            parts_inventory=["ENG004", "AVI004", "AVI005", "LG005", "INT004", "STR004"],
            service_radius=200,
            contact_info={"phone": "(303) 555-0678", "email": "service@rmaircraft.com"}
        ),
    ]
    
    return {provider.id: asdict(provider) for provider in providers}

def calculate_service_match_score(user_needs: Dict, provider: Dict) -> int:
    """Calculate match score between user needs and service provider"""
    score = 100
    
    # Aircraft type match
    if user_needs.get('aircraft_type'):
        aircraft_specialties = {
            'citation': ['Citation Specialist', 'Textron Authorized'],
            'gulfstream': ['Gulfstream Specialist', 'Gulfstream Authorized'], 
            'challenger': ['Bombardier Specialist', 'Bombardier Authorized'],
            'king air': ['King Air Specialist', 'Beechcraft Authorized'],
            'falcon': ['Falcon Specialist', 'Dassault Authorized'],
            'legacy': ['Embraer Specialist', 'Embraer Authorized'],
            'pc-12': ['Pilatus Specialist', 'Pilatus Authorized']
        }
        
        aircraft_lower = user_needs['aircraft_type'].lower()
        matching_specialties = []
        for aircraft, specialties in aircraft_specialties.items():
            if aircraft in aircraft_lower:
                matching_specialties = specialties
                break
        
        provider_specialties = provider.get('specialties', []) + provider.get('certifications', [])
        if any(spec in provider_specialties for spec in matching_specialties):
            score += 25
        else:
            score -= 15
    
    # Service type match
    if user_needs.get('service_type'):
        service_type = user_needs['service_type'].lower()
        provider_specialties = [s.lower() for s in provider.get('specialties', [])]
        
        if any(service_type in spec for spec in provider_specialties):
            score += 20
        elif 'inspection' in service_type and any('inspection' in spec for spec in provider_specialties):
            score += 15
    
    # Parts availability
    if user_needs.get('parts_needed'):
        parts_needed = user_needs['parts_needed']
        parts_in_stock = provider.get('parts_inventory', [])
        
        available_parts = sum(1 for part in parts_needed if part in parts_in_stock)
        if available_parts > 0:
            score += (available_parts / len(parts_needed)) * 30
        else:
            score -= 10
    
    # Rating weight (higher rating = better)
    rating = provider.get('average_rating', 0)
    score += (rating - 3.0) * 10  # Boost for ratings above 3.0
    
    # Experience weight (more years = better, but diminishing returns)
    years = provider.get('years_in_business', 0)
    experience_bonus = min(years * 0.5, 15)  # Cap at 15 points
    score += experience_bonus
    
    # Cost consideration (lower rate = better)
    if user_needs.get('budget_priority') == 'low_cost':
        rate = provider.get('hourly_rate', 200)
        if rate < 170:
            score += 15
        elif rate < 190:
            score += 10
        elif rate > 200:
            score -= 10
    
    # Proximity bonus (closer = better)
    if user_needs.get('location_priority') == 'near':
        # This would require actual distance calculation in real implementation
        # For now, assume all providers are reasonably close
        score += 5
    
    # Urgency handling
    if user_needs.get('urgency') == 'emergency':
        if '24/7' in provider.get('certifications', []) or 'AOG' in provider.get('specialties', []):
            score += 20
        else:
            score -= 5
    
    return max(0, min(100, score))

def main():
    """Generate the complete parts catalog and service provider database"""
    
    # Create data directory
    os.makedirs('static/data', exist_ok=True)
    
    # Generate parts catalog
    parts_catalog = create_comprehensive_parts_catalog()
    
    # Generate service providers
    service_providers = create_service_providers()
    
    # Save to JSON files
    with open('static/data/parts_catalog.json', 'w') as f:
        json.dump(parts_catalog, f, indent=2)
    
    with open('static/data/service_providers.json', 'w') as f:
        json.dump(service_providers, f, indent=2)
    
    # Create aircraft parts mapping
    aircraft_parts_mapping = {}
    for part_num, part_data in parts_catalog.items():
        for aircraft in part_data['compatible_aircraft']:
            if aircraft not in aircraft_parts_mapping:
                aircraft_parts_mapping[aircraft] = []
            aircraft_parts_mapping[aircraft].append(part_num)
    
    with open('static/data/aircraft_parts_mapping.json', 'w') as f:
        json.dump(aircraft_parts_mapping, f, indent=2)
    
    print(f"✅ Created parts catalog with {len(parts_catalog)} parts")
    print(f"✅ Created service provider network with {len(service_providers)} providers")
    print(f"✅ Created aircraft parts mapping for {len(aircraft_parts_mapping)} aircraft models")
    print("\nFiles created:")
    print("- static/data/parts_catalog.json")
    print("- static/data/service_providers.json") 
    print("- static/data/aircraft_parts_mapping.json")

if __name__ == "__main__":
    main() 