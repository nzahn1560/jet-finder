"""Charter planning uses supplied aircraft and airport data. It does not invent rates."""
import unittest

import advisory


def _airport(code, lat, lon, runway):
    return {'iata': code, 'icao': code, 'name': code, 'lat': lat, 'lon': lon, 'runway_ft': runway}


def _aircraft(**overrides):
    row = {
        'id': 1,
        'aircraft_name': 'Test Jet',
        'manufacturer': 'Test',
        'category': 'Jet',
        'passengers': 8,
        'range': 2000,
        'speed': 400,
        'runway_length': 3000,
        'total_hourly_cost': 1000,
        'hourly_variable_cost': 800,
        'price': 1000000,
    }
    row.update(overrides)
    return row


class CharterPlanTests(unittest.TestCase):
    def setUp(self):
        # About 400 nm at this latitude. Usable range is published range * 0.85.
        self.origin = _airport('AAA', 40.0, -100.0, 6000)
        self.near = _airport('BBB', 40.0, -92.0, 6000)
        self.mid = _airport('MMM', 40.0, -96.0, 6000)
        self.mid_two = _airport('NNN', 40.0, -94.0, 6000)
        self.close_a = _airport('CCC', 40.0, -98.2, 6000)
        self.close_b = _airport('DDD', 40.0, -95.4, 6000)
        self.runways = {'AAA': 6000, 'BBB': 6000, 'MMM': 6000, 'NNN': 6000, 'CCC': 6000, 'DDD': 6000, 'SHORT': 2000}

    def test_nonstop_when_range_covers_the_route(self):
        plan = advisory.plan_charter(
            self.origin, self.near, [_aircraft(range=2000)], [self.mid], self.runways, passengers=2,
        )
        self.assertTrue(plan['ok'])
        card = plan['suitable'][0]
        self.assertEqual(card['fuel_stops'], 0)
        self.assertEqual(card['stop_label'], 'Nonstop')
        self.assertEqual(len(card['points']), 2)
        self.assertTrue(card['confirmed_suitable'])
        self.assertEqual(card['hourly_charter_rate'], 1888)
        self.assertNotIn('commission_mid', card)
        self.assertNotIn('estimate_low', card)
        self.assertNotIn('estimate_high', card)
        self.assertIsNotNone(card['estimated_total'])
        self.assertEqual(plan['categories'][0]['name'], 'Test Jet')
        self.assertEqual(plan['categories'][0]['category_label'], 'Super light jet')
        self.assertTrue(plan['categories'][0]['best_available'])

    def test_one_fuel_stop_is_mapped(self):
        plan = advisory.plan_charter(
            self.origin, self.near, [_aircraft(range=450, id=2, aircraft_name='One Stop')],
            [self.mid], self.runways, passengers=2,
        )
        card = plan['suitable'][0]
        self.assertEqual(card['fuel_stops'], 1)
        self.assertEqual(card['stop_label'], '1 Fuel Stop Required')
        self.assertEqual([point['code'] for point in card['points']], ['AAA', 'MMM', 'BBB'])
        self.assertTrue(card['confirmed_suitable'])
        self.assertIn('fits the longest runway', card['runway_status'])

    def test_two_fuel_stops_are_mapped_and_three_are_excluded(self):
        airports = [self.close_a, self.close_b]
        two = advisory.plan_charter(
            self.origin, self.near, [_aircraft(range=200, id=3, aircraft_name='Two Stop')],
            airports, self.runways, passengers=2,
        )
        self.assertEqual(two['suitable'][0]['fuel_stops'], 2)
        self.assertEqual(len(two['suitable'][0]['points']), 4)
        too_far = advisory.plan_charter(
            self.origin, self.near, [_aircraft(range=90, id=4, aircraft_name='Too Far')],
            airports, self.runways, passengers=2,
        )
        self.assertEqual(too_far['unverified'], [])
        self.assertGreaterEqual(too_far['excluded']['stops'], 1)

    def test_too_few_seats_and_short_runway_are_not_suitable(self):
        plan = advisory.plan_charter(
            self.origin, self.near,
            [
                _aircraft(id=5, aircraft_name='Small', passengers=1),
                _aircraft(id=6, aircraft_name='Long Field', runway_length=9000),
            ],
            [self.mid], self.runways, passengers=4,
        )
        names = [row['name'] for row in plan['unverified']]
        self.assertNotIn('Small', names)
        self.assertNotIn('Long Field', names)
        self.assertEqual(plan['suitable'], [])
        self.assertGreaterEqual(plan['excluded']['seats'], 1)
        self.assertGreaterEqual(plan['excluded']['runway'], 1)

    def test_missing_class_is_not_priced(self):
        plan = advisory.plan_charter(
            self.origin, self.near, [_aircraft(category='Balloon', hourly_variable_cost=0, aircraft_name='No Rate')],
            [], self.runways, passengers=1,
        )
        self.assertIsNone(plan['suitable'][0]['estimated_total'])
        self.assertIn('not available for this aircraft', plan['suitable'][0]['price_note'])

    def test_price_is_variable_cost_times_class_factor_times_hours(self):
        import charter_pricing
        aircraft = _aircraft(category='Turboprop', hourly_variable_cost=2000, id=9)
        priced = charter_pricing.price_mission(aircraft, 2, fuel_stops=0, passengers=1, domestic=True)
        self.assertEqual(priced['hourly_rate'], 5500)
        self.assertEqual(priced['estimate_mid'], 11000)
        self.assertEqual(priced['status'], 'preliminary')

    def test_trip_price_uses_the_aircraft_speed_and_variable_cost(self):
        origin = {'iata': 'DFW', 'icao': 'KDFW', 'name': 'DFW', 'lat': 32.8968009949, 'lon': -97.0380020142, 'country': 'US', 'runway_ft': 13401}
        destination = {'iata': 'JFK', 'icao': 'KJFK', 'name': 'JFK', 'lat': 40.63980103, 'lon': -73.77890015, 'country': 'US', 'runway_ft': 14511}
        aircraft = _aircraft(id=21, aircraft_name='Sheet Jet', range=1900, speed=400, hourly_variable_cost=2500, passengers=7)
        plan = advisory.plan_charter(origin, destination, [aircraft], [], {'KDFW': 13401, 'KJFK': 14511}, passengers=1)
        card = plan['suitable'][0]
        hours = advisory._haversine(origin['lat'], origin['lon'], destination['lat'], destination['lon']) / 400
        self.assertAlmostEqual(card['flight_hours'], round(hours, 2), places=2)
        self.assertEqual(card['hourly_charter_rate'], 5900)
        self.assertEqual(card['estimated_total'], int(round((2500 * 2.36 * hours) / 100.0) * 100))

    def test_classes_follow_engine_and_range(self):
        import charter_pricing
        single = charter_pricing.charter_category({'category': 'Piston', 'multi_engine': 'No', 'range': 800})
        twin = charter_pricing.charter_category({'category': 'Turboprop', 'multi_engine': 'Yes', 'range': 1500})
        far = charter_pricing.charter_category({'category': 'Jet', 'range': 7500, 'passengers': 14})
        self.assertEqual(single, 'piston_single')
        self.assertEqual(twin, 'turboprop_multi')
        self.assertEqual(far, 'ultra_long')
        self.assertEqual(charter_pricing.CATEGORY_LABELS[far], 'Ultra-long range jet')

    def test_route_score_uses_the_purchase_equation(self):
        cheap = _aircraft(id=11, price=1000000, total_fixed_cost=80000, total_variable_cost=40000, aircraft_name='Cheap')
        costly = _aircraft(id=12, price=8000000, total_fixed_cost=400000, total_variable_cost=300000, aircraft_name='Costly')
        plan = advisory.plan_charter(self.origin, self.near, [cheap, costly], [], self.runways, passengers=1)
        scores = {card['name']: card['all_around_percent'] for card in plan['suitable']}
        self.assertIsNotNone(scores['Cheap'])
        self.assertGreater(scores['Cheap'], scores['Costly'])


if __name__ == '__main__':
    unittest.main()
