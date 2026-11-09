"""Product checks for accounts, listings, price, brokers, scoring, and charter."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
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
        self.assertIn(b'Compare Private Aircraft by Cost and Range | JetSchool', home.data)
        self.assertNotIn(b'Compare private aircraft by cost, range, and route', home.data)
        self.assertNotIn(b'The figures are estimates. Confirm range, price, and operating cost before you buy.', home.data)
        self.assertIn(b'rel="canonical" href="http://localhost/"', home.data)
        self.assertIn(b'WebApplication', home.data)
        self.assertIn(b'jetfinder_route_add', home.data)
        self.assertNotIn(b'noindex', home.data)
        filtered = self.client.get('/?budget=5000000')
        self.assertIn(b'noindex, follow', filtered.data)
        self.assertIn(b'rel="canonical" href="http://localhost/"', filtered.data)
        alias = self.client.get('/jet-finder')
        self.assertEqual(alias.status_code, 301)
        self.assertEqual(alias.headers.get('Location'), '/')
        page = self.client.get('/login')
        self.assertEqual(page.status_code, 200)

    def test_favicon_is_linked_and_crawlable(self):
        from io import BytesIO
        from PIL import Image
        for path in ('/', '/brokers', '/contact', '/no-such-favicon-page'):
            page = self.client.get(path)
            self.assertIn(b'favicon-48.png', page.data, path)
            self.assertIn(b'sizes="192x192" href="/static/favicon-192.png"', page.data, path)
            self.assertIn(b'rel="shortcut icon" href="/favicon.ico"', page.data, path)
        home = self.client.get('/')
        self.assertIn(b'"logo": "http://localhost/static/favicon-192.png"', home.data)
        self.assertIn(b'"@type": "Organization"', home.data)
        icon = self.client.get('/favicon.ico')
        self.assertEqual(icon.status_code, 200)
        self.assertIn('image/', icon.content_type)
        self.assertGreater(len(icon.data), 100)
        png48 = self.client.get('/static/favicon-48.png')
        png192 = self.client.get('/static/favicon-192.png')
        self.assertEqual(png48.status_code, 200)
        self.assertEqual(png192.status_code, 200)
        self.assertEqual(Image.open(BytesIO(png48.data)).size, (48, 48))
        self.assertEqual(Image.open(BytesIO(png192.data)).size, (192, 192))
        robots = self.client.get('/robots.txt').data
        self.assertIn(b'Allow: /favicon.ico', robots)
        self.assertIn(b'Allow: /static/favicon-48.png', robots)
        self.assertIn(b'Allow: /static/favicon-192.png', robots)
        self.assertNotIn(b'Disallow: /favicon', robots)
        self.assertNotIn(b'Disallow: /static/favicon', robots)

    def test_listing_fee_is_promotional_until_2027(self):
        chicago = ZoneInfo('America/Chicago')
        promo = datetime(2026, 12, 31, 23, 59, 59, tzinfo=chicago)
        after = datetime(2027, 1, 1, 0, 0, tzinfo=chicago)
        self.assertEqual(pricing.listing_price_cents(promo), 1499)
        self.assertEqual(pricing.listing_price_cents(after), 4999)
        self.assertTrue(pricing.listing_price(promo)['promotional'])
        self.assertFalse(pricing.listing_price(after)['promotional'])
        self.assertIn('does not expire', pricing.listing_price(promo)['label'])
        self.assertIn('No price change will come', pricing.listing_price(promo)['label'])
        self.assertIn('1-5 business days', pricing.listing_price(promo)['label'])

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

    def test_broker_fee_opens_the_payment_link(self):
        self._login('seller@example.com', 'seller-pass-1')
        pay = self.client.post('/api/account/broker-checkout')
        self.assertEqual(pay.status_code, 200, pay.get_json())
        url = pay.get_json().get('url') or ''
        self.assertTrue(url.startswith('https://buy.stripe.com/'))
        self.assertIn(f"client_reference_id=broker-{self.seller['id']}", url)

    def test_signup_does_not_grant_a_free_broker_account(self):
        created = self.client.post('/api/auth/signup', json={
            'email': 'new-broker@example.com',
            'password': 'broker-pass-1',
            'first_name': 'New',
            'profile_role': 'broker',
        })
        self.assertEqual(created.status_code, 201, created.get_json())
        self.assertEqual(created.get_json()['user']['profile_role'], 'buyer')
        self.assertFalse(created.get_json().get('broker_checkout_required'))
        self.assertNotEqual(created.get_json()['user'].get('broker_application_status'), 'pending')
        blocked = self.client.get('/off-market')
        self.assertEqual(blocked.status_code, 403)
        checkout = self.client.post('/api/account/broker-checkout')
        self.assertEqual(checkout.status_code, 200, checkout.get_json())
        self.assertIn('buy.stripe.com', checkout.get_json().get('url') or '')
        portal = self.client.get('/dashboard')
        self.assertNotIn(b'buy.stripe.com', portal.data)
        self.assertIn(b'Pay $19.99 a month', portal.data)
        self.assertIn(b'href="/settings"', portal.data)

    def test_broker_application_keeps_specialty_and_years(self):
        created = self.client.post('/api/auth/signup', json={
            'email': 'specialty-broker@example.com',
            'password': 'broker-pass-1',
            'first_name': 'Sky',
            'profile_role': 'broker',
            'broker_specialties': 'Citation, King Air',
            'broker_years': 14,
        })
        self.assertEqual(created.status_code, 201, created.get_json())
        user = created.get_json()['user']
        self.assertEqual(user['broker_specialties'], 'Citation, King Air')
        self.assertEqual(user['broker_years'], 14)
        form = self.client.get('/register')
        self.assertNotIn(b'Sign up as a broker', form.data)
        self.assertNotIn(b'broker-signup-check', form.data)
        self.assertNotIn(b'I am signing up as a broker', form.data)
        opened = self.client.get('/register?broker=1')
        self.assertNotIn(b'broker-signup-check', opened.data)
        profile = self.client.get('/dashboard')
        self.assertIn(b'Citation, King Air', profile.data)
        self.assertIn(b'Years in business', profile.data)
        self.assertIn(b'>14<', profile.data)
        edited = self.client.patch('/api/profile', json={
            'broker_specialties': 'Gulfstream',
            'broker_years': 21,
        })
        self.assertEqual(edited.status_code, 200, edited.get_json())
        self.assertEqual(edited.get_json()['user']['broker_specialties'], 'Gulfstream')
        self.assertEqual(edited.get_json()['user']['broker_years'], 21)
        shown = self.client.get('/settings')
        self.assertIn(b'Gulfstream', shown.data)
        self.assertIn(b'21', shown.data)

    def test_signup_does_not_open_a_broker_account(self):
        page = self.client.get('/register')
        self.assertNotIn(b'Sign up as a broker', page.data)
        self.assertNotIn(b'Northstar', page.data)
        main = self.client.post('/register', data={
            'email': 'main-signup@example.com',
            'password': 'broker-pass-1',
            'first_name': 'Main',
            'last_name': 'Signup',
            'company': 'North Hangar',
            'profile_city': 'Dallas',
            'profile_state': 'TX',
            'profile_role': 'broker',
            'broker_signup': '1',
            'broker_path': 'main',
        })
        self.assertEqual(main.status_code, 302)
        self.assertNotIn('buy.stripe.com', main.headers['Location'])
        self.assertTrue(main.headers['Location'].endswith('/profile') or main.headers['Location'].endswith('/dashboard'))
        person = db_module.get_user_by_email('main-signup@example.com')
        self.assertNotEqual(person['profile_role'], 'broker')
        self.assertNotEqual(person.get('broker_application_status'), 'pending')
        self.assertIsNone(db_module.team_membership(person['id']))
        self.assertEqual(self.client.get('/off-market').status_code, 403)

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

    def test_a_team_request_is_approved_by_the_brokerage_not_checkout(self):
        joiner = self._signup('queue-join@example.com', 'broker-pass-1', 'buyer')
        self._login(joiner['email'], 'broker-pass-1')
        asked = self.client.post('/api/account/broker-application', json={
            'kind': 'assign', 'team_id': self.team_id,
        })
        self.assertEqual(asked.status_code, 200, asked.get_json())
        self.assertNotIn('url', asked.get_json())
        self.assertFalse(asked.get_json().get('checkout'))
        self.assertNotEqual(db_module.get_user_by_id(joiner['id']).get('broker_application_status'), 'pending')
        self.assertNotEqual(db_module.get_user_by_id(joiner['id'])['profile_role'], 'broker')
        self._login('admin@example.com', 'admin-pass-1')
        queued = [row['id'] for row in self.client.get('/api/admin/approvals').get_json()['brokers']]
        self.assertNotIn(joiner['id'], queued)
        self._login('broker@example.com', 'broker-pass-1')
        notes = self.client.get('/api/notifications').get_json()['notifications']
        self.assertTrue(any('join' in (note.get('title') or '').lower() for note in notes))
        account = self.client.get('/dashboard')
        self.assertIn(b'Manage members', account.data)
        team = self.client.get('/api/account/team')
        self.assertEqual(team.status_code, 200, team.get_json())
        self.assertEqual(team.get_json()['pending'][0]['user_id'], joiner['id'])
        allowed = self.client.post(f'/api/broker-teams/{self.team_id}/members/{joiner["id"]}/allow')
        self.assertEqual(allowed.status_code, 200, allowed.get_json())
        self.assertEqual(db_module.get_user_by_id(joiner['id'])['profile_role'], 'broker')
        office = self.client.get('/brokers')
        self.assertIn(b'Northstar', office.data)
        self.assertIn(b'Buyer', office.data)
        self.assertNotIn(f'"pin_id": "broker-{joiner["id"]}"'.encode(), office.data)
        self.assertIn(b'Brokers at Northstar', self.client.get(f'/people/{self.broker["id"]}').data)
        removed = self.client.delete(f'/api/broker-teams/{self.team_id}/members/{joiner["id"]}')
        self.assertEqual(removed.status_code, 200, removed.get_json())
        self.assertNotEqual(db_module.get_user_by_id(joiner['id'])['profile_role'], 'broker')
        self.assertIsNone(db_module.team_membership(joiner['id']))

    def test_a_broker_is_added_by_a_paid_account_and_listings_follow(self):
        applicant = self._signup('assign-me@example.com', 'broker-pass-1', 'seller')
        self._login(applicant['email'], 'broker-pass-1')
        asked = self.client.post('/api/account/broker-application', json={
            'kind': 'assign', 'team_id': self.team_id,
        })
        self.assertEqual(asked.status_code, 200, asked.get_json())
        self.assertFalse(asked.get_json().get('broker'))
        self.assertEqual(self.client.get('/off-market').status_code, 403)
        labeled = self.client.patch('/api/profile', json={'profile_role': 'broker'})
        self.assertNotEqual(labeled.get_json()['user']['profile_role'], 'broker')
        self._login('admin@example.com', 'admin-pass-1')
        self.assertEqual(self.client.post(f'/api/admin/brokers/{applicant["id"]}/approve').status_code, 402)
        self._login('broker@example.com', 'broker-pass-1')
        added = self.client.post(
            f'/api/broker-teams/{self.team_id}/members',
            json={'email': applicant['email']},
        )
        self.assertEqual(added.status_code, 200, added.get_json())
        self._login(applicant['email'], 'broker-pass-1')
        self.assertEqual(self.client.get('/off-market').status_code, 200)
        created = self.client.post('/api/listings', json=self._payload('Team Jet', 'public'))
        listing_id = created.get_json()['id']
        db_module.admin_approve_listing_any(listing_id, self.admin['id'])
        own = self.client.get(f'/api/people/{applicant["id"]}/listings')
        self.assertTrue(own.get_json()['listings'][0]['title'].startswith('2018 '))
        self.assertIn('Team Jet', own.get_json()['listings'][0]['title'])
        office = self.client.get(f'/api/people/{self.broker["id"]}/listings')
        office_rows = office.get_json()['listings']
        team_jet = next(row for row in office_rows if 'Team Jet' in row['title'])
        self.assertEqual(team_jet['broker_name'], 'Seller')
        page = self.client.get(f'/people/{self.broker["id"]}')
        self.assertIn(b'Broker', page.data)
        self.assertNotIn(b'Meet our team', page.data)
        self.assertNotIn(b'Aircraft for sale', page.data)
        self._login('buyer@example.com', 'buyer-pass-1')
        member_page = self.client.get(f'/people/{applicant["id"]}')
        self.assertEqual(member_page.status_code, 302)
        self.assertIn(f'/people/{self.broker["id"]}', member_page.headers['Location'])
        brokers_page = self.client.get('/brokers')
        self.assertIn(b'broker-count', brokers_page.data)
        self.assertIn(b'in this view', brokers_page.data)
        self._login('admin@example.com', 'admin-pass-1')
        listed = self.client.get('/api/admin/brokers')
        names = [row['name'] for row in listed.get_json()['brokers']]
        self.assertIn('Seller', names)
        self.assertIn('Broker', names)
        admin_page = self.client.get('/admin')
        self.assertIn(b'>Brokers<', admin_page.data)
        self.assertNotIn(b'Approve brokerage', admin_page.data)

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

    def test_only_public_listings_open_the_paywall(self):
        previous_flag = os.environ.get('REQUIRE_PAYMENT_FOR_LISTINGS')
        previous_key = os.environ.get('STRIPE_SECRET_KEY')
        os.environ['REQUIRE_PAYMENT_FOR_LISTINGS'] = 'true'
        os.environ['STRIPE_SECRET_KEY'] = 'sk_test_paywallonly'
        try:
            self._login('seller@example.com', 'seller-pass-1')
            public = self.client.post('/api/listings', json=self._payload('Paywall Jet', 'public'))
            self.assertEqual(public.status_code, 201, public.get_json())
            self.assertTrue(public.get_json()['payment_required'])
            self.assertEqual(public.get_json()['status'], 'unpaid')
            stored = db_module.get_user_listing_by_id(public.get_json()['id'], active_only=False)
            self.assertTrue(stored['description'].endswith(f"Listing number: {public.get_json()['id']}"))
            page = self.client.get('/create-listing')
            token = page.data.split(b'name="csrf-token" content="', 1)[1].split(b'"', 1)[0].decode()
            blocked = self.client.post(
                f"/api/listings/{public.get_json()['id']}/checkout",
                headers={'Origin': 'http://localhost'},
            )
            self.assertEqual(blocked.status_code, 403, blocked.get_json())
            pay = self.client.post(
                f"/api/listings/{public.get_json()['id']}/checkout",
                json={'amount_cents': 1},
                headers={'Origin': 'http://localhost', 'X-CSRF-Token': token},
            )
            self.assertEqual(pay.status_code, 200, pay.get_json())
            url = pay.get_json().get('url') or ''
            self.assertTrue(url.startswith('https://buy.stripe.com/'))
            self.assertIn(f"listing-{public.get_json()['id']}-user-{self.seller['id']}-sn-5501", url)
            self.assertNotIn('amount_cents=1', url)
            page = self.client.get('/create-listing')
            self.assertIn(b'does not expire', page.data)
            self.assertNotIn(b'opens checkout', page.data)
            self.assertIn(b"/api/listings/' + listingId + '/checkout'", page.data)
            self.assertIn(b'X-CSRF-Token', page.data)
            home = self.client.get('/')
            self.assertIn(b"X-CSRF-Token", home.data)
            self.assertIn(b"/api/listings/' + data.id + '/checkout'", home.data)
            self.assertNotIn(b'buy.stripe.com/eVqdR20zqbge6Rg6oJgbm01', page.data)
            self.assertIn(b'There is no listing fee', page.data)
            self._login('broker@example.com', 'broker-pass-1')
            sale = self.client.post('/api/listings', json=dict(
                self._payload('Free Off Market', 'broker_only'), listing_intent='sale',
            ))
            self.assertEqual(sale.status_code, 201, sale.get_json())
            self.assertFalse(sale.get_json()['payment_required'])
            self.assertEqual(sale.get_json()['status'], 'pending')
            wanted = self.client.post('/api/listings', json=dict(
                self._payload('Wanted Jet', 'broker_only'), listing_intent='wanted', price=0,
            ))
            self.assertEqual(wanted.status_code, 201, wanted.get_json())
            self.assertFalse(wanted.get_json()['payment_required'])
            self.assertEqual(wanted.get_json()['status'], 'pending')
            skip = self.client.post(f"/api/listings/{sale.get_json()['id']}/checkout")
            self.assertEqual(skip.status_code, 200, skip.get_json())
            self.assertTrue(skip.get_json().get('skip'))
            form = self.client.get('/create-listing?market=off_market')
            self.assertIn(b'There is no listing fee', form.data)
        finally:
            if previous_flag is None:
                os.environ.pop('REQUIRE_PAYMENT_FOR_LISTINGS', None)
            else:
                os.environ['REQUIRE_PAYMENT_FOR_LISTINGS'] = previous_flag
            if previous_key is None:
                os.environ.pop('STRIPE_SECRET_KEY', None)
            else:
                os.environ['STRIPE_SECRET_KEY'] = previous_key

    def test_listing_checkout_shows_the_stripe_reason(self):
        previous_flag = os.environ.get('REQUIRE_PAYMENT_FOR_LISTINGS')
        previous_key = os.environ.get('STRIPE_SECRET_KEY')
        os.environ['REQUIRE_PAYMENT_FOR_LISTINGS'] = 'true'
        os.environ['STRIPE_SECRET_KEY'] = 'sk_test_paywallreason'
        try:
            self._login('seller@example.com', 'seller-pass-1')
            public = self.client.post('/api/listings', json=self._payload('Reason Jet', 'public'))
            self.assertEqual(public.status_code, 201, public.get_json())
            import app as app_module

            def refuse(**kwargs):
                raise app_module.stripe.error.InvalidRequestError(
                    'Your account cannot currently make live charges.', 'mode',
                )

            page = self.client.get('/create-listing')
            token = page.data.split(b'name="csrf-token" content="', 1)[1].split(b'"', 1)[0].decode()
            with patch.object(app_module.stripe.Customer, 'list', return_value=type('Page', (), {'data': []})()), \
                 patch.object(app_module.stripe.Customer, 'create', return_value={'id': 'cus_reason'}), \
                 patch.object(app_module.stripe.Customer, 'modify', return_value={'id': 'cus_reason'}), \
                 patch.object(app_module.stripe.checkout.Session, 'create', side_effect=refuse):
                pay = self.client.post(
                    f"/api/listings/{public.get_json()['id']}/checkout",
                    headers={'Origin': 'http://localhost', 'X-CSRF-Token': token},
                )
            self.assertEqual(pay.status_code, 200, pay.get_json())
            self.assertTrue((pay.get_json().get('url') or '').startswith('https://buy.stripe.com/'))
        finally:
            if previous_flag is None:
                os.environ.pop('REQUIRE_PAYMENT_FOR_LISTINGS', None)
            else:
                os.environ['REQUIRE_PAYMENT_FOR_LISTINGS'] = previous_flag
            if previous_key is None:
                os.environ.pop('STRIPE_SECRET_KEY', None)
            else:
                os.environ['STRIPE_SECRET_KEY'] = previous_key

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
        self.assertTrue(row['title'].startswith('2016 '))
        self.assertIn('Quiet Name', row['title'])
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
        import io
        import json
        self._login('seller@example.com', 'seller-pass-1')
        created = self.client.post('/api/listings', json=self._payload('Amend Jet', 'public'))
        listing_id = created.get_json()['id']
        db_module.admin_approve_listing_any(listing_id, self.admin['id'])
        patched = self.client.patch(f'/api/listings/{listing_id}', json={'price': 1800000})
        self.assertEqual(patched.status_code, 200, patched.get_json())
        note = patched.get_json().get('amendment') or ''
        self.assertIn('waiting for approval', note.lower())
        self.assertIn('Price', note)
        self.assertTrue(patched.get_json().get('pending_review'))
        row = db_module.get_listing_with_owner(listing_id)
        self.assertEqual(row['status'], 'active')
        self.assertEqual(float(row['price']), 2500000)
        staged = json.loads(row['pending_changes'])
        self.assertEqual(float(staged['fields']['price']), 1800000)
        page = self.client.get(f'/listing/{listing_id}')
        self.assertIn(b'$2,500,000', page.data)
        self.assertNotIn(b'$1,800,000', page.data)
        self._login('admin@example.com', 'admin-pass-1')
        queue = self.client.get('/api/admin/listings?status=pending')
        queued = [item for item in queue.get_json()['listings'] if item['id'] == listing_id]
        self.assertEqual(len(queued), 1)
        self.assertTrue(queued[0].get('pending_review'))
        rejected = self.client.post(f'/api/admin/listings/{listing_id}/reject', json={'reason': 'Price is off'})
        self.assertEqual(rejected.status_code, 200, rejected.get_json())
        self.assertEqual(rejected.get_json()['status'], 'active')
        row = db_module.get_listing_with_owner(listing_id)
        self.assertEqual(row['status'], 'active')
        self.assertEqual(float(row['price']), 2500000)
        self.assertFalse(row.get('pending_changes'))
        self._login('seller@example.com', 'seller-pass-1')
        again = self.client.patch(f'/api/listings/{listing_id}', json={'price': 1800000})
        self.assertEqual(again.status_code, 200, again.get_json())
        photo = self.client.post(
            f'/api/listings/{listing_id}/media',
            data={'files': (io.BytesIO(b'\xff\xd8\xff\xd9'), 'plane.jpg', 'image/jpeg')},
            content_type='multipart/form-data',
        )
        self.assertEqual(photo.status_code, 201, photo.get_json())
        self.assertTrue(photo.get_json().get('pending_review'))
        self.assertEqual(db_module.list_listing_media(listing_id), [])
        self.assertEqual(len(db_module.list_listing_media(listing_id, include_unpublished=True)), 1)
        self._login('admin@example.com', 'admin-pass-1')
        approved = self.client.post(f'/api/admin/listings/{listing_id}/approve')
        self.assertEqual(approved.status_code, 200, approved.get_json())
        row = db_module.get_listing_with_owner(listing_id)
        self.assertEqual(row['status'], 'active')
        self.assertEqual(float(row['price']), 1800000)
        self.assertFalse(row.get('pending_changes'))
        self.assertEqual(len(db_module.list_listing_media(listing_id)), 1)
        page = self.client.get(f'/listing/{listing_id}')
        self.assertIn(b'$1,800,000', page.data)

    def test_listing_notes_and_profile_details_save_without_approval(self):
        self._login('seller@example.com', 'seller-pass-1')
        created = self.client.post('/api/listings', json=self._payload('Notes Jet', 'public'))
        listing_id = created.get_json()['id']
        db_module.admin_approve_listing_any(listing_id, self.admin['id'])
        notes = self.client.patch(f'/api/listings/{listing_id}', json={
            'description': 'Fresh interior and a new coat of paint.',
            'hours': 640,
            'location': 'Keller, Texas',
            'email': 'seller@example.com',
        })
        self.assertEqual(notes.status_code, 200, notes.get_json())
        self.assertFalse(notes.get_json().get('pending_review'))
        row = db_module.get_listing_with_owner(listing_id)
        self.assertIn('Fresh interior', row['description'])
        self.assertEqual(row['hours'], 640)
        self.assertEqual(row['location'], 'Keller, Texas')
        self.assertFalse(row.get('pending_changes'))
        shown = self.client.get(f'/listing/{listing_id}')
        self.assertIn(b'Fresh interior and a new coat of paint.', shown.data)
        self.assertIn(b'Keller, Texas', shown.data)
        signed = self.client.post('/api/auth/signup', json={
            'email': 'desk-edit@example.com',
            'password': 'seller-pass-1',
            'first_name': 'Desk',
            'profile_role': 'seller',
            'profile_location': 'KTEB',
        })
        self.assertEqual(signed.status_code, 201, signed.get_json())
        person_id = signed.get_json()['user']['id']
        self._login('desk-edit@example.com', 'seller-pass-1')
        profile = self.client.patch('/api/profile', json={
            'phone': '555-0177',
            'broker_bio': 'Based in Keller.',
            'broker_specialties': 'King Air',
            'broker_years': 8,
            'profile_city': 'Keller',
            'profile_state': 'Texas',
            'profile_role': 'broker',
        })
        self.assertEqual(profile.status_code, 200, profile.get_json())
        self.assertFalse(profile.get_json().get('broker_checkout_required'))
        person = profile.get_json()['user']
        self.assertEqual(person['phone'], '555-0177')
        self.assertEqual(person['broker_bio'], 'Based in Keller.')
        self.assertEqual(person['profile_location'], 'Keller, Texas')
        self.assertNotEqual(person['profile_role'], 'broker')
        card = self.client.get('/profile')
        self.assertIn(b'555-0177', card.data)
        self.assertIn(b'Based in Keller.', card.data)
        self._login('admin@example.com', 'admin-pass-1')
        waiting = [row['id'] for row in self.client.get('/api/admin/approvals').get_json()['brokers']]
        self.assertNotIn(person_id, waiting)

    def test_owner_can_delete_a_live_listing(self):
        self._login('seller@example.com', 'seller-pass-1')
        created = self.client.post('/api/listings', json=self._payload('Delete Jet', 'public'))
        listing_id = created.get_json()['id']
        db_module.admin_approve_listing_any(listing_id, self.admin['id'])
        page = self.client.get('/dashboard')
        self.assertIn(b'id="trash-toggle"', page.data)
        removed = self.client.delete(f'/api/listings/{listing_id}')
        self.assertEqual(removed.status_code, 200, removed.get_json())
        row = db_module.get_listing_with_owner(listing_id)
        self.assertEqual(row['status'], 'deleted')
        hidden = self.client.get(f'/listing/{listing_id}')
        self.assertEqual(hidden.status_code, 404)
        mine = self.client.get('/api/listings/me')
        self.assertNotIn(listing_id, [item['id'] for item in mine.get_json()['listings']])
        self.assertIn(listing_id, [item['id'] for item in mine.get_json()['trash']])
        self.assertIn(b'id="trash-toggle"', page.data)
        self._login('admin@example.com', 'admin-pass-1')
        trashed = self.client.get('/api/admin/listings?status=trash')
        self.assertIn(listing_id, [item['id'] for item in trashed.get_json()['listings']])
        self.assertIn(b'id="trash-listings"', self.client.get('/admin').data)
        legacy = self.client.get('/api/my-listings')
        self.assertNotIn(listing_id, [item['id'] for item in legacy.get_json()])

    def test_listing_photos_can_be_added_and_reordered_up_to_fifteen(self):
        import io
        self._login('seller@example.com', 'seller-pass-1')
        created = self.client.post('/api/listings', json=self._payload('Photo Jet', 'public'))
        listing_id = created.get_json()['id']
        form = self.client.get('/create-listing')
        self.assertIn(b'Add a photo', form.data)
        self.assertIn(b'id="photo-preview"', form.data)
        self.assertIn(b'Earlier', form.data)
        self.assertIn(b'id="photos" name="photos" accept="image/jpeg,image/png,image/webp,image/gif,image/bmp,image/tiff,image/avif,image/heic,image/heif,.jpg,.jpeg,.png,.webp,.gif,.bmp,.tif,.tiff,.avif,.heic,.heif"', form.data)
        self.assertIn(b'keeps the whole picture', form.data)
        crop_js = (Path(__file__).resolve().parents[1] / 'static' / 'js' / 'photo-crop.js').read_bytes()
        self.assertIn(b'data-zoom-out', crop_js)
        self.assertIn(b'Fit whole photo', crop_js)
        self.assertIn(b'min="0.5"', crop_js)
        self.assertIn(b'photo-crop.js', form.data)
        self.assertIn(b'data-crop-photo', form.data)
        home = self.client.get('/')
        self.assertIn(b'photo-crop.js', home.data)
        first = db_module.add_listing_media(listing_id, 'photo', 'k1', 'https://example.test/1.jpg', sort_order=0)
        second = db_module.add_listing_media(listing_id, 'photo', 'k2', 'https://example.test/2.jpg', sort_order=1)
        ordered = self.client.post(f'/api/listings/{listing_id}/media/order', json={'ids': [second, first]})
        self.assertEqual(ordered.status_code, 200, ordered.get_json())
        photos = [item for item in db_module.list_listing_media(listing_id) if item['media_type'] == 'photo']
        self.assertEqual([item['id'] for item in photos], [second, first])
        for index in range(13):
            db_module.add_listing_media(listing_id, 'photo', f'k{index+3}', f'https://example.test/{index}.jpg', sort_order=index + 2)
        extra = self.client.post(
            f'/api/listings/{listing_id}/media',
            data={'files': (io.BytesIO(b'\xff\xd8\xff\xd9'), 'extra.jpg', 'image/jpeg')},
            content_type='multipart/form-data',
        )
        self.assertEqual(extra.status_code, 400, extra.get_json())
        self.assertEqual(extra.get_json()['rejected'][0]['reason'], 'photo_limit_reached')
        db_module.admin_approve_listing_any(listing_id, self.admin['id'])
        staged = self.client.post(f'/api/listings/{listing_id}/media/order', json={'ids': [first, second]})
        self.assertEqual(staged.status_code, 200, staged.get_json())
        self.assertTrue(staged.get_json().get('pending_review'))
        still = [item['id'] for item in db_module.list_listing_media(listing_id) if item['media_type'] == 'photo']
        self.assertEqual(still[:2], [second, first])
        self._login('admin@example.com', 'admin-pass-1')
        approved = self.client.post(f'/api/admin/listings/{listing_id}/approve')
        self.assertEqual(approved.status_code, 200, approved.get_json())
        shown = [item['id'] for item in db_module.list_listing_media(listing_id) if item['media_type'] == 'photo']
        self.assertEqual(shown[:2], [first, second])

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

    def test_public_and_off_market_listings_reach_the_admin_queue(self):
        self._login('seller@example.com', 'seller-pass-1')
        public = self.client.post('/api/listings', json=self._payload('Queue Public', 'public'))
        self.assertEqual(public.status_code, 201, public.get_json())
        self._login('broker@example.com', 'broker-pass-1')
        private = self.client.post('/api/listings', json=self._payload('Queue Off Market', 'off_market'))
        self.assertEqual(private.status_code, 201, private.get_json())
        self._login('admin@example.com', 'admin-pass-1')
        queue = self.client.get('/api/admin/listings?status=pending')
        self.assertEqual(queue.status_code, 200)
        listings = queue.get_json()['listings']
        public_row = next(row for row in listings if 'Queue Public' in (row.get('title') or ''))
        off_row = next(row for row in listings if 'Queue Off Market' in (row.get('title') or ''))
        self.assertNotEqual(public_row.get('payment_status'), 'paid')
        self.assertEqual(off_row.get('market'), 'broker_only')
        db_module.mark_listing_fee_paid(public.get_json()['id'])
        paid_queue = self.client.get('/api/admin/listings?status=pending')
        paid_row = next(row for row in paid_queue.get_json()['listings'] if 'Queue Public' in (row.get('title') or ''))
        self.assertEqual(paid_row.get('payment_status'), 'paid')
        page = self.client.get('/admin')
        self.assertNotIn(b'Stripe: ', page.data)
        self.assertNotIn(b'Not paid', page.data)
        self.assertNotIn(b'The customer name is the company typed at checkout.', page.data)
        self.assertIn(b'Resubmitted. Already paid', page.data)
        notes = self.client.get('/api/notifications')
        self.assertEqual(notes.status_code, 200)
        note_titles = [row.get('title') for row in notes.get_json()['notifications']]
        self.assertTrue(any('Queue Public' in (title or '') for title in note_titles))
        self.assertTrue(any('Queue Off Market' in (title or '') for title in note_titles))

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
        self.assertNotEqual(created.get_json()['user'].get('broker_application_status'), 'pending')
        self._login('apply-broker@example.com', 'broker-pass-1')
        asked = self.client.post('/api/account/broker-application', json={
            'kind': 'main', 'name': 'Apply Desk', 'city': 'Dallas', 'state': 'TX',
        })
        self.assertEqual(asked.status_code, 200, asked.get_json())
        self.assertFalse(asked.get_json().get('broker'))
        self.assertNotEqual(db_module.get_user_by_id(applicant_id)['profile_role'], 'broker')
        self.assertEqual(self.client.get('/off-market').status_code, 403)
        self._login('buyer@example.com', 'buyer-pass-1')
        self.assertEqual(self.client.post(f'/api/admin/brokers/{applicant_id}/approve').status_code, 403)
        self._login('admin@example.com', 'admin-pass-1')
        waiting = self.client.get('/api/admin/approvals').get_json()['brokers']
        submitted = next(row for row in waiting if row['id'] == applicant_id)
        self.assertFalse(submitted.get('stripe_paid'))
        self.assertIsNone(submitted.get('subscription_number'))
        titles = [note.get('title') or '' for note in self.client.get('/api/notifications').get_json()['notifications']]
        self.assertTrue(any(title.startswith('Broker submission to approve') for title in titles))
        self._login('apply-broker@example.com', 'broker-pass-1')
        labeled = self.client.patch('/api/profile', json={'profile_role': 'broker'})
        self.assertNotEqual(labeled.get_json()['user']['profile_role'], 'broker')
        self.assertEqual(self.client.get('/off-market').status_code, 403)
        self._login('admin@example.com', 'admin-pass-1')
        page = self.client.get('/admin')
        self.assertIn(b'subscription_number', page.data)
        self.assertIn(b'ap__listing-no', page.data)
        self.assertIn(b'data-approve-broker="\' + person.id + \'">Approve</button>', page.data)
        self.assertIn(b"document.getElementById('account-approve').hidden = !waiting;", page.data)
        db_module.update_user_subscription(
            applicant_id, 'broker', subscription_status='active', stripe_subscription_id='sub_queue_broker',
        )
        numbered = next(row for row in self.client.get('/api/admin/approvals').get_json()['brokers'] if row['id'] == applicant_id)
        self.assertEqual(numbered.get('subscription_number'), 'sub_queue_broker')
        account = self.client.get(f'/api/admin/users/{applicant_id}')
        self.assertEqual(account.get_json()['subscription_number'], 'sub_queue_broker')
        approved = self.client.post(f'/api/admin/brokers/{applicant_id}/approve')
        self.assertEqual(approved.status_code, 200, approved.get_json())
        person = db_module.get_user_by_id(applicant_id)
        self.assertEqual(person['profile_role'], 'broker')
        self.assertEqual(person['broker_application_status'], 'approved')
        seat = db_module.team_membership(applicant_id)
        self.assertTrue(seat['is_admin'])
        self.assertEqual(seat['subscription_status'], 'active')
        self._login('apply-broker@example.com', 'broker-pass-1')
        own = self.client.get('/profile')
        self.assertIn(b'Broker number', own.data)
        self.assertIn(b'sub_queue_broker', own.data)
        self._login('buyer@example.com', 'buyer-pass-1')
        self.assertNotIn(b'sub_queue_broker', self.client.get(f'/people/{applicant_id}').data)
        self._login('admin@example.com', 'admin-pass-1')
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
        self.assertIn(b'Seller', public.data)
        self.assertNotIn(b'Aircraft for sale', public.data)
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
        db_module.add_listing_media(
            listing_id, 'photo', 'review-photo', 'https://example.test/plane.jpg',
            sort_order=0, published=False,
        )
        self._login('admin@example.com', 'admin-pass-1')
        review = self.client.get(f'/api/admin/listings/{listing_id}/review')
        self.assertEqual(review.status_code, 200, review.get_json())
        body = review.get_json()
        self.assertEqual(body['listing']['photos'], [{'url': 'https://example.test/plane.jpg', 'label': 'New'}])
        self.assertEqual(body['listing']['price'], 2500000)
        self.assertIn('payment_status', body['listing'])
        self.assertIn('price', body['aircraft_data'])
        self.assertTrue(body['checks'])
        sent = self.client.post(
            f'/api/admin/listings/{listing_id}/message',
            json={'message': 'Add the serial number.'},
        )
        self.assertEqual(sent.status_code, 200, sent.get_json())
        self.assertEqual(sent.get_json()['status'], 'changes_requested')
        row = db_module.get_listing_with_owner(listing_id)
        self.assertEqual(row['status'], 'changes_requested')
        self.assertIn('serial', row.get('review_message') or '')
        hidden = self.client.get('/api/admin/listings?status=pending')
        self.assertNotIn(listing_id, [item['id'] for item in hidden.get_json()['listings']])
        self._login('seller@example.com', 'seller-pass-1')
        mine = self.client.get('/api/listings/me')
        self.assertEqual(mine.status_code, 200)
        found = next(item for item in mine.get_json()['listings'] if item['id'] == listing_id)
        self.assertIn('serial', found.get('review_message') or '')
        with db_module.get_session() as session:
            session.query(db_module.UserListing).filter(db_module.UserListing.id == listing_id).update(
                {'payment_status': 'paid'}, synchronize_session=False
            )
        dashboard = self.client.get('/dashboard')
        self.assertIn(b'Resubmit for review', dashboard.data)
        again = self.client.post(f'/api/listings/{listing_id}/resubmit')
        self.assertEqual(again.status_code, 200, again.get_json())
        self.assertFalse(again.get_json()['charged_again'])
        self.assertEqual(again.get_json()['status'], 'pending')
        row = db_module.get_listing_with_owner(listing_id)
        self.assertEqual(row['payment_status'], 'paid')
        self.assertFalse(row.get('review_message'))
        self._login('admin@example.com', 'admin-pass-1')
        queue = self.client.get('/api/admin/listings?status=pending')
        queued = [item for item in queue.get_json()['listings'] if item['id'] == listing_id]
        self.assertEqual(len(queued), 1)
        self.assertEqual(queued[0]['photos'][0]['url'], 'https://example.test/plane.jpg')

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
        mine = self.client.get('/api/listings/me')
        found = next(item for item in mine.get_json()['listings'] if item['id'] == listing_id)
        self.assertTrue(found['resubmitted'])
        self._login('admin@example.com', 'admin-pass-1')
        queue = self.client.get('/api/admin/listings?status=pending')
        queued = next(item for item in queue.get_json()['listings'] if item['id'] == listing_id)
        self.assertTrue(queued['resubmitted'])

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

    def test_listing_fee_follows_the_subscription(self):
        self._login('seller@example.com', 'seller-pass-1')
        created = self.client.post('/api/listings', json=self._payload('Fee Follows Jet', 'public'))
        listing_id = created.get_json()['id']
        db_module.set_user_listing_status(listing_id, 'unpaid')
        db_module.set_listing_payment_session(listing_id, 'cs_test_live_sub')
        paid = self.client.post('/api/stripe/webhook', json={
            'id': 'evt_live_sub',
            'type': 'checkout.session.completed',
            'data': {'object': {
                'id': 'cs_test_live_sub',
                'payment_status': 'unpaid',
                'customer': 'cus_listing_fee',
                'metadata': {
                    'purpose': 'listing_fee',
                    'listing_id': str(listing_id),
                    'user_id': str(self.seller['id']),
                },
                'subscription': {'id': 'sub_listing_fee', 'status': 'active'},
            }},
        })
        self.assertEqual(paid.status_code, 200, paid.get_json())
        self.assertFalse(paid.get_json().get('pending'))
        row = db_module.get_listing_with_owner(listing_id)
        self.assertEqual(row.get('payment_status'), 'paid')
        self.assertEqual(row.get('status'), 'pending')
        self.assertEqual(row.get('stripe_subscription_id'), 'sub_listing_fee')
        self.assertEqual(row.get('stripe_customer_id'), 'cus_listing_fee')
        self.assertTrue(db_module.admin_approve_listing_any(listing_id, self.admin['id']))
        visible = self.client.get('/api/user-listings')
        self.assertIn('Fee Follows Jet', visible.get_data(as_text=True))
        page = self.client.get('/dashboard')
        self.assertIn(b'Manage billing', page.data)
        ended = self.client.post('/api/stripe/webhook', json={
            'id': 'evt_end_sub',
            'type': 'customer.subscription.deleted',
            'data': {'object': {
                'id': 'sub_listing_fee',
                'status': 'canceled',
                'metadata': {'purpose': 'listing_fee', 'listing_id': str(listing_id)},
            }},
        })
        self.assertEqual(ended.status_code, 200, ended.get_json())
        row = db_module.get_listing_with_owner(listing_id)
        self.assertEqual(row.get('status'), 'suspended')
        self.assertEqual(row.get('payment_status'), 'canceled')
        hidden = self.client.get('/api/user-listings')
        self.assertNotIn('Fee Follows Jet', hidden.get_data(as_text=True))

    def test_stripe_checkout_namespace_loads(self):
        import stripe
        self.assertIsNotNone(stripe.checkout)
        self.assertTrue(callable(stripe.checkout.Session.create))
        self.assertIsNotNone(stripe.billing_portal)
        self.assertTrue(callable(stripe.billing_portal.Session.create))

    def test_returning_from_checkout_marks_the_listing_paid(self):
        import stripe
        self._login('seller@example.com', 'seller-pass-1')
        created = self.client.post('/api/listings', json=self._payload('Return Jet', 'public'))
        listing_id = created.get_json()['id']
        db_module.set_user_listing_status(listing_id, 'unpaid')
        previous_key = os.environ.get('STRIPE_SECRET_KEY')
        os.environ['STRIPE_SECRET_KEY'] = 'sk_test_returncheck'
        state = {'status': 'open', 'payment_status': 'unpaid', 'subscription_status': 'incomplete'}

        def retrieve(session_id, expand=None):
            return {
                'id': session_id,
                'status': state['status'],
                'payment_status': state['payment_status'],
                'metadata': {
                    'purpose': 'listing_fee',
                    'listing_id': str(listing_id),
                    'user_id': str(self.seller['id']),
                },
                'payment_intent': 'pi_return_1',
                'subscription': {'id': 'sub_return_1', 'status': state['subscription_status']},
            }

        original = stripe.checkout.Session.retrieve
        stripe.checkout.Session.retrieve = retrieve
        try:
            waiting = self.client.post(
                f'/api/listings/{listing_id}/confirm-payment',
                json={'session_id': 'cs_test_return'},
            )
            self.assertEqual(waiting.status_code, 400, waiting.get_json())
            self.assertNotEqual(db_module.get_listing_with_owner(listing_id).get('payment_status'), 'paid')
            state['status'] = 'complete'
            state['payment_status'] = 'unpaid'
            state['subscription_status'] = 'active'
            settled = self.client.post(
                f'/api/listings/{listing_id}/confirm-payment',
                json={'session_id': 'cs_test_return'},
            )
            self.assertEqual(settled.status_code, 200, settled.get_json())
            row = db_module.get_listing_with_owner(listing_id)
            self.assertEqual(row.get('payment_status'), 'paid')
            self.assertEqual(row.get('status'), 'pending')
            page = self.client.get(f'/dashboard?submitted={listing_id}&paid=confirmed')
            self.assertIn(b'Waiting for approval.', page.data)
            self.assertNotIn(b'This listing has not been paid for. It is only saved as a draft.', page.data.split(b'loadMyListings')[0])
        finally:
            stripe.checkout.Session.retrieve = original
            if previous_key is None:
                os.environ.pop('STRIPE_SECRET_KEY', None)
            else:
                os.environ['STRIPE_SECRET_KEY'] = previous_key

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
        self.assertIn(b'Refunds | JetSchool', page.data)
        self.assertIn(b'rel="canonical" href="http://localhost/refunds"', page.data)
        self.assertIn(b'"@type": "WebPage"', page.data)
        self.assertIn(b'<h2 class="h4" style="color:#fff;">Listing fees</h2>', page.data)
        self.assertIn(b'non-refundable once a listing has been approved and published', page.data)
        self.assertIn(b'not a promise that a refund will be issued', page.data)
        self.assertNotIn(b'noindex', page.data)
        filtered = self.client.get('/refunds?utm_source=test')
        self.assertIn(b'noindex, follow', filtered.data)
        self.assertIn(b'rel="canonical" href="http://localhost/refunds"', filtered.data)
        terms = self.client.get('/terms')
        self.assertIn(b'Terms of Service | JetSchool', terms.data)
        self.assertIn(b'rel="canonical" href="http://localhost/terms"', terms.data)
        self.assertIn(b'href="/refunds"', terms.data)
        self.assertIn(b'analytics, hosting, and media storage', terms.data)
        self.assertNotIn(b'<h4', terms.data)
        queried = self.client.get('/terms?ref=footer')
        self.assertIn(b'noindex, follow', queried.data)
        self.assertIn(b'rel="canonical" href="http://localhost/terms"', queried.data)

    def test_contact_message_reaches_admin_alerts(self):
        page = self.client.get('/contact')
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'<h1>Contact JetSchool</h1>', page.data)
        self.assertIn(b'rel="canonical" href="http://localhost/contact"', page.data)
        self.assertIn(b'ContactPage', page.data)
        self.assertIn(b'contact_message_sent', page.data)
        self.assertIn(b'support@jetschoolusa.com', page.data)
        self.assertNotIn(b'noindex', page.data)
        filtered = self.client.get('/contact?sent=1')
        self.assertIn(b'noindex, follow', filtered.data)
        self.assertIn(b'rel="canonical" href="http://localhost/contact"', filtered.data)
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

    def test_privacy_page_names_analytics_and_keeps_one_canonical(self):
        page = self.client.get('/privacy')
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'Privacy Policy | JetSchool', page.data)
        self.assertIn(b'rel="canonical" href="http://localhost/privacy"', page.data)
        self.assertIn(b'"@type": "WebPage"', page.data)
        self.assertIn(b'The words typed into a contact message are not sent to Google.', page.data)
        self.assertNotIn(b'noindex', page.data)
        filtered = self.client.get('/privacy?utm_source=test')
        self.assertIn(b'noindex, follow', filtered.data)
        self.assertIn(b'rel="canonical" href="http://localhost/privacy"', filtered.data)

    def test_one_google_tag_is_on_every_page(self):
        os.environ['ANALYTICS_MEASUREMENT_ID'] = 'G-TEST1234'
        os.environ['GOOGLE_SITE_VERIFICATION'] = 'bad token'
        try:
            for path in ('/', '/contact', '/brokers', '/privacy', '/no-such-page'):
                page = self.client.get(path)
                self.assertEqual(page.data.count(b'https://www.googletagmanager.com/gtm.js?id=GTM-TVGS9R2S'), 1, path)
                self.assertNotIn(b'gtag/js', page.data)
                self.assertNotIn(b'google-site-verification', page.data)
                head = page.data.split(b'<head>', 1)[1][:220]
                self.assertIn(b'GTM-TVGS9R2S', head)
            os.environ['GOOGLE_SITE_VERIFICATION'] = 'verifytoken123'
            home = self.client.get('/')
            self.assertEqual(home.data.count(b'GTM-TVGS9R2S'), 1)
            self.assertIn(b'google-site-verification" content="verifytoken123"', home.data)
        finally:
            os.environ.pop('ANALYTICS_MEASUREMENT_ID', None)
            os.environ.pop('GOOGLE_SITE_VERIFICATION', None)

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

    def test_a_paid_listing_or_broker_is_not_asked_to_pay_again(self):
        person = self._paid_broker('already-paid@example.com', 'sub_already_paid')
        self._login(person['email'], 'broker-pass-1')
        again = self.client.post('/api/account/broker-checkout')
        self.assertEqual(again.status_code, 200, again.get_json())
        self.assertTrue(again.get_json().get('already'))
        self.assertNotIn('url', again.get_json())
        account = self.client.get('/dashboard')
        self.assertIn(b'Subscription is active.', account.data)
        self.assertNotIn(b'Pay $19.99 a month', account.data)
        self.assertIn(b'Waiting for approval.', account.data)
        self.assertIn(b'only saved as a draft.', account.data)
        created = self.client.post('/api/listings', json=self._payload('Already Paid Jet', 'public'))
        listing_id = created.get_json()['id']
        with db_module.get_session() as session:
            session.query(db_module.UserListing).filter(db_module.UserListing.id == listing_id).update(
                {'payment_status': 'paid', 'status': 'pending'}, synchronize_session=False,
            )
        pay = self.client.post(f'/api/listings/{listing_id}/checkout')
        self.assertEqual(pay.status_code, 200, pay.get_json())
        self.assertTrue(pay.get_json().get('skip'))

    def test_refund_shows_on_the_listing_it_paid_for(self):
        self._login('seller@example.com', 'seller-pass-1')
        created = self.client.post('/api/listings', json=self._payload('Refunded Fee Jet', 'public'))
        listing_id = created.get_json()['id']
        db_module.admin_approve_listing_any(listing_id, self.admin['id'])
        with db_module.get_session() as session:
            session.query(db_module.UserListing).filter(db_module.UserListing.id == listing_id).update(
                {'payment_status': 'pending', 'stripe_subscription_id': 'sub_listing_refund'},
                synchronize_session=False,
            )
        refunded = self.client.post('/api/stripe/webhook', json={
            'id': 'evt_listing_fee_refund',
            'type': 'charge.refunded',
            'data': {'object': {
                'object': 'charge', 'amount': 4999, 'amount_refunded': 4999,
                'refunded': True, 'payment_intent': 'pi_listing_fee_refund',
                'invoice': {'subscription': 'sub_listing_refund'},
            }},
        })
        self.assertEqual(refunded.status_code, 200, refunded.get_json())
        row = db_module.get_listing_with_owner(listing_id)
        self.assertEqual(row['payment_status'], 'refunded')
        self.assertEqual(row['stripe_payment_intent_id'], 'pi_listing_fee_refund')
        self.assertEqual(row['status'], 'active')
        kept = db_module.mark_listing_fee_paid(listing_id, subscription_id='sub_listing_refund')
        self.assertEqual(kept, listing_id)
        self.assertEqual(db_module.get_listing_with_owner(listing_id)['payment_status'], 'refunded')
        page = self.client.get(f'/listing/{listing_id}')
        self.assertIn(b'Listing fee refunded', page.data)
        self._login('buyer@example.com', 'buyer-pass-1')
        hidden = self.client.get(f'/listing/{listing_id}')
        self.assertNotIn(b'Listing fee refunded', hidden.data)
        self._login('seller@example.com', 'seller-pass-1')
        mine = self.client.get('/api/listings/me')
        match = next(item for item in mine.get_json()['listings'] if item['id'] == listing_id)
        self.assertEqual(match['payment_status'], 'refunded')
        self._login('admin@example.com', 'admin-pass-1')
        listed = self.client.get('/api/admin/listings')
        admin_row = next(item for item in listed.get_json()['listings'] if item['id'] == listing_id)
        self.assertEqual(admin_row['payment_status'], 'refunded')

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
        self.assertIn(b'Manage payment', page.data)
        self.assertIn(b'js-delete-broker-subscription">Delete', page.data)
        self.assertIn(b'/api/account/broker-subscription/cancel-request', page.data)
        self.assertIn(b'subscription-bar__pay', page.data)
        opened = self.client.post('/api/account/billing-portal', json={'purpose': 'broker'})
        self.assertEqual(opened.status_code, 503, opened.get_json())
        self.assertNotIn('billing.stripe.com', opened.get_json().get('url') or '')
        from app import _broker_billing_row, _broker_portal_params
        billing = _broker_billing_row(person['id'])
        self.assertEqual(billing['stripe_subscription_id'], 'sub_portal_broker')
        params = _broker_portal_params(billing, 'https://jetschoolusa.com/dashboard')
        self.assertEqual(params['customer'], 'cus_sub_portal_broker')
        self.assertEqual(params['flow_data']['subscription_update']['subscription'], 'sub_portal_broker')
        self.assertNotIn('billing.stripe.com', str(params))
        self.assertIn(b'js-manage-broker-payment', page.data)
        self.assertIn(b"purpose: 'broker'", page.data)
        self.assertIn(b'Subscription is active.', page.data)
        bar = page.data.find(b'class="subscription-status')
        state = page.data.find(b'>active<', bar)
        pay = page.data.find(b'subscription-bar__pay', state)
        self.assertGreater(state, bar)
        self.assertGreater(pay, state)
        self.assertLess(pay - state, 250)
        active_at = page.data.find(b'Subscription is active.')
        button_at = page.data.find(b'js-manage-broker-payment', active_at)
        self.assertGreater(button_at, active_at)
        self.assertLess(button_at - active_at, 500)
        bar_end = page.data.find(b'Manage billing', bar)
        bar_html = page.data[bar:bar_end if bar_end > bar else bar + 2500]
        self.assertIn(b'js-delete-broker-subscription">Delete', bar_html)
        self.assertNotIn(b'js-manage-broker-payment', bar_html)
        self.assertNotIn(b'billing-portal', bar_html)

    def test_deleting_a_broker_subscription_waits_for_approval(self):
        person = self._paid_broker('end-ask@example.com', 'sub_end_ask')
        self._login(person['email'], 'broker-pass-1')
        missing = self.client.post('/api/account/broker-subscription/cancel-request')
        self.assertEqual(missing.status_code, 200, missing.get_json())
        row = db_module.get_user_subscription(person['id'], 'broker')
        self.assertEqual(row['subscription_status'], 'active')
        self.assertIsNotNone(row.get('cancel_requested_at'))
        self.assertEqual(self.client.get('/off-market').status_code, 200)
        waiting = self.client.get('/profile')
        self.assertIn(b'Delete requested', waiting.data)
        self.assertIn(b'Waiting for approval.', waiting.data)
        self._login('admin@example.com', 'admin-pass-1')
        approvals = self.client.get('/api/admin/approvals')
        self.assertEqual(approvals.status_code, 200)
        match = next(item for item in approvals.get_json()['subscription_deletes'] if item['user_id'] == person['id'])
        self.assertEqual(match['subscription_number'], 'sub_end_ask')
        self.assertEqual(match['subscription_status'], 'active')
        portal = self.client.get('/admin')
        self.assertIn(b'data-clear-cancel', portal.data)
        self.assertIn(b'End it in Stripe yourself.', portal.data)
        import app as app_module
        with patch.object(app_module.stripe.Subscription, 'delete', side_effect=AssertionError('stripe cancel')):
            cleared = self.client.post(f"/api/admin/subscriptions/{person['id']}/cancel-request/clear")
        self.assertEqual(cleared.status_code, 200, cleared.get_json())
        self.assertEqual(cleared.get_json()['subscription_status'], 'active')
        row = db_module.get_user_subscription(person['id'], 'broker')
        self.assertEqual(row['subscription_status'], 'active')
        self.assertIsNone(row.get('cancel_requested_at'))
        self.assertFalse(any(
            item['user_id'] == person['id']
            for item in self.client.get('/api/admin/approvals').get_json()['subscription_deletes']
        ))
        self._login(person['email'], 'broker-pass-1')
        with patch.object(app_module.stripe.Subscription, 'delete', side_effect=AssertionError('stripe cancel')):
            again = self.client.post('/api/account/broker-subscription/cancel-request')
        self.assertEqual(again.status_code, 200, again.get_json())
        db_module.update_user_subscription(person['id'], 'broker', subscription_status='canceled')
        ended = db_module.get_user_subscription(person['id'], 'broker')
        self.assertEqual(ended['subscription_status'], 'canceled')
        self.assertIsNone(ended.get('cancel_requested_at'))
        plain = self._signup('end-plain@example.com', 'broker-pass-1', 'seller')
        db_module.update_user_subscription(plain['id'], 'broker', subscription_status='active')
        self._login(plain['email'], 'broker-pass-1')
        shown = self.client.get('/profile')
        self.assertIn(b'js-delete-broker-subscription">Delete', shown.data)
        asked = self.client.post('/api/account/broker-subscription/cancel-request')
        self.assertEqual(asked.status_code, 200, asked.get_json())
        plain_row = db_module.get_user_subscription(plain['id'], 'broker')
        self.assertEqual(plain_row['subscription_status'], 'active')
        self.assertIsNotNone(plain_row.get('cancel_requested_at'))

    def test_listing_fee_ignores_a_client_supplied_amount(self):
        from app import _listing_fee_cents
        self.assertEqual(_listing_fee_cents(), pricing.listing_price_cents())
        self._login('seller@example.com', 'seller-pass-1')
        created = self.client.post('/api/listings', json=self._payload('Fee Jet', 'public'))
        listing_id = created.get_json()['id']
        checkout = self.client.post(f'/api/listings/{listing_id}/checkout', json={'amount': 1, 'amount_cents': 1})
        self.assertEqual(checkout.status_code, 200)
        self.assertTrue(checkout.get_json().get('skip'))

    def test_a_typed_city_and_state_lands_in_that_state(self):
        import sections
        keller = sections.resolve_place('Keller, Texas')
        self.assertAlmostEqual(keller['lat'], 32.9346, delta=0.02)
        self.assertAlmostEqual(keller['lon'], -97.2517, delta=0.02)
        self.assertEqual(sections.resolve_place('Keller Texas')['lat'], keller['lat'])
        self.assertEqual(sections.resolve_place('KTEB').get('icao'), 'KTEB')
        self.assertEqual(sections.resolve_place('KEE').get('country'), 'CG')
        person = self._signup('keller-pin@example.com', 'broker-pass-1', 'seller')
        db_module.update_user_profile(person['id'], {
            'first_name': 'Kellerpin',
            'profile_location': 'Keller, Texas',
            'company': 'Kellerpin Aviation',
        })
        from app import _grant_broker_account
        _grant_broker_account(person['id'])
        with db_module.get_session() as session:
            session.query(db_module.User).filter(db_module.User.id == person['id']).update(
                {'broker_lat': -0.083, 'broker_lon': 14.533}, synchronize_session=False,
            )
            session.query(db_module.BrokerTeam).filter(
                db_module.BrokerTeam.admin_user_id == person['id'],
            ).update({'latitude': -0.083, 'longitude': 14.533}, synchronize_session=False)
        page = self.client.get('/brokers')
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'Kellerpin', page.data)
        self.assertIn(b'32.9346', page.data)
        self.assertNotIn(b'14.533', page.data)

    def test_approved_broker_gets_off_market_and_the_map(self):
        person = self._signup('map-broker@example.com', 'broker-pass-1', 'seller')
        db_module.update_user_profile(person['id'], {'first_name': 'Mapbroker', 'profile_location': 'KTEB'})
        self._login('admin@example.com', 'admin-pass-1')
        approved = self.client.post(f"/api/admin/brokers/{person['id']}/approve")
        self.assertEqual(approved.status_code, 402, approved.get_json())
        self.assertNotIn(b'Mapbroker', self.client.get('/brokers').data)
        db_module.update_user_subscription(
            person['id'], 'broker', subscription_status='active', stripe_subscription_id='sub_map_broker',
        )
        from app import _grant_broker_account
        _grant_broker_account(person['id'])
        directory = self.client.get('/brokers')
        self.assertEqual(directory.status_code, 200)
        self.assertIn(b'Mapbroker', directory.data)
        self.assertNotIn(b'id="broker-list"', directory.data)
        self.assertIn(b'id="broker-search"', directory.data)
        self.assertIn(b'Find an Aircraft Broker | JetSchool', directory.data)
        self.assertIn(b'<h1>Find an aircraft broker</h1>', directory.data)
        self.assertIn(b'rel="canonical" href="http://localhost/brokers"', directory.data)
        self.assertIn(b'CollectionPage', directory.data)
        self.assertIn(b'broker_area_search', directory.data)
        self.assertIn(b'noindex, follow', self.client.get('/brokers?q=kteb').data)
        self.assertIn(b'Airport code or location', directory.data)
        self.assertIn(b'/api/airports?q=', directory.data)
        self.assertIn(b"if (Date.now() - pinClickAt < 400) return;", directory.data)
        self.assertIn(b'clearSelection();', directory.data)
        self.assertIn(b'Open profile', directory.data)
        self._login('map-broker@example.com', 'broker-pass-1')
        opened = self.client.get('/off-market')
        self.assertEqual(opened.status_code, 200)
        listed = self.client.post('/api/listings', json=self._payload('Quiet Map Jet', 'broker_only'))
        self.assertEqual(listed.status_code, 201, listed.get_json())
        self._login('seller@example.com', 'seller-pass-1')
        blocked = self.client.post('/api/listings', json=self._payload('Seller Off Market', 'broker_only'))
        self.assertEqual(blocked.status_code, 403)

    def test_owner_can_delete_their_account_from_the_profile(self):
        person = self._signup('delete-me@example.com', 'delete-pass-1', 'seller')
        self._login('delete-me@example.com', 'delete-pass-1')
        page = self.client.get('/profile')
        self.assertIn(b'id="delete-account"', page.data)
        removed = self.client.delete('/api/account')
        self.assertEqual(removed.status_code, 200, removed.get_json())
        self.assertIsNone(db_module.get_user_by_id(person['id']))
        self.assertEqual(self.client.get('/api/auth/me').status_code, 401)
        self.assertEqual(self.client.delete('/api/account').status_code, 401)

    def test_off_market_listing_contact_comes_from_the_poster(self):
        person = self._paid_broker('off-contact@example.com', 'sub_off_contact')
        db_module.update_user_profile(person['id'], {
            'first_name': 'North',
            'last_name': 'Star',
            'phone': '555-0148',
            'company': 'Northstar Desk',
        })
        self._login('off-contact@example.com', 'broker-pass-1')
        created = self.client.post('/api/listings', json=self._payload('Contact Jet', 'off_market'))
        self.assertEqual(created.status_code, 201, created.get_json())
        listing_id = created.get_json()['id']
        self.assertTrue(db_module.admin_approve_listing_any(listing_id, self.admin['id']))
        page = self.client.get('/off-market')
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'555-0148', page.data)
        self.assertIn(b'off-contact@example.com', page.data)
        self.assertIn(b'Northstar Desk', page.data)
        self.assertNotIn(b'seller@example.com', page.data)
        self.assertIn(b'id="om-contact"', page.data)

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
            'contact_email': 'buyer@example.com', 'contact_phone': '555-0199',
        })
        self.assertEqual(request_note.status_code, 201, request_note.get_json())
        listing_note = self.client.post(f"/api/brokers/{self.broker['id']}/messages", json={
            'kind': 'listing', 'listing_id': listing_id, 'notes': 'Please take a look',
            'contact_email': 'buyer@example.com', 'contact_phone': '555-0199',
        })
        self.assertEqual(listing_note.status_code, 201, listing_note.get_json())
        page = self.client.get(f'/listing/{listing_id}')
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'Range (seats full)', page.data)
        self.assertIn(b'Best Speed/$', page.data)
        self.assertIn(b'Best All-Around/$', page.data)
        self.assertIn(b'showroom', page.data)
        self.assertIn(b'Seller notes', page.data)
        self.assertIn(b'showroom-prev', page.data)
        self.assertIn(b'for sale | JetSchool', page.data)
        self.assertIn(b'rel="canonical" href="http://localhost/listing/' + str(listing_id).encode() + b'"', page.data)
        self.assertIn(b'"@type": "Product"', page.data)
        self.assertIn(b'listing_view', page.data)
        self.assertIn(b'listing_broker_send', page.data)
        self.assertNotIn(b'noindex', page.data)
        queried = self.client.get(f'/listing/{listing_id}?ref=share')
        self.assertIn(b'noindex, follow', queried.data)
        self.assertIn(b'rel="canonical" href="http://localhost/listing/' + str(listing_id).encode() + b'"', queried.data)
        self._login('broker@example.com', 'broker-pass-1')
        inbox = self.client.get('/api/broker/messages')
        self.assertEqual(inbox.status_code, 200)
        kinds = {row['kind'] for row in inbox.get_json()['inbox']}
        self.assertIn('request', kinds)
        self.assertIn('listing', kinds)
        self.assertTrue(all(row['contact_email'] == 'buyer@example.com' and row['contact_phone'] == '555-0199' for row in inbox.get_json()['inbox']))
        request_id = next(row['id'] for row in inbox.get_json()['inbox'] if row['kind'] == 'request')
        removed = self.client.delete(f'/api/broker/messages/{request_id}')
        self.assertEqual(removed.status_code, 200, removed.get_json())
        left = self.client.get('/api/broker/messages').get_json()['inbox']
        self.assertEqual([row['kind'] for row in left], ['listing'])
        self._login('seller@example.com', 'seller-pass-1')
        blocked = self.client.delete(f'/api/broker/messages/{left[0]["id"]}')
        self.assertEqual(blocked.status_code, 404)
        self._login('broker@example.com', 'broker-pass-1')
        self.assertEqual(len(self.client.get('/api/broker/messages').get_json()['inbox']), 1)
        cleared = self.client.delete('/api/broker/messages')
        self.assertEqual(cleared.status_code, 200, cleared.get_json())
        archived = self.client.get('/api/broker/messages').get_json()
        self.assertEqual(archived['inbox'], [])
        self.assertEqual(len(archived['deleted']), 2)
        put_back = self.client.post(f'/api/broker/messages/{request_id}/restore')
        self.assertEqual(put_back.status_code, 200, put_back.get_json())
        restored = self.client.get('/api/broker/messages').get_json()
        self.assertEqual([row['kind'] for row in restored['inbox']], ['request'])
        self.assertEqual(len(restored['deleted']), 1)
        self._login('buyer@example.com', 'buyer-pass-1')
        sent = self.client.get('/api/broker/messages').get_json()['sent']
        self.assertEqual(len(sent), 2)
        note = self.client.get('/api/notifications')
        self.assertEqual(note.status_code, 200)
        if note.get_json()['notifications']:
            one = note.get_json()['notifications'][0]['id']
            self.assertEqual(self.client.delete(f'/api/notifications/{one}').status_code, 200)
        self.assertEqual(self.client.delete('/api/notifications').status_code, 200)
        self.assertEqual(self.client.get('/api/notifications').get_json()['notifications'], [])
        portal = self.client.get('/dashboard')
        self.assertNotIn(b'id="messagesDropdown"', portal.data)
        self.assertIn(b'href="/profile#messages"', portal.data)
        self.assertIn(b'id="nav-message-count"', portal.data)
        self.assertIn(b'id="messages-body" hidden', portal.data)
        self.assertIn(b'id="clear-messages"', portal.data)
        self.assertIn(b'id="clear-alerts"', portal.data)
        self.assertIn(b'Deleted messages', portal.data)
        self.assertIn(b'data-expand-message', portal.data)
        self.assertIn(b"article.querySelector('[data-message-body]')", portal.data)
        self.assertIn(b'mailto:', portal.data)
        self.assertIn(b'tel:', portal.data)
        self._login('buyer@example.com', 'buyer-pass-1')
        profile = self.client.get(f"/people/{self.broker['id']}")
        self.assertIn(b'Broker', profile.data)
        self.assertNotIn(b'name="contact_email"', profile.data)
        self.assertNotIn(b'Aircraft for sale', profile.data)
        listing_page = self.client.get(f'/listing/{listing_id}')
        self.assertIn(b'id="send-email"', listing_page.data)
        self.assertIn(b'id="send-phone"', listing_page.data)
        portal = self.client.get('/dashboard')
        self.assertIn(b'id="portal-email"', portal.data)
        self.assertIn(b'id="portal-phone"', portal.data)
        missing_phone = self.client.post(f"/api/brokers/{self.broker['id']}/messages", json={
            'kind': 'message', 'notes': 'Call me', 'contact_email': 'buyer@example.com', 'contact_phone': '',
        })
        self.assertEqual(missing_phone.status_code, 400)

    def test_settings_cover_password_email_and_privacy(self):
        self._login('seller@example.com', 'seller-pass-1')
        page = self.client.get('/settings')
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'General', page.data)
        self.assertIn(b'id="current-password"', page.data)
        self.assertIn(b'id="email-opt-in"', page.data)
        self.assertIn(b'We do not sell your personal information', page.data)
        self.assertIn(b'Download my information', page.data)
        self.assertIn(b'Delete account', page.data)
        token = page.data.split(b'name="csrf_token" value="', 1)[1].split(b'"', 1)[0]
        saved = self.client.post('/settings', data={
            'csrf_token': token.decode(),
            'action': 'email',
            'email_opt_in': '0',
        })
        self.assertEqual(saved.status_code, 200)
        self.assertIn(b'Email preference saved', saved.data)
        self.assertNotIn(b'id="email-opt-in" name="email_opt_in" type="checkbox" value="1" checked', saved.data)
        sent = []
        original = db_module._send_notice_email
        db_module._send_notice_email = lambda email, title, body: sent.append(email) or True
        try:
            db_module.notify_user(self.seller['id'], 'watch', 'Watch', 'A plane', '/', 'seller@example.com')
            self.assertEqual(sent, [])
            db_module.notify_user(self.seller['id'], 'billing', 'Payment', 'Card declined', '/', 'seller@example.com')
            self.assertEqual(sent, ['seller@example.com'])
        finally:
            db_module._send_notice_email = original
            db_module.set_email_opt_in(self.seller['id'], True)
        changed = self.client.post('/settings', data={
            'csrf_token': token.decode(),
            'action': 'password',
            'current_password': 'seller-pass-1',
            'new_password': 'seller-pass-2',
            'confirm_password': 'seller-pass-2',
        })
        self.assertEqual(changed.status_code, 200)
        self.assertIn(b'Password updated', changed.data)
        self.client.post('/settings', data={
            'csrf_token': token.decode(),
            'action': 'password',
            'current_password': 'seller-pass-2',
            'new_password': 'seller-pass-1',
            'confirm_password': 'seller-pass-1',
        })
        exported = self.client.get('/settings/download')
        self.assertEqual(exported.status_code, 200)
        self.assertNotIn('password_hash', exported.get_json()['account'])
        self.assertEqual(exported.get_json()['account']['email'], 'seller@example.com')

    def test_rewritten_payment_links_go_back_to_their_confirmation_page(self):
        import app as app_module
        previous_key = os.environ.get('STRIPE_SECRET_KEY')
        previous_base = os.environ.get('PUBLIC_BASE_URL')
        os.environ['STRIPE_SECRET_KEY'] = 'sk_test_returnpage'
        os.environ['PUBLIC_BASE_URL'] = 'https://jetschoolusa.com'
        app_module._payment_links_restored = False
        calls = []

        class Redirect:
            url = 'https://jetschoolusa.com/dashboard'

        class After:
            type = 'redirect'
            redirect = Redirect()

        class Subscription:
            trial_period_days = 14

        class Link:
            def __init__(self, url):
                self.id = 'plink_broker'
                self.url = url
                self.active = False
                self.after_completion = After()
                self.subscription_data = Subscription()
                self.payment_method_collection = 'if_required'

        page = type('Page', (), {'data': [Link('https://buy.stripe.com/7sYbIUgyoesqejI9AVgbm00')]})()
        try:
            with patch.object(app_module.stripe.PaymentLink, 'list', return_value=page), \
                 patch.object(app_module.stripe.PaymentLink, 'modify', side_effect=lambda *args, **kwargs: calls.append(kwargs)):
                app_module._restore_payment_links()
            self.assertEqual(calls, [])
            home = self.client.get('/')
            self.assertIn(b'aspect-ratio: 16 / 9', home.data)
            self.assertIn(b'repeat(3, minmax(0, 1fr))', home.data)
            self.assertIn(b'max-height: calc(5 * 2.35rem + 14px)', home.data)
            card = home.data[home.data.find(b'class="listing-face"'):]
            self.assertLess(card.find(b'class="listing-scroll"'), card.find(b'performance-scores-${index}'))
        finally:
            app_module._payment_links_restored = False
            if previous_key is None:
                os.environ.pop('STRIPE_SECRET_KEY', None)
            else:
                os.environ['STRIPE_SECRET_KEY'] = previous_key
            if previous_base is None:
                os.environ.pop('PUBLIC_BASE_URL', None)
            else:
                os.environ['PUBLIC_BASE_URL'] = previous_base

    def test_payment_link_reference_marks_the_public_listing_paid(self):
        self._login('seller@example.com', 'seller-pass-1')
        created = self.client.post('/api/listings', json=self._payload('Pay Link Jet', 'public'))
        listing_id = created.get_json()['id']
        db_module.set_user_listing_status(listing_id, 'unpaid')
        paid = self.client.post('/api/stripe/webhook', json={
            'id': 'evt_paylink_listing',
            'type': 'checkout.session.completed',
            'data': {'object': {
                'id': 'cs_paylink_listing',
                'status': 'complete',
                'payment_status': 'paid',
                'client_reference_id': f'listing-{listing_id}-user-{self.seller["id"]}',
                'metadata': {},
            }},
        })
        self.assertEqual(paid.status_code, 200, paid.get_json())
        row = db_module.get_listing_with_owner(listing_id)
        self.assertEqual(row.get('payment_status'), 'paid')
        self.assertEqual(row.get('status'), 'pending')
        stamped = self.client.post('/api/stripe/webhook', json={
            'id': 'evt_paylink_serial',
            'type': 'checkout.session.completed',
            'data': {'object': {
                'id': 'cs_paylink_serial',
                'status': 'complete',
                'payment_status': 'paid',
                'client_reference_id': f'listing-{listing_id}-user-{self.seller["id"]}-sn-5501',
                'metadata': {},
            }},
        })
        self.assertEqual(stamped.status_code, 200, stamped.get_json())
        self.assertEqual(db_module.get_listing_with_owner(listing_id).get('payment_status'), 'paid')

    def test_taking_a_listing_down_cancels_its_stripe_subscription(self):
        import app as app_module
        self._login('seller@example.com', 'seller-pass-1')
        created = self.client.post('/api/listings', json=self._payload('Cancel Fee Jet', 'public'))
        listing_id = created.get_json()['id']
        with db_module.get_session() as session:
            session.query(db_module.UserListing).filter(db_module.UserListing.id == listing_id).update(
                {'stripe_customer_id': 'cus_cancel_listing', 'payment_status': 'paid', 'status': 'active'},
                synchronize_session=False,
            )
        previous_key = os.environ.get('STRIPE_SECRET_KEY')
        os.environ['STRIPE_SECRET_KEY'] = 'sk_test_cancel_listing'
        deleted = []
        sessions = type('Page', (), {'data': [{
            'client_reference_id': f'listing-{listing_id}-user-{self.seller["id"]}-sn-5501',
            'subscription': 'sub_listing_cancel',
            'customer': 'cus_cancel_listing',
        }]})()
        subscriptions = type('Page', (), {'data': []})()
        try:
            with patch.object(app_module.stripe.checkout.Session, 'list', return_value=sessions), \
                 patch.object(app_module.stripe.Subscription, 'list', return_value=subscriptions), \
                 patch.object(app_module.stripe.Subscription, 'retrieve', return_value={'id': 'sub_listing_cancel', 'status': 'active'}), \
                 patch.object(app_module.stripe.Subscription, 'delete', side_effect=lambda sub_id, **kwargs: deleted.append(sub_id)):
                removed = self.client.delete(f'/api/listings/{listing_id}')
            self.assertEqual(removed.status_code, 409, removed.get_json())
            self.assertIn('Manage payment', removed.get_json().get('message') or '')
            self.assertEqual(deleted, [])
            row = db_module.get_listing_with_owner(listing_id)
            self.assertEqual(row.get('status'), 'active')
            db_module.save_listing_subscription(
                user_id=self.seller['id'], listing_id=listing_id, stripe_subscription_id='sub_listing_cancel',
                status='canceled', match_status='matched',
            )
            removed = self.client.delete(f'/api/listings/{listing_id}')
            self.assertEqual(removed.status_code, 200, removed.get_json())
            self.assertEqual(deleted, [])
            row = db_module.get_listing_with_owner(listing_id)
            self.assertEqual(row.get('status'), 'deleted')
        finally:
            if previous_key is None:
                os.environ.pop('STRIPE_SECRET_KEY', None)
            else:
                os.environ['STRIPE_SECRET_KEY'] = previous_key

    def test_paid_charge_matches_the_account_email_when_stripe_has_no_reference(self):
        person = self._signup('paid-match@example.com', 'seller-pass-1', 'seller')
        self._login(person['email'], 'seller-pass-1')
        created = self.client.post('/api/listings', json=self._payload('Matched Jet', 'public'))
        listing_id = created.get_json()['id']
        db_module.set_user_listing_status(listing_id, 'unpaid')
        paid = self.client.post('/api/stripe/webhook', json={
            'id': 'evt_email_match_listing',
            'type': 'checkout.session.completed',
            'data': {'object': {
                'id': 'cs_email_match',
                'status': 'complete',
                'payment_status': 'paid',
                'amount_total': 4999,
                'customer_email': person['email'],
                'customer': 'cus_email_match',
                'metadata': {},
            }},
        })
        self.assertEqual(paid.status_code, 200, paid.get_json())
        row = db_module.get_listing_with_owner(listing_id)
        self.assertNotEqual(row.get('payment_status'), 'paid')
        self._login('admin@example.com', 'admin-pass-1')
        page = self.client.get('/admin')
        self.assertIn(b'Search Stripe for ', page.data)
        listed = self.client.get('/api/admin/listings')
        match = next(item for item in listed.get_json()['listings'] if item['id'] == listing_id)
        self.assertEqual(match['stripe_reference'], f'listing-{listing_id}-user-{person["id"]}-sn-5501')
        self.assertNotEqual(match['payment_status'], 'paid')

    def test_two_open_listings_are_not_assigned_from_the_email_alone(self):
        person = self._signup('paid-two@example.com', 'seller-pass-1', 'seller')
        self._login(person['email'], 'seller-pass-1')
        first = self.client.post('/api/listings', json=self._payload('First Open Jet', 'public')).get_json()['id']
        second = self.client.post('/api/listings', json=self._payload('Second Open Jet', 'public')).get_json()['id']
        paid = self.client.post('/api/stripe/webhook', json={
            'id': 'evt_email_two_listings',
            'type': 'checkout.session.completed',
            'data': {'object': {
                'id': 'cs_email_two',
                'status': 'complete',
                'payment_status': 'paid',
                'amount_total': 4999,
                'customer_email': person['email'],
                'metadata': {},
            }},
        })
        self.assertEqual(paid.status_code, 200, paid.get_json())
        self.assertNotEqual(db_module.get_listing_with_owner(first).get('payment_status'), 'paid')
        self.assertNotEqual(db_module.get_listing_with_owner(second).get('payment_status'), 'paid')

    def test_reconcile_names_the_listing_on_the_stripe_customer(self):
        import app as app_module
        person = self._signup('paid-reconcile@example.com', 'seller-pass-1', 'seller')
        self._login(person['email'], 'seller-pass-1')
        listing_id = self.client.post('/api/listings', json=self._payload('Reconcile Jet', 'public')).get_json()['id']
        db_module.set_user_listing_status(listing_id, 'unpaid')
        app_module._checkouts_reconciled = False
        previous_key = os.environ.get('STRIPE_SECRET_KEY')
        os.environ['STRIPE_SECRET_KEY'] = 'sk_test_reconcile'
        calls = []
        page = type('Page', (), {'data': [{
            'id': 'cs_reconcile',
            'status': 'complete',
            'payment_status': 'paid',
            'client_reference_id': f'listing-{listing_id}-user-{person["id"]}',
            'customer': 'cus_reconcile',
            'subscription': 'sub_reconcile',
            'metadata': {},
        }]})()
        try:
            with patch.object(app_module.stripe.checkout.Session, 'list', return_value=page), \
                 patch.object(app_module.stripe.Customer, 'modify', side_effect=lambda *args, **kwargs: calls.append(kwargs)), \
                 patch.object(app_module.stripe.Subscription, 'modify', side_effect=lambda *args, **kwargs: calls.append(kwargs)):
                app_module._reconcile_paid_checkouts()
        finally:
            app_module._checkouts_reconciled = False
            if previous_key is None:
                os.environ.pop('STRIPE_SECRET_KEY', None)
            else:
                os.environ['STRIPE_SECRET_KEY'] = previous_key
        row = db_module.get_listing_with_owner(listing_id)
        self.assertEqual(row.get('payment_status'), 'paid')
        self.assertTrue(any('JetSchool listing' in (call.get('description') or '') for call in calls))
        self.assertTrue(any(call.get('metadata', {}).get('listing_id') == str(listing_id) for call in calls))

    def test_one_stripe_customer_is_reused_and_each_payment_sends_a_receipt(self):
        person = self._signup('one-customer@example.com', 'seller-pass-1', 'seller')
        self._login(person['email'], 'seller-pass-1')
        previous_flag = os.environ.get('REQUIRE_PAYMENT_FOR_LISTINGS')
        previous_key = os.environ.get('STRIPE_SECRET_KEY')
        os.environ['REQUIRE_PAYMENT_FOR_LISTINGS'] = 'true'
        os.environ['STRIPE_SECRET_KEY'] = 'sk_test_paylink'
        try:
            first = self.client.post('/api/listings', json=self._payload('One Customer Jet', 'public'))
            second = self.client.post('/api/listings', json=self._payload('Second Customer Jet', 'public'))
            first_id = first.get_json()['id']
            second_id = second.get_json()['id']
            pay1 = self.client.post(f'/api/listings/{first_id}/checkout')
            pay2 = self.client.post(f'/api/listings/{second_id}/checkout')
            self.assertEqual(pay1.status_code, 200, pay1.get_json())
            self.assertEqual(pay2.status_code, 200, pay2.get_json())
            self.assertIn(f'listing-{first_id}-user-{person["id"]}', pay1.get_json().get('url') or '')
            self.assertIn(f'listing-{second_id}-user-{person["id"]}', pay2.get_json().get('url') or '')
            self.assertNotEqual(pay1.get_json().get('url'), pay2.get_json().get('url'))
            sent = []
            original = db_module._send_notice_email
            db_module._send_notice_email = lambda email, title, body: sent.append((email, title, body)) or True
            try:
                first_invoice = self._stripe_event('evt_receipt_first', 'invoice.paid', {
                    'id': 'in_receipt_first',
                    'object': 'invoice',
                    'amount_paid': 4999,
                    'customer': 'cus_one',
                    'subscription': 'sub_listing_one',
                    'hosted_invoice_url': 'https://pay.stripe.com/invoice/receipt-first',
                    'metadata': {
                        'purpose': 'listing_fee',
                        'listing_id': str(first_id),
                        'user_id': str(person['id']),
                    },
                })
                renewal = self._stripe_event('evt_receipt_renewal', 'invoice.paid', {
                    'id': 'in_receipt_renewal',
                    'object': 'invoice',
                    'amount_paid': 4999,
                    'customer': 'cus_one',
                    'subscription': 'sub_listing_one',
                    'hosted_invoice_url': 'https://pay.stripe.com/invoice/receipt-renewal',
                    'metadata': {
                        'purpose': 'listing_fee',
                        'listing_id': str(first_id),
                        'user_id': str(person['id']),
                    },
                })
            finally:
                db_module._send_notice_email = original
            self.assertEqual(first_invoice.status_code, 200, first_invoice.get_json())
            self.assertEqual(renewal.status_code, 200, renewal.get_json())
            self.assertEqual([row[0] for row in sent], ['one-customer@example.com', 'one-customer@example.com'])
            self.assertIn('receipt-first', sent[0][2])
            self.assertIn('$49.99', sent[0][2])
            self.assertIn('receipt-renewal', sent[1][2])
            row = db_module.get_listing_with_owner(first_id)
            self.assertEqual(row.get('payment_status'), 'paid')
            self.assertEqual(row.get('stripe_customer_id'), 'cus_one')
        finally:
            if previous_flag is None:
                os.environ.pop('REQUIRE_PAYMENT_FOR_LISTINGS', None)
            else:
                os.environ['REQUIRE_PAYMENT_FOR_LISTINGS'] = previous_flag
            if previous_key is None:
                os.environ.pop('STRIPE_SECRET_KEY', None)
            else:
                os.environ['STRIPE_SECRET_KEY'] = previous_key

    def test_admin_can_view_message_and_delete_a_user_account(self):
        created = self.client.post('/api/auth/signup', json={
            'email': 'account-view@example.com',
            'password': 'account-pass-1',
            'first_name': 'Casey',
            'profile_role': 'buyer',
        })
        self.assertEqual(created.status_code, 201, created.get_json())
        user_id = created.get_json()['user']['id']
        self._login('buyer@example.com', 'buyer-pass-1')
        self.assertEqual(self.client.get(f'/api/admin/users/{user_id}').status_code, 403)
        self._login('admin@example.com', 'admin-pass-1')
        page = self.client.get('/admin')
        self.assertIn(b'id="user-search"', page.data)
        self.assertIn(b'id="user-role"', page.data)
        self.assertIn(b'Send message', page.data)
        self.assertIn(b'data-user-message="\' + broker.id', page.data)
        self.assertIn(b'data-user-message="\' + person.id', page.data)
        self.assertIn(b'data-user-message="\' + broker.id', page.data)
        self.assertIn(b'data-user-message="\' + l.owner.id', page.data)
        buyers = self.client.get('/api/admin/users?role=buyer&q=account-view')
        self.assertEqual(buyers.status_code, 200)
        emails = [row['email'] for row in buyers.get_json()['users']]
        self.assertEqual(emails, ['account-view@example.com'])
        self.assertEqual(self.client.get('/api/admin/users?role=seller&q=account-view').get_json()['users'], [])
        viewed = self.client.get(f'/api/admin/users/{user_id}')
        self.assertEqual(viewed.status_code, 200)
        self.assertEqual(viewed.get_json()['user']['email'], 'account-view@example.com')
        self.assertNotIn('password_hash', viewed.get_json()['user'])
        sent = self.client.post(
            f'/api/admin/users/{user_id}/message',
            json={'message': 'Please confirm the phone number on your account.'},
        )
        self.assertEqual(sent.status_code, 200, sent.get_json())
        self._login('account-view@example.com', 'account-pass-1')
        notes = self.client.get('/api/notifications').get_json()['notifications']
        self.assertTrue(any('phone number' in (note.get('body') or '') for note in notes))
        inbox = self.client.get('/api/broker/messages').get_json()['inbox']
        self.assertTrue(any('phone number' in (row.get('notes') or '') for row in inbox))
        self.assertTrue(any(row.get('aircraft_name') == 'JetSchool' for row in inbox))
        self._login('admin@example.com', 'admin-pass-1')
        blocked = self.client.delete(f'/api/admin/users/{self.admin["id"]}')
        self.assertEqual(blocked.status_code, 403)
        removed = self.client.delete(f'/api/admin/users/{user_id}')
        self.assertEqual(removed.status_code, 200, removed.get_json())
        self.assertIsNone(db_module.get_user_by_id(user_id))

    def test_listing_billing_is_owned_canceled_and_reconciled_without_stripe(self):
        import app as app_module
        person = self._signup('billing-owner@example.com', 'seller-pass-1', 'seller')
        self._login(person['email'], 'seller-pass-1')
        first = self.client.post('/api/listings', json=self._payload('Billing One', 'public')).get_json()['id']
        second = self.client.post('/api/listings', json=self._payload('Billing Two', 'public')).get_json()['id']
        db_module.admin_approve_listing_any(first, self.admin['id'])
        db_module.admin_approve_listing_any(second, self.admin['id'])
        paid = self._stripe_event('evt_bill_one', 'checkout.session.completed', {
            'id': 'cs_bill_one',
            'status': 'complete',
            'payment_status': 'paid',
            'client_reference_id': f'listing-{first}-user-{person["id"]}',
            'customer': 'cus_bill',
            'subscription': 'sub_bill_one',
            'metadata': {'purpose': 'listing_fee', 'listing_id': str(first), 'user_id': str(person['id'])},
        })
        self.assertEqual(paid.status_code, 200, paid.get_json())
        other = self._stripe_event('evt_bill_two', 'customer.subscription.created', {
            'id': 'sub_bill_two',
            'object': 'subscription',
            'status': 'active',
            'customer': 'cus_bill',
            'current_period_end': 1893456000,
            'metadata': {'purpose': 'listing_fee', 'listing_id': str(second), 'user_id': str(person['id'])},
            'items': {'data': [{'price': {'unit_amount': 4999, 'recurring': {'interval': 'month'}}}]},
        }, created=20)
        self.assertEqual(other.status_code, 200, other.get_json())
        rows = {row['listing_id']: row for row in db_module.list_listing_subscriptions(user_id=person['id'])}
        self.assertEqual(rows[first]['stripe_subscription_id'], 'sub_bill_one')
        self.assertEqual(rows[second]['stripe_subscription_id'], 'sub_bill_two')
        self.assertNotEqual(rows[first]['stripe_subscription_id'], rows[second]['stripe_subscription_id'])
        renewed = self._stripe_event('evt_bill_renew', 'invoice.paid', {
            'id': 'in_bill_renew',
            'object': 'invoice',
            'amount_paid': 4999,
            'customer': 'cus_bill',
            'subscription': 'sub_bill_one',
            'metadata': {'purpose': 'listing_fee', 'listing_id': str(first), 'user_id': str(person['id'])},
        }, created=30)
        self.assertEqual(renewed.status_code, 200, renewed.get_json())
        again = self._stripe_event('evt_bill_renew', 'invoice.paid', {
            'id': 'in_bill_renew',
            'object': 'invoice',
            'amount_paid': 4999,
            'customer': 'cus_bill',
            'subscription': 'sub_bill_one',
            'metadata': {'purpose': 'listing_fee', 'listing_id': str(first), 'user_id': str(person['id'])},
        }, created=30)
        self.assertEqual(again.get_json().get('duplicate'), True)
        self.assertEqual(len(db_module.list_billing_invoices(user_id=person['id'], stripe_subscription_id='sub_bill_one')), 1)
        failed = self._stripe_event('evt_bill_fail', 'invoice.payment_failed', {
            'id': 'in_bill_fail',
            'object': 'invoice',
            'amount_due': 4999,
            'customer': 'cus_bill',
            'subscription': 'sub_bill_two',
            'metadata': {'purpose': 'listing_fee', 'listing_id': str(second), 'user_id': str(person['id'])},
        }, created=40)
        self.assertEqual(failed.status_code, 200, failed.get_json())
        second_row = db_module.listing_subscription_by_stripe_id('sub_bill_two')
        self.assertEqual(second_row['status'], 'past_due')
        self.assertEqual(db_module.get_listing_with_owner(second)['status'], 'active')
        stale = self._stripe_event('evt_bill_stale', 'customer.subscription.updated', {
            'id': 'sub_bill_two',
            'object': 'subscription',
            'status': 'active',
            'customer': 'cus_bill',
            'metadata': {'purpose': 'listing_fee', 'listing_id': str(second), 'user_id': str(person['id'])},
        }, created=10)
        self.assertEqual(stale.status_code, 200, stale.get_json())
        self.assertEqual(db_module.listing_subscription_by_stripe_id('sub_bill_two')['status'], 'past_due')
        mine = self.client.get('/api/account/subscriptions')
        self.assertEqual(mine.status_code, 200, mine.get_json())
        self.assertEqual(len(mine.get_json()['subscriptions']), 2)
        self._login('buyer@example.com', 'buyer-pass-1')
        denied = self.client.post(f"/api/account/subscriptions/{rows[first]['id']}/cancel")
        self.assertEqual(denied.status_code, 404)
        self.assertEqual(db_module.get_listing_with_owner(first)['status'], 'active')
        self._login(person['email'], 'seller-pass-1')
        previous_key = os.environ.get('STRIPE_SECRET_KEY')
        os.environ['STRIPE_SECRET_KEY'] = 'sk_test_billing_cancel'
        try:
            with patch.object(app_module.stripe.Subscription, 'retrieve', side_effect=RuntimeError('stripe down')), \
                 patch.object(app_module.stripe.Subscription, 'delete', side_effect=AssertionError('delete must not run')):
                blocked = self.client.delete(f'/api/listings/{first}')
            self.assertEqual(blocked.status_code, 409, blocked.get_json())
            self.assertEqual(db_module.get_listing_with_owner(first)['status'], 'active')
            self.assertEqual(db_module.listing_subscription_by_stripe_id('sub_bill_one')['status'], 'active')
            removed = self.client.post(f"/api/account/subscriptions/{rows[first]['id']}/cancel")
            self.assertEqual(removed.status_code, 409, removed.get_json())
            self.assertIn('billing.stripe.com', removed.get_json().get('portal_url') or '')
            self.assertEqual(db_module.listing_subscription_by_stripe_id('sub_bill_one')['status'], 'active')
            db_module.save_listing_subscription(
                user_id=person['id'], listing_id=first, stripe_subscription_id='sub_bill_one',
                status='canceled', match_status='matched',
            )
            cleared = self.client.delete(f'/api/listings/{first}')
            self.assertEqual(cleared.status_code, 200, cleared.get_json())
            self.assertEqual(db_module.get_listing_with_owner(first)['status'], 'deleted')
            self.assertEqual(db_module.listing_subscription_by_stripe_id('sub_bill_one')['status'], 'canceled')
            self.assertTrue(db_module.list_billing_invoices(stripe_subscription_id='sub_bill_one'))
            with patch.object(app_module.stripe.Subscription, 'retrieve', return_value={'id': 'sub_bill_one', 'status': 'canceled'}), \
                 patch.object(app_module.stripe.Subscription, 'delete', side_effect=AssertionError('already canceled')):
                repeat = self.client.delete(f'/api/listings/{first}')
            self.assertIn(repeat.status_code, (200, 404))
        finally:
            if previous_key is None:
                os.environ.pop('STRIPE_SECRET_KEY', None)
            else:
                os.environ['STRIPE_SECRET_KEY'] = previous_key
        stranger = self._stripe_event('evt_bill_stranger', 'customer.subscription.created', {
            'id': 'sub_stranger',
            'object': 'subscription',
            'status': 'active',
            'customer': 'cus_stranger',
            'metadata': {},
        }, created=50)
        self.assertEqual(stranger.status_code, 200, stranger.get_json())
        stranger_row = db_module.listing_subscription_by_stripe_id('sub_stranger')
        self.assertEqual(stranger_row['match_status'], 'unmatched')
        self.assertIsNone(stranger_row['listing_id'])
        self._login('admin@example.com', 'admin-pass-1')
        page = self.client.get('/admin')
        self.assertIn(b'Billing', page.data)
        self.assertIn(b'My subscriptions', self.client.get('/dashboard').data)
        dashboard = self.client.get('/dashboard')
        self.assertIn(b'My billing', dashboard.data)
        self.assertIn(b'Manage payment', dashboard.data)
        self.assertIn(b'https://billing.stripe.com/p/login/7sYbIUgyoesqejI9AVgbm00', dashboard.data)
        billing = self.client.get('/api/admin/billing?q=sub_stranger')
        self.assertEqual(billing.status_code, 200, billing.get_json())
        self.assertTrue(any(row.get('stripe_subscription_id') == 'sub_stranger' for row in billing.get_json()['unmatched']))
        conflict = self.client.post('/api/admin/billing/match', json={
            'stripe_subscription_id': 'sub_stranger',
            'listing_id': second,
            'confirm': True,
        })
        self.assertEqual(conflict.status_code, 409, conflict.get_json())
        self._login(person['email'], 'seller-pass-1')
        third_response = self.client.post('/api/listings', json=self._payload('Billing Three', 'public'))
        third = third_response.get_json()['id']
        self._login('admin@example.com', 'admin-pass-1')
        matched = self.client.post('/api/admin/billing/match', json={
            'stripe_subscription_id': 'sub_stranger',
            'listing_id': third,
            'confirm': True,
        })
        self.assertEqual(matched.status_code, 200, matched.get_json())
        self.assertEqual(db_module.listing_subscription_by_stripe_id('sub_stranger')['listing_id'], third)
        self.assertEqual(db_module.listing_subscription_by_stripe_id('sub_stranger')['user_id'], person['id'])
        os.environ['STRIPE_SECRET_KEY'] = 'sk_test_billing_reconcile'
        try:
            page = type('Page', (), {'data': [{
                'id': 'sub_remote_only',
                'status': 'active',
                'customer': 'cus_remote',
                'metadata': {'purpose': 'listing_fee', 'listing_id': str(second), 'user_id': str(person['id'])},
                'items': {'data': [{'price': {'unit_amount': 4999, 'recurring': {'interval': 'month'}}}]},
            }], 'has_more': False})()
            with patch.object(app_module.stripe.Subscription, 'list', return_value=page):
                reconciled = self.client.post('/api/admin/billing/reconcile')
            self.assertEqual(reconciled.status_code, 200, reconciled.get_json())
            self.assertEqual(reconciled.get_json()['canceled'], 0)
            self.assertGreaterEqual(reconciled.get_json()['matched'], 1)
        finally:
            os.environ.pop('STRIPE_SECRET_KEY', None)
        with db_module.get_session() as session:
            record = session.query(db_module.ListingSubscription).filter(
                db_module.ListingSubscription.stripe_subscription_id == 'sub_bill_two'
            ).first()
            record.grace_until = datetime(2020, 1, 1)
        db_module.enforce_listing_grace()
        self.assertEqual(db_module.get_listing_with_owner(second)['status'], 'suspended')
        self.assertIsNotNone(db_module.listing_subscription_by_stripe_id('sub_bill_two'))

    def test_billing_keeps_the_agreed_price_and_recovers_a_missed_webhook(self):
        import app as app_module
        db_module.save_listing_subscription(
            user_id=self.seller['id'], stripe_subscription_id='sub_agreed', status='active',
            amount_cents=1499, agreed_amount_cents=1499, billing_interval='month', match_status='matched',
        )
        db_module.save_listing_subscription(
            stripe_subscription_id='sub_agreed', amount_cents=4999, status='active', event_created=5,
        )
        agreed = db_module.listing_subscription_by_stripe_id('sub_agreed')
        self.assertEqual(agreed['agreed_amount_cents'], 1499)
        self.assertEqual(agreed['amount_cents'], 4999)
        self.assertEqual(db_module.monthly_recurring_cents() >= 1499, True)
        self._login('seller@example.com', 'seller-pass-1')
        created = self.client.post('/api/listings', json=self._payload('Period Jet', 'public'))
        listing_id = created.get_json()['id']
        period = self._stripe_event('evt_period_item', 'customer.subscription.created', {
            'id': 'sub_period_item',
            'object': 'subscription',
            'status': 'active',
            'customer': 'cus_period',
            'metadata': {
                'jetschool_billing_type': 'aircraft_listing',
                'jetschool_listing_id': str(listing_id),
                'jetschool_user_id': str(self.seller['id']),
            },
            'items': {'data': [{
                'current_period_start': 1790000000,
                'current_period_end': 1800000000,
                'price': {'id': 'price_promo', 'product': 'prod_listing', 'unit_amount': 1499, 'recurring': {'interval': 'month'}},
            }]},
        }, created=60)
        self.assertEqual(period.status_code, 200, period.get_json())
        stored = db_module.listing_subscription_by_stripe_id('sub_period_item')
        self.assertEqual(stored['listing_id'], listing_id)
        self.assertEqual(stored['stripe_price_id'], 'price_promo')
        self.assertIsNotNone(stored['current_period_end'])
        self.assertEqual(stored['agreed_amount_cents'], 1499)
        failed_start = self._stripe_event('evt_async_fail', 'checkout.session.async_payment_failed', {
            'id': 'cs_async_fail',
            'payment_status': 'unpaid',
            'metadata': {'purpose': 'listing_fee', 'listing_id': str(listing_id), 'user_id': str(self.seller['id'])},
        })
        self.assertEqual(failed_start.status_code, 200, failed_start.get_json())
        self.assertNotEqual(db_module.get_listing_with_owner(listing_id)['payment_status'], 'paid')
        action = self._stripe_event('evt_action', 'invoice.payment_action_required', {
            'id': 'in_action',
            'object': 'invoice',
            'amount_due': 1499,
            'customer': 'cus_period',
            'subscription': 'sub_period_item',
            'metadata': {'purpose': 'listing_fee', 'listing_id': str(listing_id), 'user_id': str(self.seller['id'])},
        }, created=70)
        self.assertEqual(action.status_code, 200, action.get_json())
        self.assertEqual(db_module.listing_subscription_by_stripe_id('sub_period_item')['status'], 'active')
        expired = self._stripe_event('evt_expired', 'checkout.session.expired', {
            'id': 'cs_expired_only',
            'metadata': {'purpose': 'listing_fee', 'listing_id': str(listing_id), 'user_id': str(self.seller['id'])},
        })
        self.assertEqual(expired.status_code, 200, expired.get_json())
        self.assertEqual(db_module.listing_subscription_by_stripe_id('sub_period_item')['status'], 'active')
        with patch.object(db_module, 'save_listing_subscription', side_effect=RuntimeError('db down')):
            broken = self._stripe_event('evt_retry_store', 'customer.subscription.updated', {
                'id': 'sub_period_item',
                'object': 'subscription',
                'status': 'active',
                'customer': 'cus_period',
                'metadata': {'purpose': 'listing_fee', 'listing_id': str(listing_id), 'user_id': str(self.seller['id'])},
            }, created=80)
        self.assertEqual(broken.status_code, 500, broken.get_json())
        retried = self._stripe_event('evt_retry_store', 'customer.subscription.updated', {
            'id': 'sub_period_item',
            'object': 'subscription',
            'status': 'active',
            'customer': 'cus_period',
            'metadata': {'purpose': 'listing_fee', 'listing_id': str(listing_id), 'user_id': str(self.seller['id'])},
        }, created=80)
        self.assertEqual(retried.status_code, 200, retried.get_json())
        self.assertNotEqual(retried.get_json().get('duplicate'), True)
        db_module.admin_approve_listing_any(listing_id, self.admin['id'])
        hidden = self.client.post(f'/api/listings/{listing_id}/pause')
        self.assertEqual(hidden.status_code, 200, hidden.get_json())
        self.assertTrue(db_module.get_listing_with_owner(listing_id)['paused'])
        self.assertEqual(db_module.listing_subscription_by_stripe_id('sub_period_item')['status'], 'active')
        self.assertEqual(self.client.get(f'/listing/{listing_id}').status_code, 404)
        shown = self.client.post(f'/api/listings/{listing_id}/resume')
        self.assertEqual(shown.status_code, 200, shown.get_json())
        other = self.client.post('/api/listings', json=self._payload('Keep Jet', 'public')).get_json()['id']
        db_module.save_listing_subscription(
            user_id=self.seller['id'], listing_id=other, stripe_subscription_id='sub_keep_jet',
            status='active', amount_cents=1499, match_status='matched',
        )
        previous_key = os.environ.get('STRIPE_SECRET_KEY')
        os.environ['STRIPE_SECRET_KEY'] = 'sk_test_sold'
        try:
            with patch.object(app_module.stripe.Subscription, 'retrieve', return_value={'id': 'sub_period_item', 'status': 'active'}), \
                 patch.object(app_module.stripe.Subscription, 'delete', side_effect=AssertionError('do not delete')):
                sold = self.client.post(f'/api/listings/{listing_id}/sold')
            self.assertEqual(sold.status_code, 409, sold.get_json())
            self.assertEqual(db_module.get_listing_with_owner(listing_id)['status'], 'active')
            self.assertEqual(db_module.listing_subscription_by_stripe_id('sub_period_item')['status'], 'active')
            self.assertEqual(db_module.listing_subscription_by_stripe_id('sub_keep_jet')['status'], 'active')
            db_module.save_listing_subscription(
                user_id=self.seller['id'], listing_id=listing_id, stripe_subscription_id='sub_period_item',
                status='canceled', match_status='matched',
            )
            sold = self.client.post(f'/api/listings/{listing_id}/sold')
            self.assertEqual(sold.status_code, 200, sold.get_json())
            self.assertEqual(db_module.get_listing_with_owner(listing_id)['status'], 'sold')
            sold_notes = db_module.list_notifications(self.admin['id'])
            self.assertTrue(any((note.get('title') or '').startswith('Sold aircraft to approve') for note in sold_notes))
            self.assertEqual(db_module.listing_subscription_by_stripe_id('sub_keep_jet')['status'], 'active')
            again = self.client.delete(f'/api/listings/{listing_id}')
            self.assertEqual(again.status_code, 200, again.get_json())
            removed_notes = db_module.list_notifications(self.admin['id'])
            self.assertTrue(any((note.get('title') or '').startswith('Deleted aircraft to approve') for note in removed_notes))
        finally:
            if previous_key is None:
                os.environ.pop('STRIPE_SECRET_KEY', None)
            else:
                os.environ['STRIPE_SECRET_KEY'] = previous_key
        self.assertNotIn('sub_keep_jet', [row['stripe_subscription_id'] for row in db_module.list_listing_subscriptions() if row.get('status') == 'canceled' and row.get('stripe_subscription_id') == 'sub_keep_jet'])
        page = self.client.get('/dashboard')
        self.assertIn(b'My billing', page.data)
        self._login('admin@example.com', 'admin-pass-1')
        self.assertIn(b'Reconciliation', self.client.get('/admin').data)
        self.assertIsNone(self.client.post('/api/internal/billing/reconcile').get_json().get('ok'))
        os.environ['BILLING_RECONCILE_TOKEN'] = 'reconcile-test-token'
        try:
            denied = self.client.post('/api/internal/billing/reconcile', headers={'X-Billing-Reconcile-Token': 'nope'})
            self.assertEqual(denied.status_code, 404)
        finally:
            os.environ.pop('BILLING_RECONCILE_TOKEN', None)
        self.assertTrue(hasattr(db_module.ListingSubscription, 'agreed_amount_cents'))
        self.assertTrue(hasattr(db_module.ListingSubscription, 'stripe_price_id'))

    def _stripe_event(self, event_id, event_type, obj, created=None):
        payload = {'id': event_id, 'type': event_type, 'data': {'object': obj}}
        if created is not None:
            payload['created'] = created
        return self.client.post('/api/stripe/webhook', json=payload)

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
            'serial_number': '5501',
        }


if __name__ == '__main__':
    unittest.main()
