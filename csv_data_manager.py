"""
CSV Data Manager - Single Source of Truth for Aircraft Data
Handles all CSV operations: loading, filtering, updating, and CRUD operations
"""

import os
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime
import shutil


class AircraftDataManager:
    def __init__(self, csv_path: str = 'Aircraft Data - Aircraft Data (1).csv'):
        self.csv_path = csv_path
        self.user_inputs_csv = 'Aircraft Data - User Inputs.csv'
        self.df = None
        self.user_inputs = None
        self.last_loaded = None

        # Column mapping for the CSV structure
        self.col_indices = {
            'aircraft_name': 0,      # Column index 0
            'manufacturer': 1,       # Column index 1
            'type': 2,               # Column index 2
            'multi_engine': 3,       # Column index 3
            'lowest_year': 4,        # Column index 4
            'highest_year': 5,       # Column index 5
            'range': 23,             # Column index 23 (X) - Range(NM)
            'speed': 24,             # Column index 24 (Y) - Speed(KTS)
            'passengers': 25,        # Column index 25 (Z) - Passengers
            'price': 26,             # Column index 26 (AA) - Average Price
            'annual_budget': 38,     # Column index 38 - Annual Budget
            'total_hourly_cost': 59,  # Column index 59 - Total Hourly Cost
            'hourly_variable_cost': 63,  # Column index 63 - Hourly Variable Cost
            'multi_year_cost': 40,   # Column index 40 - Multi-Year Total Cost
            'cost_to_charter': 42,   # Column index 42 - Cost To Charter
            'best_speed_dollar': 45,  # Column index 45 - Best Speed/$
            'best_range_dollar': 48,  # Column index 48 - Best Range/$
            'best_all_around': 57    # Column index 57 - Best All Around/$
        }

        # Load data on initialization
        self.load_data()

    def load_data(self) -> bool:
        """Load CSV data into memory"""
        try:
            if not os.path.exists(self.csv_path):
                print(f"❌ CSV file not found: {self.csv_path}")
                return False

            # Load main aircraft data
            self.df = pd.read_csv(self.csv_path, header=0)
            print(f"✅ Loaded {len(self.df)} rows from {self.csv_path}")

            # Load user inputs if available
            self.load_user_inputs()

            self.last_loaded = datetime.now()
            return True

        except Exception as e:
            print(f"❌ Error loading CSV data: {e}")
            return False

    def load_user_inputs(self):
        """Load user inputs CSV if available"""
        try:
            if os.path.exists(self.user_inputs_csv):
                df_inputs = pd.read_csv(self.user_inputs_csv, header=0)
                if len(df_inputs) > 0:
                    values = df_inputs.iloc[0].to_dict()
                    self.user_inputs = {}

                    for col in df_inputs.columns:
                        value = values.get(col, '')
                        clean_value = self._clean_value(value)

                        self.user_inputs[col] = {
                            'display_name': col,
                            'value': clean_value,
                            'original_value': value,
                            'type': self._determine_input_type(col, value)
                        }
                    print(f"✅ Loaded user inputs from {self.user_inputs_csv}")
        except Exception as e:
            print(f"⚠️ Could not load user inputs: {e}")
            self.user_inputs = None

    def _clean_value(self, value):
        """Clean values from CSV (remove $, %, commas, etc.)"""
        if isinstance(value, str):
            if value.startswith('$'):
                try:
                    return float(value.replace('$', '').replace(',', ''))
                except BaseException:
                    return value
            elif value.endswith('%'):
                try:
                    return float(value.replace('%', ''))
                except BaseException:
                    return value
        return value

    def _determine_input_type(self, field_name: str, value) -> str:
        """Determine input type based on field name and value"""
        field_lower = field_name.lower()
        if 'price' in field_lower or 'cost' in field_lower or 'pay' in field_lower:
            return 'currency'
        elif 'rate' in field_lower or 'percentage' in field_lower or str(value).endswith('%'):
            return 'percentage'
        elif 'year' in field_lower:
            return 'year'
        elif 'count' in field_lower or '# of' in field_name:
            return 'number'
        elif 'nm' in field_lower or 'range' in field_lower:
            return 'distance'
        elif 'kts' in field_lower or 'speed' in field_lower:
            return 'speed'
        elif 'ft' in field_lower or 'altitude' in field_lower:
            return 'length'
        elif 'pax' in field_lower or 'passenger' in field_lower:
            return 'number'
        else:
            return 'text'

    def get_all_aircraft(self) -> List[Dict[str, Any]]:
        """Get all aircraft as a list of dictionaries"""
        if self.df is None:
            return []

        aircraft_list = []

        for idx, (_, row) in enumerate(self.df.iterrows()):
            # Skip rows without aircraft name
            if pd.isna(row.iloc[self.col_indices['aircraft_name']]) or str(
                    row.iloc[self.col_indices['aircraft_name']]).strip() == '':
                continue

            try:
                aircraft_name = str(row.iloc[self.col_indices['aircraft_name']]).strip()

                # Skip header-like entries
                if aircraft_name.lower() in ['aircraft name', 'aircraft_name', 'name', ''] or aircraft_name == 'nan':
                    continue

                aircraft_data = self._row_to_aircraft_dict(row, idx)
                if aircraft_data:
                    aircraft_list.append(aircraft_data)

            except Exception as e:
                print(f"⚠️ Skipping row {idx} due to error: {e}")
                continue

        return aircraft_list

    def _row_to_aircraft_dict(self, row, idx: int) -> Optional[Dict[str, Any]]:
        """Convert a DataFrame row to aircraft dictionary"""
        try:
            # Extract basic info
            aircraft_name = str(row.iloc[self.col_indices['aircraft_name']]).strip()
            manufacturer = str(row.iloc[self.col_indices['manufacturer']]) if not pd.isna(
                row.iloc[self.col_indices['manufacturer']]) else aircraft_name.split(' ')[0]
            aircraft_type = str(row.iloc[self.col_indices['type']]) if not pd.isna(
                row.iloc[self.col_indices['type']]) else 'Unknown'

            # Extract numeric data with error handling
            def safe_numeric(value, default=0):
                try:
                    if pd.isna(value) or str(value).strip() == '':
                        return default
                    if isinstance(value, str):
                        value = value.replace('$', '').replace(',', '').replace('%', '')
                    return float(value)
                except (ValueError, TypeError):
                    return default

            def safe_int(value, default=0):
                try:
                    if pd.isna(value) or str(value).strip() == '':
                        return default
                    if isinstance(value, str):
                        value = value.replace(',', '')
                    return int(float(value))
                except (ValueError, TypeError):
                    return default

            # Extract all performance and cost data
            range_nm = safe_int(row.iloc[self.col_indices['range']], 0)
            speed_kts = safe_int(row.iloc[self.col_indices['speed']], 0)
            pax = safe_int(row.iloc[self.col_indices['passengers']], 0)
            price = safe_numeric(row.iloc[self.col_indices['price']], 0)
            year = safe_int(row.iloc[self.col_indices['highest_year']], 2020)

            # Determine category
            if aircraft_type.lower() in ['business jet', 'jet']:
                category_type = 'jet'
            elif aircraft_type.lower() in ['turboprop']:
                category_type = 'turboprop'
            elif aircraft_type.lower() in ['piston']:
                category_type = 'piston'
            else:
                category_type = 'jet'  # Default

            # Create aircraft dictionary
            aircraft = {
                'id': f"csv_{idx}",
                'title': aircraft_name,
                'manufacturer': manufacturer,
                'model': aircraft_name.replace(manufacturer, '').strip() if aircraft_name.startswith(manufacturer) else aircraft_name,
                'category': category_type,
                'type': aircraft_type,
                'year': year,
                'price': price,
                'range': range_nm,
                'max_speed': speed_kts,
                'seats': pax,
                'description': f"{aircraft_type} aircraft with {pax} seats, {range_nm} nm range, and {speed_kts} kts cruise speed.",
                'location': 'Various',
                'contact': 'Sales Department',
                'images': [f'{category_type}_placeholder.jpg'],
                'features': [
                    f"Range: {range_nm:,} nm",
                    f"Speed: {speed_kts} kts",
                    f"Passengers: {pax}",
                    f"Type: {aircraft_type}"
                ],
                'created_at': '2024-01-01',
                'owner_id': 'csv_data',

                # Additional CSV data
                'total_hourly_cost': safe_numeric(row.iloc[self.col_indices['total_hourly_cost']], 0),
                'annual_budget': safe_numeric(row.iloc[self.col_indices['annual_budget']], 0),
                'hourly_variable_cost': safe_numeric(row.iloc[self.col_indices['hourly_variable_cost']], 0),
                'multi_year_cost': safe_numeric(row.iloc[self.col_indices['multi_year_cost']], 0),
                'cost_to_charter': safe_numeric(row.iloc[self.col_indices['cost_to_charter']], 0),
                'best_speed_dollar': safe_numeric(row.iloc[self.col_indices['best_speed_dollar']], 0),
                'best_range_dollar': safe_numeric(row.iloc[self.col_indices['best_range_dollar']], 0),
                'best_all_around': safe_numeric(row.iloc[self.col_indices['best_all_around']], 0),
                'multi_engine': str(row.iloc[self.col_indices['multi_engine']]) if not pd.isna(row.iloc[self.col_indices['multi_engine']]) else 'Unknown'
            }

            # Calculate derived metrics
            if price > 0:
                aircraft.update(self._calculate_derived_metrics(aircraft))

            return aircraft

        except Exception as e:
            print(f"❌ Error converting row {idx}: {e}")
            return None

    def _calculate_derived_metrics(self, aircraft: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate derived metrics for aircraft"""
        price = aircraft['price']
        speed_kts = aircraft['max_speed']
        range_nm = aircraft['range']
        pax = aircraft['seats']

        # Calculate efficiency scores
        speed_per_dollar = speed_kts / (price / 1000000) if price > 0 else 0
        range_per_dollar = range_nm / (price / 1000000) if price > 0 else 0
        performance_score = (speed_kts * range_nm) / (price / 1000000) if price > 0 else 0
        efficiency_score = (speed_kts * range_nm * pax) / (price / 1000000) if price > 0 else 0

        # Calculate financial metrics (using default values)
        avg_trip_length = 300
        num_trips = 25
        years_ownership = 5
        depreciation_rate = 4.0

        avg_leg_hours = avg_trip_length / speed_kts if speed_kts > 0 else 0
        annual_hours = (avg_trip_length * num_trips) / speed_kts if speed_kts > 0 else 0

        # Use actual annual budget from CSV if available
        annual_budget = aircraft.get('annual_budget', 0)
        if annual_budget == 0:
            # Calculate estimated annual budget
            base_hourly_cost = 800
            price_multiplier = price / 5000000
            speed_bonus = speed_kts / 400
            seats_penalty = pax / 6
            hourly_operating_cost = base_hourly_cost * price_multiplier * speed_bonus * seats_penalty

            annual_operating_cost = hourly_operating_cost * annual_hours
            annual_budget = annual_operating_cost + (price * depreciation_rate / 100)

        # Multi-year total cost
        mytc = (annual_budget * years_ownership) + price - (price * (1 - depreciation_rate / 100) ** years_ownership)

        # Charter cost comparison
        charter_cost_per_hour = 2500
        total_charter_cost = charter_cost_per_hour * annual_hours * years_ownership
        own_charter_savings = total_charter_cost - mytc

        # Overall score
        best_all_around = aircraft.get('best_all_around', 0)
        overall_score = best_all_around if best_all_around > 0 else max(1, round((
            (speed_per_dollar * 0.2) +
            (range_per_dollar * 0.2) +
            ((performance_score / 100) * 0.3) +
            ((efficiency_score / 100) * 0.3)
        ) * 100))

        return {
            'speed_per_dollar': round(speed_per_dollar, 1),
            'range_per_dollar': round(range_per_dollar, 1),
            'performance_score': round(performance_score / 100, 1),
            'efficiency_score': round(efficiency_score / 100, 1),
            'avg_leg_hours': round(avg_leg_hours, 1),
            'calculated_annual_hours': round(annual_hours),
            'calculated_annual_budget': round(annual_budget),
            'mytc': round(mytc),
            'own_charter_savings': round(own_charter_savings),
            'overall_score': overall_score
        }

    def filter_aircraft(self, aircraft_list: List[Dict], filters: Dict[str, Any]) -> List[Dict]:
        """Apply filters to aircraft list"""
        filtered = aircraft_list.copy()

        # Apply each filter
        if filters.get('category'):
            filtered = [a for a in filtered if a.get('category', '').lower() == filters['category'].lower()]

        if filters.get('min_price', 0) > 0:
            filtered = [a for a in filtered if a.get('price', 0) >= filters['min_price']]

        if filters.get('max_price', float('inf')) < float('inf'):
            filtered = [a for a in filtered if a.get('price', 0) <= filters['max_price']]

        if filters.get('min_year', 0) > 0:
            filtered = [a for a in filtered if a.get('year', 0) >= filters['min_year']]

        if filters.get('max_year', 9999) < 9999:
            filtered = [a for a in filtered if a.get('year', 0) <= filters['max_year']]

        if filters.get('manufacturer'):
            filtered = [a for a in filtered if filters['manufacturer'].lower() in a.get('manufacturer', '').lower()]

        if filters.get('min_range', 0) > 0:
            filtered = [a for a in filtered if a.get('range', 0) >= filters['min_range']]

        if filters.get('max_range', float('inf')) < float('inf'):
            filtered = [a for a in filtered if a.get('range', 0) <= filters['max_range']]

        if filters.get('seats', 0) > 0:
            filtered = [a for a in filtered if a.get('seats', 0) >= filters['seats']]

        if filters.get('max_flight_hours'):
            filtered = [a for a in filtered if a.get('total_hours', 0) <= filters['max_flight_hours']]

        return filtered

    def sort_aircraft(self, aircraft_list: List[Dict], sort_by: str = 'recommended') -> List[Dict]:
        """Sort aircraft list by specified criteria"""
        sorted_list = aircraft_list.copy()

        if sort_by == 'price_low':
            sorted_list.sort(key=lambda x: x.get('price', 0))
        elif sort_by == 'price_high':
            sorted_list.sort(key=lambda x: x.get('price', 0), reverse=True)
        elif sort_by == 'range_high':
            sorted_list.sort(key=lambda x: x.get('range', 0), reverse=True)
        elif sort_by == 'range_low':
            sorted_list.sort(key=lambda x: x.get('range', 0))
        elif sort_by == 'speed_high':
            sorted_list.sort(key=lambda x: x.get('max_speed', 0), reverse=True)
        elif sort_by == 'speed_low':
            sorted_list.sort(key=lambda x: x.get('max_speed', 0))
        elif sort_by == 'passengers_high':
            sorted_list.sort(key=lambda x: x.get('seats', 0), reverse=True)
        elif sort_by == 'passengers_low':
            sorted_list.sort(key=lambda x: x.get('seats', 0))
        elif sort_by == 'year_new':
            sorted_list.sort(key=lambda x: x.get('year', 0), reverse=True)
        elif sort_by == 'year_old':
            sorted_list.sort(key=lambda x: x.get('year', 0))
        elif sort_by == 'annual_budget_low':
            sorted_list.sort(key=lambda x: x.get('annual_budget', 0) or x.get('calculated_annual_budget', 0))
        elif sort_by == 'annual_budget_high':
            sorted_list.sort(
                key=lambda x: x.get(
                    'annual_budget',
                    0) or x.get(
                    'calculated_annual_budget',
                    0),
                reverse=True)
        elif sort_by == 'total_hourly_cost_low':
            sorted_list.sort(key=lambda x: x.get('total_hourly_cost', 0))
        elif sort_by == 'total_hourly_cost_high':
            sorted_list.sort(key=lambda x: x.get('total_hourly_cost', 0), reverse=True)
        elif sort_by == 'lowest_hourly_cost':
            sorted_list.sort(key=lambda x: x.get('total_hourly_cost', 0))
        elif sort_by == 'best_all_around':
            sorted_list.sort(key=lambda x: x.get('best_all_around', 0), reverse=True)
        elif sort_by == 'best_speed_dollar':
            sorted_list.sort(key=lambda x: x.get('best_speed_dollar', 0), reverse=True)
        elif sort_by == 'best_range_dollar':
            sorted_list.sort(key=lambda x: x.get('best_range_dollar', 0), reverse=True)
        elif sort_by == 'best_performance_dollar':
            sorted_list.sort(key=lambda x: x.get('performance_score', 0), reverse=True)
        elif sort_by == 'best_efficiency_dollar':
            sorted_list.sort(key=lambda x: x.get('efficiency_score', 0), reverse=True)
        elif sort_by == 'lowest_annual_cost':
            sorted_list.sort(key=lambda x: x.get('annual_budget', 0) or x.get('calculated_annual_budget', 0))
        elif sort_by == 'lowest_mytc':
            sorted_list.sort(key=lambda x: x.get('mytc', 0))
        elif sort_by == 'best_own_charter_savings':
            sorted_list.sort(key=lambda x: x.get('own_charter_savings', 0), reverse=True)
        elif sort_by == 'recommendation_low':
            # Sort by lowest recommendation score first (most accessible/budget-friendly)
            sorted_list.sort(key=lambda x: x.get('recommendation_score', 0), reverse=False)
        elif sort_by == 'recommendation_high':
            # Sort by highest recommendation score first (best match for criteria)
            sorted_list.sort(key=lambda x: x.get('recommendation_score', 0), reverse=True)
        elif sort_by == 'aircraft_name':
            sorted_list.sort(key=lambda x: x.get('title', ''))
        elif sort_by == 'manufacturer':
            sorted_list.sort(key=lambda x: x.get('manufacturer', ''))
        elif sort_by == 'type':
            sorted_list.sort(key=lambda x: x.get('type', ''))
        # Default sorting for 'recommended' is now handled in the calling function
        # Add more sorting options as needed

        return sorted_list

    def get_aircraft_by_id(self, aircraft_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific aircraft by ID"""
        aircraft_list = self.get_all_aircraft()
        for aircraft in aircraft_list:
            if aircraft.get('id') == aircraft_id:
                return aircraft
        return None

    def upload_csv(self, file_path: str) -> bool:
        """Upload and replace the current CSV file"""
        try:
            # Backup current file
            if os.path.exists(self.csv_path):
                backup_path = f"{self.csv_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                shutil.copy2(self.csv_path, backup_path)
                print(f"✅ Backed up current CSV to {backup_path}")

            # Replace with new file
            shutil.copy2(file_path, self.csv_path)
            print(f"✅ Uploaded new CSV: {file_path}")

            # Reload data
            return self.load_data()

        except Exception as e:
            print(f"❌ Error uploading CSV: {e}")
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """Get overall statistics about the aircraft data"""
        aircraft_list = self.get_all_aircraft()

        if not aircraft_list:
            return {}

        total_aircraft = len(aircraft_list)

        # Calculate statistics
        prices = [a['price'] for a in aircraft_list if a['price'] > 0]
        ranges = [a['range'] for a in aircraft_list if a['range'] > 0]
        speeds = [a['max_speed'] for a in aircraft_list if a['max_speed'] > 0]

        categories = {}
        manufacturers = {}

        for aircraft in aircraft_list:
            category = aircraft.get('category', 'Unknown')
            categories[category] = categories.get(category, 0) + 1

            manufacturer = aircraft.get('manufacturer', 'Unknown')
            manufacturers[manufacturer] = manufacturers.get(manufacturer, 0) + 1

        return {
            'total_aircraft': total_aircraft,
            'price_stats': {
                'min': min(prices) if prices else 0,
                'max': max(prices) if prices else 0,
                'avg': sum(prices) / len(prices) if prices else 0
            },
            'range_stats': {
                'min': min(ranges) if ranges else 0,
                'max': max(ranges) if ranges else 0,
                'avg': sum(ranges) / len(ranges) if ranges else 0
            },
            'speed_stats': {
                'min': min(speeds) if speeds else 0,
                'max': max(speeds) if speeds else 0,
                'avg': sum(speeds) / len(speeds) if speeds else 0
            },
            'categories': categories,
            'manufacturers': manufacturers,
            'last_loaded': self.last_loaded.isoformat() if self.last_loaded else None
        }


# Global instance
aircraft_data_manager = AircraftDataManager()
