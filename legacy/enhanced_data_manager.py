"""
Enhanced Aircraft Data Manager for Marketplace
Handles CSV data as live marketplace listings with advanced filtering
Built for scale and performance like a Google product
"""

import pandas as pd
import numpy as np
import json
import os
from typing import Dict, List, Any, Optional, Union, cast
from pandas import Series, DataFrame
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnhancedAircraftDataManager:
    """
    Advanced data manager for aircraft marketplace with live filtering capabilities
    """
    
    def __init__(self):
        self.aircraft_data_path = "Aircraft Data - Aircraft Data (1).csv"
        self.user_inputs_path = "Aircraft Data - User Inputs.csv"
        self.aircraft_df = None
        self.user_preferences = None
        self.filters_cache = {}
        self.load_data()
    
    def load_data(self):
        """Load and preprocess aircraft data"""
        try:
            # Load aircraft data
            self.aircraft_df = pd.read_csv(self.aircraft_data_path)
            logger.info(f"Loaded {len(self.aircraft_df)} aircraft records")
            
            # Load user preferences if file exists
            if os.path.exists(self.user_inputs_path):
                self.user_preferences = pd.read_csv(self.user_inputs_path)
                logger.info("Loaded user preferences")
            else:
                logger.warning("User preferences file not found, creating empty DataFrame")
                self.user_preferences = pd.DataFrame()
            
            # Clean and enhance data
            self._clean_and_enhance_data()
            
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            # Create empty DataFrame as fallback
            self.aircraft_df = pd.DataFrame()
            self.user_preferences = pd.DataFrame()
    
    def _clean_and_enhance_data(self):
        """Clean data and add computed fields for better filtering"""
        if self.aircraft_df is None or len(self.aircraft_df) == 0:
            logger.warning("No aircraft data to clean")
            return
        
        # Convert price strings to numbers
        if 'Average Price' in self.aircraft_df.columns:
            price_series = cast(Series, pd.to_numeric(
                self.aircraft_df['Average Price'].replace(r'[\$,]', '', regex=True), 
                errors='coerce'
            ))
            self.aircraft_df['price_numeric'] = price_series.fillna(0)
        else:
            self.aircraft_df['price_numeric'] = 1000000  # Default price
        
        # Convert range to numeric
        if 'Range(NM)' in self.aircraft_df.columns:
            range_series = cast(Series, pd.to_numeric(self.aircraft_df['Range(NM)'], errors='coerce'))
            self.aircraft_df['Range(NM)'] = range_series.fillna(0)
        
        # Convert speed to numeric  
        if 'Speed(KTS)' in self.aircraft_df.columns:
            speed_series = cast(Series, pd.to_numeric(self.aircraft_df['Speed(KTS)'], errors='coerce'))
            self.aircraft_df['Speed(KTS)'] = speed_series.fillna(0)
        
        # Convert passengers to numeric
        if 'Passengers' in self.aircraft_df.columns:
            passengers_series = cast(Series, pd.to_numeric(self.aircraft_df['Passengers'], errors='coerce'))
            self.aircraft_df['Passengers'] = passengers_series.fillna(0)
        
        # Convert year columns to numeric
        if 'Lowest Year' in self.aircraft_df.columns:
            lowest_year_series = cast(Series, pd.to_numeric(self.aircraft_df['Lowest Year'], errors='coerce'))
            self.aircraft_df['Lowest Year'] = lowest_year_series.fillna(1980)
        
        if 'Highest Year' in self.aircraft_df.columns:
            highest_year_series = cast(Series, pd.to_numeric(self.aircraft_df['Highest Year'], errors='coerce'))
            self.aircraft_df['Highest Year'] = highest_year_series.fillna(2024)
        
        # Add aircraft categories based on type
        if 'Type' in self.aircraft_df.columns:
            def map_category(aircraft_type: Any) -> str:
                mapping = {
                    'Piston': 'piston',
                    'Turboprop': 'turboprop', 
                    'Business Jet': 'jet'
                }
                return mapping.get(aircraft_type, 'unknown')
            self.aircraft_df['category'] = self.aircraft_df['Type'].apply(map_category)
        else:
            self.aircraft_df['category'] = 'unknown'
        
        # Add size categories based on passengers
        def categorize_size(passengers):
            if pd.isna(passengers) or passengers <= 4:
                return 'light'
            elif passengers <= 8:
                return 'mid'
            elif passengers <= 12:
                return 'super-mid'
            else:
                return 'heavy'
        
        self.aircraft_df['size_category'] = self.aircraft_df['Passengers'].apply(categorize_size)
        
        # Calculate efficiency metrics (avoid division by zero)
        range_safe = self.aircraft_df['Range(NM)'].replace(0, 1)  # Replace 0 with 1 to avoid division by zero
        passengers_safe = self.aircraft_df['Passengers'].replace(0, 1)
        
        self.aircraft_df['cost_per_nm'] = self.aircraft_df['price_numeric'] / range_safe
        self.aircraft_df['cost_per_passenger'] = self.aircraft_df['price_numeric'] / passengers_safe
        
        # Add unique listing IDs
        self.aircraft_df['listing_id'] = range(len(self.aircraft_df))
        
        # Ensure all required columns exist with default values
        required_columns = {
            'Multi Engine': 'No',
            'Max Operating Altitude (ft)': 0,
            'Balanced Field Length (ft)': 0,
            'Cabin Height (ft)': 0,
            'Cabin Width (ft)': 0,
            'Cabin Length (ft)': 0,
            'Cabin Volume (cubic ft)': 0,
            'Baggage Volume (cubic ft)': 0,
            'Total Hourly Cost': 0
        }
        
        for col, default_val in required_columns.items():
            if col not in self.aircraft_df.columns:
                self.aircraft_df[col] = default_val
            else:
                # Convert to numeric if it should be numeric
                if col != 'Multi Engine':
                    numeric_series = cast(Series, pd.to_numeric(self.aircraft_df[col], errors='coerce'))
                    self.aircraft_df[col] = numeric_series.fillna(default_val)
        
        # Handle manufacturer column
        if 'Manufacturer' not in self.aircraft_df.columns:
            self.aircraft_df['Manufacturer'] = 'Unknown'
    
    def get_filter_options(self) -> Dict[str, List]:
        """Get all available filter options for the UI"""
        if self.aircraft_df is None or len(self.aircraft_df) == 0:
            return {'manufacturers': [], 'categories': [], 'size_categories': [], 'price_ranges': [], 'year_ranges': []}
            
        return {
            'manufacturers': sorted(self.aircraft_df['Manufacturer'].dropna().unique().tolist()),
            'categories': sorted(self.aircraft_df['category'].dropna().unique().tolist()),
            'size_categories': sorted(self.aircraft_df['size_category'].dropna().unique().tolist()),
            'price_ranges': [
                {'label': 'Under $500K', 'min': 0, 'max': 500000},
                {'label': '$500K - $1M', 'min': 500000, 'max': 1000000},
                {'label': '$1M - $2M', 'min': 1000000, 'max': 2000000},
                {'label': '$2M - $5M', 'min': 2000000, 'max': 5000000},
                {'label': '$5M - $10M', 'min': 5000000, 'max': 10000000},
                {'label': '$10M+', 'min': 10000000, 'max': float('inf')}
            ],
            'year_ranges': [
                {'label': '2020+', 'min': 2020, 'max': 2024},
                {'label': '2010-2019', 'min': 2010, 'max': 2019},
                {'label': '2000-2009', 'min': 2000, 'max': 2009},
                {'label': '1990-1999', 'min': 1990, 'max': 1999},
                {'label': 'Pre-1990', 'min': 1900, 'max': 1989}
            ]
        }
    
    def search_aircraft(self, filters: Dict[str, Any], 
                       sort_by: str = 'relevance',
                       page: int = 1, 
                       per_page: int = 20) -> Dict[str, Any]:
        """
        Advanced search with multiple filters - CarGurus style
        """
        if self.aircraft_df is None or len(self.aircraft_df) == 0:
            return {'listings': [], 'total_results': 0, 'page': 1, 'per_page': per_page, 'total_pages': 0, 'filters_applied': filters, 'sort_by': sort_by}
            
        df: DataFrame = self.aircraft_df.copy()
        
        # Apply filters
        if filters.get('price_min'):
            df = cast(DataFrame, df[df['price_numeric'] >= float(filters['price_min'])])
        
        if filters.get('price_max'):
            df = cast(DataFrame, df[df['price_numeric'] <= float(filters['price_max'])])
        
        if filters.get('min_range'):
            df = cast(DataFrame, df[df['Range(NM)'] >= float(filters['min_range'])])
        
        if filters.get('max_range'):
            df = cast(DataFrame, df[df['Range(NM)'] <= float(filters['max_range'])])
        
        if filters.get('min_passengers'):
            df = cast(DataFrame, df[df['Passengers'] >= int(filters['min_passengers'])])
        
        if filters.get('max_passengers'):
            df = cast(DataFrame, df[df['Passengers'] <= int(filters['max_passengers'])])
        
        if filters.get('min_speed'):
            df = cast(DataFrame, df[df['Speed(KTS)'] >= float(filters['min_speed'])])
        
        if filters.get('category'):
            if isinstance(filters['category'], list):
                df = cast(DataFrame, df[df['category'].isin(filters['category'])])
            else:
                df = cast(DataFrame, df[df['category'] == filters['category']])
        
        if filters.get('manufacturer'):
            if isinstance(filters['manufacturer'], list):
                df = cast(DataFrame, df[df['Manufacturer'].isin(filters['manufacturer'])])
            else:
                df = cast(DataFrame, df[df['Manufacturer'] == filters['manufacturer']])
        
        if filters.get('size_category'):
            if isinstance(filters['size_category'], list):
                df = cast(DataFrame, df[df['size_category'].isin(filters['size_category'])])
            else:
                df = cast(DataFrame, df[df['size_category'] == filters['size_category']])
        
        if filters.get('year_min'):
            df = cast(DataFrame, df[df['Highest Year'] >= int(filters['year_min'])])
        
        if filters.get('year_max'):
            df = cast(DataFrame, df[df['Lowest Year'] <= int(filters['year_max'])])
        
        if filters.get('multi_engine') is not None:
            multi_engine_bool = filters['multi_engine'] == 'Yes'
            df = cast(DataFrame, df[df['Multi Engine'] == ('Yes' if multi_engine_bool else 'No')])
        
        # Text search
        if filters.get('search_text'):
            search_text = filters['search_text'].lower()
            text_mask = (
                df['Manufacturer'].str.lower().str.contains(search_text, na=False) |
                df['Type'].str.lower().str.contains(search_text, na=False) |
                df.iloc[:, 0].str.lower().str.contains(search_text, na=False)  # Model name
            )
            df = cast(DataFrame, df[text_mask])
        
        # Sort results
        df = cast(DataFrame, self._sort_results(df, sort_by))
        
        # Pagination
        total_results = len(df)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_df = df.iloc[start_idx:end_idx]
        
        # Convert to listings format
        listings = []
        for _, row in paginated_df.iterrows():
            listing = self._row_to_listing(row)
            listings.append(listing)
        
        return {
            'listings': listings,
            'total_results': total_results,
            'page': page,
            'per_page': per_page,
            'total_pages': (total_results + per_page - 1) // per_page,
            'filters_applied': filters,
            'sort_by': sort_by
        }
    
    def _sort_results(self, df: pd.DataFrame, sort_by: str) -> pd.DataFrame:
        """Sort search results"""
        if sort_by == 'price_low':
            return df.sort_values('price_numeric', ascending=True)
        elif sort_by == 'price_high':
            return df.sort_values('price_numeric', ascending=False)
        elif sort_by == 'year_new':
            return df.sort_values('Highest Year', ascending=False)
        elif sort_by == 'year_old':
            return df.sort_values('Lowest Year', ascending=True)
        elif sort_by == 'range_high':
            return df.sort_values('Range(NM)', ascending=False)
        elif sort_by == 'speed_high':
            return df.sort_values('Speed(KTS)', ascending=False)
        elif sort_by == 'passengers_high':
            return df.sort_values('Passengers', ascending=False)
        elif sort_by == 'efficiency':
            return df.sort_values('cost_per_nm', ascending=True)
        else:  # relevance or default
            # Sort by a combination of factors for relevance
            df['relevance_score'] = (
                df['Speed(KTS)'].fillna(0) * 0.3 +
                df['Range(NM)'].fillna(0) * 0.3 +
                df['Passengers'].fillna(0) * 10 +
                (2024 - df['Lowest Year'].fillna(2024)) * 0.1
            )
            return df.sort_values('relevance_score', ascending=False)
    
    def _row_to_listing(self, row: pd.Series) -> Dict[str, Any]:
        """Convert DataFrame row to listing dictionary"""
        # Extract model name (first column)
        model_name = str(row.iloc[0]) if not pd.isna(row.iloc[0]) else "Unknown Model"
        
        # Helper function to safely convert values
        def safe_int(value: Any) -> int:
            try:
                return int(value) if not pd.isna(value) else 0
            except (ValueError, TypeError):
                return 0
        
        def safe_float(value: Any) -> float:
            try:
                return float(value) if not pd.isna(value) else 0.0
            except (ValueError, TypeError):
                return 0.0
        
        def safe_str(value: Any, default: str = 'Unknown') -> str:
            try:
                return str(value) if not pd.isna(value) else default
            except (ValueError, TypeError):
                return default

        return {
            'id': safe_int(row['listing_id']),
            'model': model_name,
            'manufacturer': safe_str(row['Manufacturer']),
            'type': safe_str(row['Type']),
            'category': row['category'],
            'size_category': row['size_category'],
            'price': safe_int(row['price_numeric']),
            'price_formatted': f"${safe_int(row['price_numeric']):,}" if safe_int(row['price_numeric']) > 0 else 'Price on Request',
            'range': safe_int(row['Range(NM)']),
            'speed': safe_int(row['Speed(KTS)']),
            'passengers': safe_int(row['Passengers']),
            'year_range': f"{safe_int(row['Lowest Year'])}-{safe_int(row['Highest Year'])}" if safe_int(row['Lowest Year']) > 0 else 'N/A',
            'lowest_year': safe_int(row['Lowest Year']),
            'highest_year': safe_int(row['Highest Year']),
            'multi_engine': row['Multi Engine'] == 'Yes',
            'max_altitude': safe_int(row['Max Operating Altitude (ft)']),
            'runway_length': safe_int(row['Balanced Field Length (ft)']),
            'cabin_height': safe_float(row['Cabin Height (ft)']),
            'cabin_width': safe_float(row['Cabin Width (ft)']),
            'cabin_length': safe_float(row['Cabin Length (ft)']),
            'cabin_volume': safe_float(row['Cabin Volume (cubic ft)']),
            'baggage_volume': safe_float(row['Baggage Volume (cubic ft)']),
            'cost_per_nm': safe_float(row['cost_per_nm']),
            'cost_per_passenger': safe_float(row['cost_per_passenger']),
            'total_hourly_cost': safe_float(row['Total Hourly Cost']) if 'Total Hourly Cost' in row.index else 0.0,
            'image_url': f"/static/images/aircraft/{model_name.lower().replace(' ', '_')}.jpg",
            'details_url': f"/aircraft/{row['listing_id']}",
            'contact_url': f"/contact/{row['listing_id']}"
        }
    
    def get_aircraft_details(self, listing_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed information for a specific aircraft"""
        if self.aircraft_df is None or len(self.aircraft_df) == 0:
            return None
            
        try:
            row = self.aircraft_df[self.aircraft_df['listing_id'] == listing_id].iloc[0]
            listing = self._row_to_listing(row)
            
            # Add additional details
            all_columns = self.aircraft_df.columns.tolist()
            for col in all_columns:
                if col not in ['listing_id'] and not pd.isna(row[col]):
                    key = col.lower().replace(' ', '_').replace('(', '').replace(')', '').replace('/', '_')
                    listing[f'spec_{key}'] = row[col]
            
            return listing
            
        except (IndexError, KeyError):
            return None
    
    def get_similar_aircraft(self, listing_id: int, limit: int = 6) -> List[Dict[str, Any]]:
        """Find similar aircraft based on specifications"""
        if self.aircraft_df is None or len(self.aircraft_df) == 0:
            return []
            
        try:
            base_aircraft = self.aircraft_df[self.aircraft_df['listing_id'] == listing_id].iloc[0]
            
            # Calculate similarity scores
            df = self.aircraft_df.copy()
            df = df[df['listing_id'] != listing_id]  # Exclude the base aircraft
            
            # Similarity based on category, price range, passenger count, and range
            price_tolerance = 0.5  # 50% price tolerance
            passenger_tolerance = 2
            range_tolerance = 500  # NM
            
            # Initialize similarity score
            df['similarity_score'] = 0.0
            
            # Calculate each similarity component separately and sum them
            # Category match (high weight)
            category_score = (df['category'] == base_aircraft['category']).astype(float) * 30.0
            
            # Price similarity
            price_diff = abs(df['price_numeric'] - base_aircraft['price_numeric']) / max(base_aircraft['price_numeric'], 1)
            price_score = (price_diff <= price_tolerance).astype(float) * 25.0
            
            # Passenger similarity
            passenger_diff = abs(df['Passengers'] - base_aircraft['Passengers'])
            passenger_score = (passenger_diff <= passenger_tolerance).astype(float) * 20.0
            
            # Range similarity
            range_diff = abs(df['Range(NM)'] - base_aircraft['Range(NM)'])
            range_score = (range_diff <= range_tolerance).astype(float) * 15.0
            
            # Manufacturer match
            manufacturer_score = (df['Manufacturer'] == base_aircraft['Manufacturer']).astype(float) * 10.0
            
            # Sum all similarity components
            df['similarity_score'] = category_score + price_score + passenger_score + range_score + manufacturer_score
            
            # Sort by similarity and get top results
            similar_df = df.nlargest(limit, 'similarity_score')  # type: ignore
            
            return [self._row_to_listing(row) for _, row in similar_df.iterrows()]
            
        except (IndexError, KeyError):
            return []
    
    def get_market_insights(self, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get market insights and statistics"""
        if self.aircraft_df is None or len(self.aircraft_df) == 0:
            return {'error': 'No aircraft data available'}
            
        df: DataFrame = self.aircraft_df.copy()
        
        # Apply filters if provided
        if filters:
            search_result = self.search_aircraft(filters, per_page=10000)
            if search_result['listings']:
                filtered_ids = [listing['id'] for listing in search_result['listings']]
                df = cast(DataFrame, df[df['listing_id'].isin(filtered_ids)])
        
        if len(df) == 0:
            return {'error': 'No aircraft match the specified criteria'}
        
        insights = {
            'total_aircraft': len(df),
            'price_stats': {
                'min': int(df['price_numeric'].min()),
                'max': int(df['price_numeric'].max()),
                'avg': int(df['price_numeric'].mean()),
                'median': int(df['price_numeric'].median())
            },
            'category_distribution': df['category'].value_counts().to_dict(),
            'manufacturer_distribution': df['Manufacturer'].value_counts().head(10).to_dict(),
            'size_distribution': df['size_category'].value_counts().to_dict(),
            'range_stats': {
                'min': int(df['Range(NM)'].min()),
                'max': int(df['Range(NM)'].max()),
                'avg': int(df['Range(NM)'].mean())
            },
            'speed_stats': {
                'min': int(df['Speed(KTS)'].min()),
                'max': int(df['Speed(KTS)'].max()),
                'avg': int(df['Speed(KTS)'].mean())
            }
        }
        
        return insights
    
    def suggest_filters(self, partial_query: str) -> List[Dict[str, Any]]:
        """Suggest filters based on partial query - for autocomplete"""
        if self.aircraft_df is None or len(self.aircraft_df) == 0:
            return []
            
        suggestions = []
        partial_lower = partial_query.lower()
        
        # Manufacturer suggestions
        manufacturers = self.aircraft_df['Manufacturer'].dropna().unique()
        for mfg in manufacturers:
            if partial_lower in mfg.lower():
                suggestions.append({
                    'type': 'manufacturer',
                    'value': mfg,
                    'label': f"Manufacturer: {mfg}",
                    'count': len(self.aircraft_df[self.aircraft_df['Manufacturer'] == mfg])
                })
        
        # Model suggestions  
        models = self.aircraft_df.iloc[:, 0].dropna().unique()
        for model in models:
            if partial_lower in str(model).lower():
                suggestions.append({
                    'type': 'model',
                    'value': str(model),
                    'label': f"Model: {model}",
                    'count': 1
                })
        
        return suggestions[:10]  # Limit to top 10 suggestions


# Global instance
enhanced_data_manager = EnhancedAircraftDataManager() 