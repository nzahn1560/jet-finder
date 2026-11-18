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
        'charter_rate': 4000,
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
        self.assertEqual(plan['suitable'], [])
        self.assertEqual(plan['unverified'][0]['fuel_stops'], 0)
        self.assertEqual(plan['unverified'][0]['stop_label'], 'Nonstop')
        self.assertEqual(len(plan['unverified'][0]['points']), 2)
        self.assertGreater(plan['unverified'][0]['estimated_total'], 0)

    def test_one_fuel_stop_is_mapped(self):
        plan = advisory.plan_charter(
            self.origin, self.near, [_aircraft(range=450, id=2, aircraft_name='One Stop')],
            [self.mid], self.runways, passengers=2,
        )
        card = plan['unverified'][0]
        self.assertEqual(card['fuel_stops'], 1)
        self.assertEqual(card['stop_label'], '1 Fuel Stop Required')
        self.assertEqual([point['code'] for point in card['points']], ['AAA', 'MMM', 'BBB'])
        self.assertFalse(card['confirmed_suitable'])

    def test_two_fuel_stops_are_mapped_and_three_are_excluded(self):
        airports = [self.close_a, self.close_b]
        two = advisory.plan_charter(
            self.origin, self.near, [_aircraft(range=200, id=3, aircraft_name='Two Stop')],
            airports, self.runways, passengers=2,
        )
        self.assertEqual(two['unverified'][0]['fuel_stops'], 2)
        self.assertEqual(len(two['unverified'][0]['points']), 4)
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

    def test_missing_charter_rate_is_not_invented(self):
        plan = advisory.plan_charter(
            self.origin, self.near, [_aircraft(charter_rate=0, aircraft_name='No Rate')],
            [], self.runways, passengers=1,
        )
        self.assertIsNone(plan['unverified'][0]['estimated_total'])
        self.assertIn('not in the spreadsheet', plan['unverified'][0]['price_note'])


if __name__ == '__main__':
    unittest.main()
