"""Product checks for accounts, listings, price, brokers, scoring, and charter."""
import os
import tempfile
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

_DB = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
os.environ['DATABASE_URL'] = 'sqlite:///' + _DB.name
os.environ['FLASK_ENV'] = 'development'
os.environ['REQUIRE_PAYMENT_FOR_LISTINGS'] = 'false'
os.environ.pop('SECRET_KEY', None)

import pricing  # noqa: E402
from app import app  # noqa: E402
import db as db_module  # noqa: E402
import matching  # noqa: E402


class ProductTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        profiles = db_module.get_all_aircraft_profiles()
        cls.profile_id = profiles[0]['id']
        cls.seller = cls._signup('seller@example.com', 'seller-pass-1', 'seller')
        cls.buyer = cls._signup('buyer@example.com', 'buyer-pass-1', 'buyer')
        cls.broker = cls._signup('broker@example.com', 'broker-pass-1', 'broker')
        db_module.update_user_profile(cls.broker['id'], {'profile_role': 'broker'})
        cls.team_id = db_module.create_broker_team(cls.broker['id'], 'Northstar', 'Teterboro', 'NJ', active=True)
        cls.operator = cls._signup('operator@example.com', 'operator-pass-1', 'charter_operator')
        cls.admin = cls._signup('admin@example.com', 'admin-pass-1', 'seller')
        db_module.set_user_admin(cls.admin['id'], True)

    @classmethod
    def _signup(cls, email, password, role):
        response = cls.client.post('/api/auth/signup', json={
            'email': email,
            'password': password,
            'first_name': role.title(),
            'profile_role': role,
            'profile_location': 'KTEB',
        })
        body = response.get_json()
        assert response.status_code == 201, body
        return body['user']

    def setUp(self):
        self.client = app.test_client()

    def _login(self, email, password):
        response = self.client.post('/api/auth/login', json={'email': email, 'password': password})
        self.assertEqual(response.status_code, 200, response.get_json())
        return response

    def test_login_endpoint_is_registered_and_home_renders(self):
        from flask import url_for
        with app.test_request_context():
            self.assertEqual(url_for('login'), '/login')
        home = self.client.get('/')
        self.assertEqual(home.status_code, 200)
        page = self.client.get('/login')
        self.assertEqual(page.status_code, 200)

    def test_listing_fee_is_fifty_dollars(self):
        chicago = ZoneInfo('America/Chicago')
        promo = datetime(2026, 12, 31, 23, 59, tzinfo=chicago)
        after = datetime(2027, 1, 1, 0, 0, tzinfo=chicago)
        self.assertEqual(pricing.listing_price_cents(promo), 4999)
        self.assertEqual(pricing.listing_price_cents(after), 4999)
        self.assertEqual(pricing.listing_price()['amount_dollars'], 49.99)
        self.assertFalse(pricing.listing_price()['promotional'])

    def test_login_logout_and_wrong_password(self):
        bad = self.client.post('/api/auth/login', json={'email': 'buyer@example.com', 'password': 'nope-nope'})
        self.assertEqual(bad.status_code, 401)
        good = self._login('buyer@example.com', 'buyer-pass-1')
        me = self.client.get('/api/auth/me')
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.get_json()['user']['email'], 'buyer@example.com')
        self.client.post('/api/auth/logout')
        self.assertEqual(self.client.get('/api/auth/me').status_code, 401)
        self.assertIn('jet_session', good.headers.get('Set-Cookie', ''))

    def test_public_listing_hides_broker_inventory(self):
        self._login('seller@example.com', 'seller-pass-1')
        created = self.client.post('/api/listings', json=self._payload('Public Jet', 'public'))
        self.assertEqual(created.status_code, 201, created.get_json())
        public_id = created.get_json()['id']
        self._login('broker@example.com', 'broker-pass-1')
        hidden = self.client.post('/api/listings', json=self._payload('Quiet Jet', 'broker_only'))
        hidden_id = hidden.get_json()['id']
        db_module.admin_approve_listing_any(public_id, self.admin['id'])
        db_module.admin_approve_listing_any(hidden_id, self.admin['id'])
        ids = {row.get('id') for row in self.client.get('/api/user-listings').get_json()}
        self.assertIn(public_id, ids)
        self.assertNotIn(hidden_id, ids)
        page = self.client.get(f'/listing/{hidden_id}')
        self.assertEqual(page.status_code, 404)
        self.assertEqual(self.client.get(f'/listing/{public_id}').status_code, 200)

    def test_buyer_cannot_open_off_market_and_broker_can(self):
        self._login('buyer@example.com', 'buyer-pass-1')
        blocked = self.client.get('/off-market')
        self.assertEqual(blocked.status_code, 403)
        self.assertIn(b'Brokers only', blocked.data)
        self._login('broker@example.com', 'broker-pass-1')
        allowed = self.client.get('/off-market')
        self.assertEqual(allowed.status_code, 200)
        self.assertIn(b'Brokers only', allowed.data)

    def test_signup_does_not_grant_a_free_broker_account(self):
        created = self.client.post('/api/auth/signup', json={
            'email': 'new-broker@example.com',
            'password': 'broker-pass-1',
            'first_name': 'New',
            'profile_role': 'broker',
        })
        self.assertEqual(created.status_code, 201, created.get_json())
        self.assertEqual(created.get_json()['user']['profile_role'], 'buyer')
        self.assertTrue(created.get_json().get('broker_checkout_required'))
        blocked = self.client.get('/off-market')
        self.assertEqual(blocked.status_code, 403)
        checkout = self.client.post('/api/account/broker-checkout')
        self.assertEqual(checkout.status_code, 503)
        self.assertIn(b'$19.99 a month', checkout.data)
        self.assertIn(b'broker map', checkout.data)
        self.assertIn(b'off-market', checkout.data)

    def test_role_alone_does_not_open_off_market(self):
        labeled = self._signup('solo-label@example.com', 'broker-pass-1', 'seller')
        db_module.update_user_profile(labeled['id'], {'profile_role': 'broker'})
        self._login('solo-label@example.com', 'broker-pass-1')
        blocked = self.client.get('/off-market')
        self.assertEqual(blocked.status_code, 403)

    def test_team_admin_allows_a_broker_who_pays_nothing(self):
        self._login('buyer@example.com', 'buyer-pass-1')
        joined = self.client.post(f'/api/broker-teams/{self.team_id}/join')
        self.assertEqual(joined.status_code, 200, joined.get_json())
        self.assertEqual(joined.get_json().get('status'), 'pending')
        self.assertEqual(self.client.get('/off-market').status_code, 403)
        self._login('broker@example.com', 'broker-pass-1')
        allowed = self.client.post(f'/api/broker-teams/{self.team_id}/members/{self.buyer["id"]}/allow')
        self.assertEqual(allowed.status_code, 200, allowed.get_json())
        self._login('buyer@example.com', 'buyer-pass-1')
        page = self.client.get('/off-market')
        self.assertEqual(page.status_code, 200)
        detail = self.client.get(f'/api/broker-teams/{self.team_id}')
        names = [person.get('name') for person in detail.get_json().get('brokers', [])]
        self.assertIn('Buyer', names)
        checkout = self.client.post('/api/account/broker-checkout')
        self.assertEqual(checkout.status_code, 200)
        self.assertTrue(checkout.get_json().get('already'))

    def test_charter_and_mechanics_are_coming_soon(self):
        for path in ('/charter', '/charter-search', '/mechanics', '/charter/fleet'):
            page = self.client.get(path)
            self.assertEqual(page.status_code, 200, path)
            self.assertIn(b'Coming soon', page.data)

    def test_listing_market_is_public_or_broker_off_market(self):
        self._login('seller@example.com', 'seller-pass-1')
        page = self.client.get('/create-listing')
        self.assertEqual(page.status_code, 200)
        self.assertNotIn(b'value="private"', page.data)
        self.assertNotIn(b'Off market', page.data)
        private = self.client.post('/api/listings', json=self._payload('Private Jet', 'private'))
        self.assertEqual(private.status_code, 400, private.get_json())
        blocked = self.client.post('/api/listings', json=self._payload('Sneak Jet', 'broker_only'))
        self.assertEqual(blocked.status_code, 403, blocked.get_json())
        self._login('broker@example.com', 'broker-pass-1')
        broker_page = self.client.get('/create-listing')
        self.assertIn(b'Off market', broker_page.data)
        self.assertIn(b'For sale', broker_page.data)
        self.assertIn(b'Wanted', broker_page.data)
        self.assertNotIn(b'value="private"', broker_page.data)
        created = self.client.post('/api/listings', json=self._payload('Broker Quiet', 'broker_only'))
        self.assertEqual(created.status_code, 201, created.get_json())

    def test_off_market_listing_needs_only_name_profile_and_year(self):
        self._login('broker@example.com', 'broker-pass-1')
        created = self.client.post('/api/listings', json={
            'profile_id': self.profile_id,
            'title': 'Quiet Name',
            'year': 2016,
            'market': 'broker_only',
        })
        self.assertEqual(created.status_code, 201, created.get_json())
        row = db_module.get_listing_with_owner(created.get_json()['id'])
        self.assertEqual(row['title'], 'Quiet Name')
        self.assertEqual(row['year'], 2016)
        self.assertEqual(row.get('listing_intent') or 'sale', 'sale')
        wanted = self.client.post('/api/listings', json={
            'profile_id': self.profile_id,
            'title': 'Looking For',
            'year': 2018,
            'market': 'broker_only',
            'listing_intent': 'wanted',
        })
        self.assertEqual(wanted.status_code, 201, wanted.get_json())
        wanted_row = db_module.get_listing_with_owner(wanted.get_json()['id'])
        self.assertEqual(wanted_row['listing_intent'], 'wanted')
        rejected = self.client.post('/api/listings', json={
            'profile_id': self.profile_id,
            'title': 'Neither',
            'year': 2018,
            'market': 'broker_only',
            'listing_intent': 'lease',
        })
        self.assertEqual(rejected.status_code, 400)
        opened = self.client.get('/off-market')
        self.assertIn(b'For sale', opened.data)
        self.assertIn(b'Wanted', opened.data)

    def test_editing_a_live_listing_is_sent_back_as_an_amendment(self):
        self._login('seller@example.com', 'seller-pass-1')
        created = self.client.post('/api/listings', json=self._payload('Amend Jet', 'public'))
        listing_id = created.get_json()['id']
        db_module.admin_approve_listing_any(listing_id, self.admin['id'])
        patched = self.client.patch(f'/api/listings/{listing_id}', json={'price': 1800000})
        self.assertEqual(patched.status_code, 200, patched.get_json())
        note = patched.get_json().get('amendment') or ''
        self.assertIn('Amendment', note)
        self.assertIn('Price', note)
        row = db_module.get_listing_with_owner(listing_id)
        self.assertEqual(row['status'], 'pending')
        self.assertIn('Price', row.get('amendment_note') or '')

    def test_public_profile_hides_edit_from_visitors(self):
        visitor = self.client.get(f"/people/{self.buyer['id']}")
        self.assertEqual(visitor.status_code, 200)
        self.assertNotIn(b'Member since', visitor.data)
        self.assertNotIn(b'id="open-profile-edit"', visitor.data)
        self._login('buyer@example.com', 'buyer-pass-1')
        owner = self.client.get(f"/people/{self.buyer['id']}")
        self.assertIn(b'id="open-profile-edit"', owner.data)
        self.assertIn(b'id="profile-edit"', owner.data)
        self.assertIn(b'hidden', owner.data)

    def test_owner_cannot_edit_someone_elses_listing(self):
        self._login('seller@example.com', 'seller-pass-1')
        created = self.client.post('/api/listings', json=self._payload('Owned Jet', 'public'))
        listing_id = created.get_json()['id']
        self._login('buyer@example.com', 'buyer-pass-1')
        patched = self.client.patch(f'/api/listings/{listing_id}', json={'price': 1})
        self.assertEqual(patched.status_code, 403)

    def test_buyer_cannot_open_admin_and_admin_can_approve_own_listing(self):
        self._login('buyer@example.com', 'buyer-pass-1')
        self.assertEqual(self.client.get('/api/admin/listings').status_code, 403)
        self._login('admin@example.com', 'admin-pass-1')
        created = self.client.post('/api/listings', json=self._payload('Admin Jet', 'public'))
        listing_id = created.get_json()['id']
        approved = self.client.post(f'/api/admin/listings/{listing_id}/approve')
        self.assertEqual(approved.status_code, 200, approved.get_json())
        self.assertEqual(approved.get_json()['status'], 'active')

    def test_admin_can_approve_a_broker_and_a_watch_creates_an_alert(self):
        created = self.client.post('/api/auth/signup', json={
            'email': 'apply-broker@example.com',
            'password': 'broker-pass-1',
            'first_name': 'Apply',
            'profile_role': 'broker',
        })
        applicant_id = created.get_json()['user']['id']
        self.assertEqual(created.get_json()['user']['broker_application_status'], 'pending')
        self._login('buyer@example.com', 'buyer-pass-1')
        self.assertEqual(self.client.post(f'/api/admin/brokers/{applicant_id}/approve').status_code, 403)
        self._login('admin@example.com', 'admin-pass-1')
        approved = self.client.post(f'/api/admin/brokers/{applicant_id}/approve')
        self.assertEqual(approved.status_code, 200, approved.get_json())
        person = db_module.get_user_by_id(applicant_id)
        self.assertEqual(person['profile_role'], 'broker')
        self.assertEqual(person['broker_application_status'], 'approved')
        queue = self.client.get('/api/admin/approvals')
        self.assertEqual(queue.status_code, 200)
        self._login('seller@example.com', 'seller-pass-1')
        listing = self.client.post('/api/listings', json=self._payload('Watched Jet', 'public'))
        listing_id = listing.get_json()['id']
        self._login('buyer@example.com', 'buyer-pass-1')
        saved = self.client.post('/api/profile/saved', json={
            'kind': 'listing', 'target_id': listing_id, 'title': 'Watched Jet',
        })
        self.assertEqual(saved.status_code, 201, saved.get_json())
        public = self.client.get(f'/people/{self.seller["id"]}')
        self.assertEqual(public.status_code, 200)
        self.assertIn(b'Aircraft for sale', public.data)
        self.assertNotIn(b'id="open-profile-edit"', public.data)
        self._login('seller@example.com', 'seller-pass-1')
        notes = self.client.get('/api/notifications')
        self.assertEqual(notes.status_code, 200)
        titles = [note['title'] for note in notes.get_json()['notifications']]
        self.assertIn('Someone is watching your listing', titles)

    def test_admin_review_compares_aircraft_data_and_keeps_a_fix_message_pending(self):
        self._login('seller@example.com', 'seller-pass-1')
        created = self.client.post('/api/listings', json=self._payload('Review Jet', 'public'))
        listing_id = created.get_json()['id']
        self._login('buyer@example.com', 'buyer-pass-1')
        self.assertEqual(self.client.get(f'/api/admin/listings/{listing_id}/review').status_code, 403)
        self._login('admin@example.com', 'admin-pass-1')
        review = self.client.get(f'/api/admin/listings/{listing_id}/review')
        self.assertEqual(review.status_code, 200, review.get_json())
        body = review.get_json()
        self.assertEqual(body['listing']['price'], 2500000)
        self.assertIn('price', body['aircraft_data'])
        self.assertTrue(body['checks'])
        sent = self.client.post(
            f'/api/admin/listings/{listing_id}/message',
            json={'message': 'Add the serial number.'},
        )
        self.assertEqual(sent.status_code, 200, sent.get_json())
        self.assertEqual(sent.get_json()['status'], 'pending')
        row = db_module.get_listing_with_owner(listing_id)
        self.assertEqual(row['status'], 'pending')
        self.assertIn('serial', row.get('review_message') or '')
        self._login('seller@example.com', 'seller-pass-1')
        mine = self.client.get('/api/listings/me')
        self.assertEqual(mine.status_code, 200)
        found = next(item for item in mine.get_json()['listings'] if item['id'] == listing_id)
        self.assertIn('serial', found.get('review_message') or '')

    def test_reject_then_resubmit_does_not_require_a_second_payment(self):
        self._login('seller@example.com', 'seller-pass-1')
        created = self.client.post('/api/listings', json=self._payload('Rejected Jet', 'public'))
        listing_id = created.get_json()['id']
        db_module.admin_reject_listing_any(listing_id, 'Need the serial number')
        with db_module.get_session() as session:
            session.query(db_module.UserListing).filter(db_module.UserListing.id == listing_id).update(
                {'payment_status': 'paid'}, synchronize_session=False
            )
        again = self.client.post(f'/api/listings/{listing_id}/resubmit')
        self.assertEqual(again.status_code, 200, again.get_json())
        self.assertFalse(again.get_json()['charged_again'])
        self.assertEqual(again.get_json()['status'], 'pending')

    def test_turning_paint_off_changes_the_rank(self):
        cards = [
            {'id': 1, 'title': 'Fresh', 'price': 100, 'year': 2018, 'hours': 500, 'range': 2000,
             'passengers': 6, 'speed': 400, 'paint_year': 2024, 'engine_hours': 400, 'avionics': 'G3000'},
            {'id': 2, 'title': 'Older paint', 'price': 100, 'year': 2018, 'hours': 500, 'range': 2000,
             'passengers': 6, 'speed': 400, 'paint_year': 1998, 'engine_hours': 400, 'avionics': 'G3000'},
        ]
        prefs = {'range_nm': 500, 'passengers': 2, 'weights': {key: True for key in matching.COMPONENTS}}
        with_paint = matching.rank_listings(cards, prefs)['results']
        prefs['weights']['paint'] = False
        without = matching.rank_listings(cards, prefs)['results']
        self.assertNotEqual(with_paint[0]['scores']['paint'], with_paint[1]['scores']['paint'])
        self.assertNotIn('paint', without[0]['used'])
        too_far = matching.rank_listings(cards, {'range_nm': 5000, 'weights': prefs['weights']})
        self.assertEqual(too_far['results'], [])
        self.assertEqual(len(too_far['excluded']), 2)

    def test_charter_request_is_not_confirmed_until_operator_accepts(self):
        self._login('operator@example.com', 'operator-pass-1')
        operator_id = db_module.ensure_charter_operator(self.operator['id'], 'Operator Air', email='operator@example.com')
        db_module.create_charter_aircraft(operator_id, {
            'name': 'Citation CJ3', 'registration': 'N100JS', 'base_airport': 'KTEB',
            'seats': 7, 'hourly_rate': 3200, 'range_nm': 1800, 'speed_kts': 400,
        })
        available = self.client.get('/api/charter/available?departure=JFK&arrival=MIA&passengers=2&date=2026-11-01')
        aircraft = available.get_json()['aircraft']
        self.assertTrue(aircraft)
        booked = self.client.post('/api/charter/book', json={
            'aircraft_id': aircraft[0]['id'],
            'name': 'Pat Buyer',
            'email': 'pat@example.com',
            'departure_airport': 'JFK',
            'arrival_airport': 'MIA',
            'departure_date': '2026-11-01',
            'passengers': 2,
        })
        self.assertEqual(booked.status_code, 201)
        self.assertEqual(booked.get_json()['status'], 'requested')
        booking_id = booked.get_json()['id']
        accepted = self.client.post(f'/api/charter/bookings/{booking_id}/status', json={'status': 'confirmed'})
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(db_module.get_charter_booking(booking_id)['status'], 'confirmed')

    def test_airport_search_includes_longest_runway(self):
        found = self.client.get('/api/airports?q=TEB')
        self.assertEqual(found.status_code, 200)
        airports = found.get_json()
        teb = next(item for item in airports if item.get('iata') == 'TEB')
        self.assertEqual(teb['longest_runway_ft'], 6997)

    def test_hidden_listing_media_and_spreadsheet_stay_private(self):
        self._login('broker@example.com', 'broker-pass-1')
        created = self.client.post('/api/listings', json=self._payload('Hidden Media Jet', 'broker_only'))
        listing_id = created.get_json()['id']
        self._login('buyer@example.com', 'buyer-pass-1')
        hidden = self.client.get(f'/api/listings/{listing_id}/media')
        self.assertEqual(hidden.status_code, 404)
        sheet = self.client.get('/api/aircraft-data')
        self.assertEqual(sheet.status_code, 404)
        self._login('broker@example.com', 'broker-pass-1')
        owner = self.client.get(f'/api/listings/{listing_id}/media')
        self.assertEqual(owner.status_code, 200)
        page = self.client.get('/')
        self.assertIn(b'function escCard', page.data)
        self.assertIn(b'seller-notes', page.data)
        self.assertIn(b'inc. 1 pilot seat', page.data)
        self.assertIn(b'(one-way)', page.data)
        self.assertIn(b'If chartered', page.data)
        self.assertNotIn(b'Cost To Charter', page.data)
        self.assertIn(b'Choose what you want to compare.', page.data)
        self.assertNotIn(b'Independent scale per metric', page.data)
        self.assertIn(b'I understand', page.data)
        self.assertIn(b'Min Crew Required', page.data)
        self.assertIn(b'Best Speed/$', page.data)
        self.assertIn(b'refreshListingNumbers', page.data)
        self.assertNotIn(b'Column AN', page.data)
        self.assertNotIn(b'Normalized Speed', page.data)

    def test_unpaid_checkout_does_not_mark_a_listing_paid(self):
        self._login('seller@example.com', 'seller-pass-1')
        created = self.client.post('/api/listings', json=self._payload('Unpaid Jet', 'public'))
        listing_id = created.get_json()['id']
        db_module.set_listing_payment_session(listing_id, 'cs_test_unpaid')
        unpaid = self.client.post('/api/stripe/webhook', json={
            'id': 'evt_unpaid_1',
            'type': 'checkout.session.completed',
            'data': {'object': {'id': 'cs_test_unpaid', 'payment_status': 'unpaid', 'metadata': {}}},
        })
        self.assertEqual(unpaid.status_code, 200, unpaid.get_json())
        self.assertTrue(unpaid.get_json().get('pending'))
        row = db_module.get_listing_with_owner(listing_id)
        self.assertNotEqual(row.get('payment_status'), 'paid')
        paid = self.client.post('/api/stripe/webhook', json={
            'id': 'evt_paid_1',
            'type': 'checkout.session.async_payment_succeeded',
            'data': {'object': {'id': 'cs_test_unpaid', 'payment_status': 'paid', 'metadata': {}}},
        })
        self.assertEqual(paid.status_code, 200, paid.get_json())
        row = db_module.get_listing_with_owner(listing_id)
        self.assertEqual(row.get('payment_status'), 'paid')
        self.assertEqual(row.get('status'), 'pending')

    def test_production_webhook_without_a_secret_is_refused(self):
        import os
        os.environ['FLASK_ENV'] = 'production'
        os.environ.pop('STRIPE_WEBHOOK_SECRET', None)
        try:
            refused = self.client.post('/api/stripe/webhook', data=b'{}', content_type='application/json')
            self.assertEqual(refused.status_code, 500)
        finally:
            os.environ['FLASK_ENV'] = 'development'
            os.environ.pop('STRIPE_WEBHOOK_SECRET', None)

    def test_refunds_page_matches_the_terms(self):
        page = self.client.get('/refunds')
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'non-refundable once a listing has been approved and published', page.data)
        self.assertIn(b'not a promise that a refund will be issued', page.data)
        terms = self.client.get('/terms')
        self.assertIn(b'href="/refunds"', terms.data)

    def test_contact_message_reaches_admin_alerts(self):
        page = self.client.get('/contact')
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'Contact', page.data)
        token = page.data.split(b'name="csrf-token" content="', 1)[1].split(b'"', 1)[0].decode()
        sent = self.client.post('/api/contact', json={
            'name': 'Ada Buyer',
            'email': 'ada@example.com',
            'phone': '555-0100',
            'message': 'I would like to ask about a listing.',
        }, headers={'X-CSRF-Token': token})
        self.assertEqual(sent.status_code, 200, sent.get_json())
        self._login('buyer@example.com', 'buyer-pass-1')
        hidden = self.client.get('/api/admin/contacts')
        self.assertEqual(hidden.status_code, 403)
        self._login('admin@example.com', 'admin-pass-1')
        inbox = self.client.get('/api/admin/contacts')
        self.assertEqual(inbox.status_code, 200)
        messages = inbox.get_json()['messages']
        self.assertTrue(any(row['email'] == 'ada@example.com' for row in messages))
        notes = self.client.get('/api/notifications')
        titles = [note['title'] for note in notes.get_json()['notifications']]
        self.assertIn('Contact from Ada Buyer', titles)

    def test_robots_and_sitemap_skip_private_listings(self):
        self._login('seller@example.com', 'seller-pass-1')
        public = self.client.post('/api/listings', json=self._payload('Sitemap Public', 'public'))
        public_id = public.get_json()['id']
        self._login('broker@example.com', 'broker-pass-1')
        hidden = self.client.post('/api/listings', json=self._payload('Sitemap Quiet', 'broker_only'))
        hidden_id = hidden.get_json()['id']
        db_module.admin_approve_listing_any(public_id, self.admin['id'])
        db_module.admin_approve_listing_any(hidden_id, self.admin['id'])
        robots = self.client.get('/robots.txt')
        self.assertEqual(robots.status_code, 200)
        self.assertIn(b'Disallow: /off-market', robots.data)
        self.assertIn(b'Disallow: /api/', robots.data)
        self.assertIn(b'Sitemap:', robots.data)
        sitemap = self.client.get('/sitemap.xml')
        self.assertEqual(sitemap.status_code, 200)
        self.assertIn(f'/listing/{public_id}'.encode(), sitemap.data)
        self.assertNotIn(f'/listing/{hidden_id}'.encode(), sitemap.data)
        self.assertNotIn(b'/off-market', sitemap.data)
        self.assertNotIn(b'/admin', sitemap.data)

    def test_public_diagnostics_omit_account_counts(self):
        for path in ('/api/health', '/api/data-safety', '/api/data-source', '/api/diagnostic'):
            body = self.client.get(path).get_data()
            self.assertNotIn(b'user_sessions', body)
            self.assertNotIn(b'"users"', body)
            self.assertNotIn(b'table_counts', body)
            self.assertNotIn(b'connection_error', body)
            self.assertNotIn(b'app_root', body)

    def test_logout_requires_a_post_and_csrf_token(self):
        self._login('buyer@example.com', 'buyer-pass-1')
        page = self.client.get('/logout')
        self.assertEqual(page.status_code, 200)
        self.assertEqual(self.client.get('/api/auth/me').status_code, 200)
        blocked = self.client.post('/logout', data={'csrf_token': 'not-the-token'})
        self.assertEqual(blocked.status_code, 400)
        self.assertEqual(self.client.get('/api/auth/me').status_code, 200)
        import re
        token = re.search(br'name="csrf_token" value="([^"]+)"', page.data).group(1)
        done = self.client.post('/logout', data={'csrf_token': token.decode()})
        self.assertEqual(done.status_code, 302)
        self.assertEqual(self.client.get('/api/auth/me').status_code, 401)
        cross = self.client.post('/api/auth/login', json={'email': 'buyer@example.com', 'password': 'buyer-pass-1'})
        self.assertEqual(cross.status_code, 200)
        foreign = self.client.post('/api/auth/logout', headers={'Origin': 'https://evil.example'})
        self.assertEqual(foreign.status_code, 403)
        self.assertEqual(self.client.get('/api/auth/me').status_code, 200)

    def test_production_rate_limit_is_shared_across_clients(self):
        for _ in range(10):
            self.assertFalse(db_module.consume_auth_rate('shared-test-bucket', limit=10, window_seconds=60))
        self.assertTrue(db_module.consume_auth_rate('shared-test-bucket', limit=10, window_seconds=60))
        os.environ['FLASK_ENV'] = 'production'
        try:
            for _ in range(10):
                attempt = self.client.post('/api/auth/login', json={
                    'email': 'buyer@example.com', 'password': 'wrong-password',
                })
                self.assertEqual(attempt.status_code, 401)
            blocked = self.client.post('/api/auth/login', json={
                'email': 'buyer@example.com', 'password': 'wrong-password',
            })
            self.assertEqual(blocked.status_code, 429)
            other = app.test_client()
            again = other.post('/api/auth/login', json={
                'email': 'buyer@example.com', 'password': 'wrong-password',
            })
            self.assertEqual(again.status_code, 429)
        finally:
            os.environ['FLASK_ENV'] = 'development'

    def test_settled_stripe_refund_updates_payment_status_only(self):
        self._login('seller@example.com', 'seller-pass-1')
        created = self.client.post('/api/listings', json=self._payload('Refund Jet', 'public'))
        listing_id = created.get_json()['id']
        db_module.admin_approve_listing_any(listing_id, self.admin['id'])
        with db_module.get_session() as session:
            session.query(db_module.UserListing).filter(db_module.UserListing.id == listing_id).update(
                {'payment_status': 'paid', 'stripe_payment_intent_id': 'pi_refund_full'},
                synchronize_session=False,
            )
        pending = self.client.post('/api/stripe/webhook', json={
            'id': 'evt_refund_pending',
            'type': 'refund.updated',
            'data': {'object': {
                'object': 'refund', 'status': 'pending', 'amount': 1499,
                'payment_intent': 'pi_refund_full',
            }},
        })
        self.assertEqual(pending.status_code, 200)
        row = db_module.get_listing_with_owner(listing_id)
        self.assertEqual(row['payment_status'], 'paid')
        self.assertEqual(row['status'], 'active')
        full = self.client.post('/api/stripe/webhook', json={
            'id': 'evt_refund_full',
            'type': 'charge.refunded',
            'data': {'object': {
                'object': 'charge', 'amount': 1499, 'amount_refunded': 1499,
                'refunded': True, 'payment_intent': 'pi_refund_full', 'status': 'succeeded',
            }},
        })
        self.assertEqual(full.status_code, 200)
        row = db_module.get_listing_with_owner(listing_id)
        self.assertEqual(row['payment_status'], 'refunded')
        self.assertEqual(row['status'], 'active')
        created = self.client.post('/api/listings', json=self._payload('Partial Jet', 'public'))
        partial_id = created.get_json()['id']
        db_module.admin_approve_listing_any(partial_id, self.admin['id'])
        with db_module.get_session() as session:
            session.query(db_module.UserListing).filter(db_module.UserListing.id == partial_id).update(
                {'payment_status': 'paid', 'stripe_payment_intent_id': 'pi_refund_part'},
                synchronize_session=False,
            )
        part = self.client.post('/api/stripe/webhook', json={
            'id': 'evt_refund_part',
            'type': 'charge.refunded',
            'data': {'object': {
                'object': 'charge', 'amount': 1499, 'amount_refunded': 500,
                'refunded': False, 'payment_intent': 'pi_refund_part',
            }},
        })
        self.assertEqual(part.status_code, 200)
        row = db_module.get_listing_with_owner(partial_id)
        self.assertEqual(row['payment_status'], 'partially_refunded')
        self.assertEqual(row['status'], 'active')
        unmatched = self.client.post('/api/stripe/webhook', json={
            'id': 'evt_refund_unknown',
            'type': 'charge.refunded',
            'data': {'object': {
                'object': 'charge', 'amount': 1499, 'amount_refunded': 1499,
                'refunded': True, 'payment_intent': 'pi_does_not_exist',
            }},
        })
        self.assertEqual(unmatched.status_code, 200)
        self.assertEqual(unmatched.get_json(), {'received': True})

    def test_duplicate_stripe_event_is_ignored(self):
        self.assertTrue(db_module.claim_stripe_event('evt_test_once'))
        self.assertFalse(db_module.claim_stripe_event('evt_test_once'))

    def _paid_broker(self, email, subscription_id, kind='broker'):
        person = self._signup(email, 'broker-pass-1', 'seller')
        db_module.update_user_profile(person['id'], {'profile_role': 'broker'})
        db_module.set_broker_application(person['id'], 'approved')
        db_module.update_user_subscription(
            person['id'], kind,
            stripe_customer_id='cus_' + subscription_id,
            stripe_subscription_id=subscription_id,
            subscription_status='active',
        )
        return person

    def _stripe_event(self, event_id, event_type, obj):
        return self.client.post('/api/stripe/webhook', json={
            'id': event_id,
            'type': event_type,
            'data': {'object': obj},
        })

    def test_cancelled_broker_subscription_closes_off_market(self):
        person = self._paid_broker('cancel-broker@example.com', 'sub_cancel_broker')
        self._login(person['email'], 'broker-pass-1')
        self.assertEqual(self.client.get('/off-market').status_code, 200)
        kept = self._stripe_event('evt_sub_still_active', 'customer.subscription.updated', {
            'id': 'sub_cancel_broker', 'object': 'subscription', 'status': 'active',
            'cancel_at_period_end': True, 'customer': 'cus_sub_cancel_broker',
        })
        self.assertEqual(kept.status_code, 200, kept.get_json())
        self.assertEqual(self.client.get('/off-market').status_code, 200)
        failed = self._stripe_event('evt_sub_past_due', 'invoice.payment_failed', {
            'object': 'invoice', 'subscription': 'sub_cancel_broker', 'customer': 'cus_sub_cancel_broker',
        })
        self.assertEqual(failed.status_code, 200, failed.get_json())
        self.assertEqual(self.client.get('/off-market').status_code, 200)
        restored = self._stripe_event('evt_sub_paid_again', 'invoice.paid', {
            'object': 'invoice', 'subscription': 'sub_cancel_broker', 'customer': 'cus_sub_cancel_broker',
        })
        self.assertEqual(restored.status_code, 200, restored.get_json())
        self.assertEqual(db_module.get_user_subscription(person['id'], 'broker')['subscription_status'], 'active')
        ended = self._stripe_event('evt_sub_deleted', 'customer.subscription.deleted', {
            'id': 'sub_cancel_broker', 'object': 'subscription', 'status': 'canceled',
            'customer': 'cus_sub_cancel_broker',
        })
        self.assertEqual(ended.status_code, 200, ended.get_json())
        self.assertEqual(self.client.get('/off-market').status_code, 403)
        unrelated = self._stripe_event('evt_sub_other', 'customer.subscription.deleted', {
            'id': 'sub_someone_else', 'object': 'subscription', 'status': 'canceled',
        })
        self.assertEqual(unrelated.status_code, 200, unrelated.get_json())

    def test_cancelled_team_subscription_closes_members(self):
        leader = self._paid_broker('team-lead-cancel@example.com', 'sub_team_cancel', kind='broker_team')
        team_id = db_module.create_broker_team(leader['id'], 'Cancel Co', 'Dallas', 'TX', active=True)
        member = self._signup('team-member-cancel@example.com', 'broker-pass-1', 'buyer')
        self._login(member['email'], 'broker-pass-1')
        self.assertEqual(self.client.post(f'/api/broker-teams/{team_id}/join').status_code, 200)
        self._login(leader['email'], 'broker-pass-1')
        allowed = self.client.post(f"/api/broker-teams/{team_id}/members/{member['id']}/allow")
        self.assertEqual(allowed.status_code, 200, allowed.get_json())
        self._login(member['email'], 'broker-pass-1')
        self.assertEqual(self.client.get('/off-market').status_code, 200)
        ended = self._stripe_event('evt_team_deleted', 'customer.subscription.deleted', {
            'id': 'sub_team_cancel', 'object': 'subscription', 'status': 'canceled',
            'customer': 'cus_sub_team_cancel', 'metadata': {'purpose': 'broker_team', 'team_id': str(team_id)},
        })
        self.assertEqual(ended.status_code, 200, ended.get_json())
        self.assertEqual(self.client.get('/off-market').status_code, 403)
        self.assertEqual(db_module.get_broker_team(team_id)['subscription_status'], 'inactive')

    def test_listing_dispute_does_not_unpublish_or_close_a_broker(self):
        person = self._paid_broker('dispute-broker@example.com', 'sub_dispute_broker')
        self._login('seller@example.com', 'seller-pass-1')
        created = self.client.post('/api/listings', json=self._payload('Disputed Jet', 'public'))
        listing_id = created.get_json()['id']
        db_module.admin_approve_listing_any(listing_id, self.admin['id'])
        with db_module.get_session() as session:
            session.query(db_module.UserListing).filter(db_module.UserListing.id == listing_id).update(
                {'payment_status': 'paid', 'stripe_payment_intent_id': 'pi_dispute_listing'},
                synchronize_session=False,
            )
        opened = self._stripe_event('evt_dispute_open', 'charge.dispute.created', {
            'object': 'dispute', 'status': 'needs_response', 'payment_intent': 'pi_dispute_listing',
        })
        self.assertEqual(opened.status_code, 200, opened.get_json())
        row = db_module.get_listing_with_owner(listing_id)
        self.assertEqual(row['payment_status'], 'disputed')
        self.assertEqual(row['status'], 'active')
        won = self._stripe_event('evt_dispute_won', 'charge.dispute.closed', {
            'object': 'dispute', 'status': 'won', 'payment_intent': 'pi_dispute_listing',
        })
        self.assertEqual(won.status_code, 200, won.get_json())
        self.assertEqual(db_module.get_listing_with_owner(listing_id)['payment_status'], 'paid')
        self._login(person['email'], 'broker-pass-1')
        self.assertEqual(self.client.get('/off-market').status_code, 200)

    def test_refunded_broker_charge_ends_access(self):
        person = self._paid_broker('refund-broker@example.com', 'sub_refund_broker')
        self._login(person['email'], 'broker-pass-1')
        refunded = self._stripe_event('evt_broker_refund', 'charge.refunded', {
            'object': 'charge', 'amount': 2000, 'amount_refunded': 2000, 'refunded': True,
            'payment_intent': 'pi_broker_refund',
            'invoice': {'subscription': 'sub_refund_broker'},
        })
        self.assertEqual(refunded.status_code, 200, refunded.get_json())
        self.assertEqual(self.client.get('/off-market').status_code, 403)

    def test_billing_portal_needs_a_subscription_and_stripe(self):
        self._login('buyer@example.com', 'buyer-pass-1')
        missing = self.client.post('/api/account/billing-portal')
        self.assertEqual(missing.status_code, 404)
        person = self._paid_broker('portal-broker@example.com', 'sub_portal_broker')
        self._login(person['email'], 'broker-pass-1')
        unavailable = self.client.post('/api/account/billing-portal')
        self.assertEqual(unavailable.status_code, 503)
        page = self.client.get('/dashboard')
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'Manage billing', page.data)

    def test_listing_fee_ignores_a_client_supplied_amount(self):
        from app import _listing_fee_cents
        self.assertEqual(_listing_fee_cents(), pricing.listing_price_cents())
        self._login('seller@example.com', 'seller-pass-1')
        created = self.client.post('/api/listings', json=self._payload('Fee Jet', 'public'))
        listing_id = created.get_json()['id']
        checkout = self.client.post(f'/api/listings/{listing_id}/checkout', json={'amount': 1, 'amount_cents': 1})
        self.assertEqual(checkout.status_code, 200)
        self.assertTrue(checkout.get_json().get('skip'))

    def test_approved_broker_gets_off_market_and_the_map(self):
        person = self._signup('map-broker@example.com', 'broker-pass-1', 'seller')
        db_module.update_user_profile(person['id'], {'first_name': 'Mapbroker', 'profile_location': 'KTEB'})
        self._login('admin@example.com', 'admin-pass-1')
        approved = self.client.post(f"/api/admin/brokers/{person['id']}/approve")
        self.assertEqual(approved.status_code, 200, approved.get_json())
        directory = self.client.get('/brokers')
        self.assertEqual(directory.status_code, 200)
        self.assertIn(b'Mapbroker', directory.data)
        self.assertIn(b'airport code', directory.data)
        self.assertIn(b'team.iata', directory.data)
        self._login('map-broker@example.com', 'broker-pass-1')
        opened = self.client.get('/off-market')
        self.assertEqual(opened.status_code, 200)
        listed = self.client.post('/api/listings', json=self._payload('Quiet Map Jet', 'broker_only'))
        self.assertEqual(listed.status_code, 201, listed.get_json())
        self._login('seller@example.com', 'seller-pass-1')
        blocked = self.client.post('/api/listings', json=self._payload('Seller Off Market', 'broker_only'))
        self.assertEqual(blocked.status_code, 403)

    def test_buyer_can_send_a_broker_a_request_and_a_listing(self):
        self._login('buyer@example.com', 'buyer-pass-1')
        missing = self.client.post(f"/api/brokers/{self.seller['id']}/messages", json={
            'kind': 'request', 'aircraft_name': 'Citation', 'notes': 'Looking now',
        })
        self.assertEqual(missing.status_code, 404)
        self._login('seller@example.com', 'seller-pass-1')
        created = self.client.post('/api/listings', json=self._payload('Shared Jet', 'public'))
        listing_id = created.get_json()['id']
        db_module.admin_approve_listing_any(listing_id, self.admin['id'])
        saved = self.client.patch('/api/profile', json={'broker_bio': 'x' * 1001})
        self.assertEqual(saved.status_code, 200, saved.get_json())
        self.assertEqual(len(self.client.get('/api/profile').get_json()['user']['broker_bio']), 1000)
        db_module.set_broker_application(self.broker['id'], 'approved')
        self._login('buyer@example.com', 'buyer-pass-1')
        request_note = self.client.post(f"/api/brokers/{self.broker['id']}/messages", json={
            'kind': 'request', 'aircraft_name': 'Citation Latitude', 'notes': 'Seats for six',
        })
        self.assertEqual(request_note.status_code, 201, request_note.get_json())
        listing_note = self.client.post(f"/api/brokers/{self.broker['id']}/messages", json={
            'kind': 'listing', 'listing_id': listing_id, 'notes': 'Please take a look',
        })
        self.assertEqual(listing_note.status_code, 201, listing_note.get_json())
        page = self.client.get(f'/listing/{listing_id}')
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'Range (seats full)', page.data)
        self.assertIn(b'showroom', page.data)
        self.assertIn(b'Seller notes', page.data)
        self.assertIn(b'showroom-prev', page.data)
        self._login('broker@example.com', 'broker-pass-1')
        inbox = self.client.get('/api/broker/messages')
        self.assertEqual(inbox.status_code, 200)
        kinds = {row['kind'] for row in inbox.get_json()['inbox']}
        self.assertIn('request', kinds)
        self.assertIn('listing', kinds)

    def _payload(self, title, market):
        return {
            'profile_id': self.profile_id,
            'title': title,
            'price': 2500000,
            'location': 'KTEB',
            'email': 'seller@example.com',
            'year': 2018,
            'hours': 900,
            'description': 'Test aircraft',
            'market': market,
            'engine_hours': 700,
            'paint_year': 2020,
            'avionics': 'G1000',
        }


if __name__ == '__main__':
    unittest.main()
