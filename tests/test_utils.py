from datetime import timedelta

from graphql_jwt import exceptions, utils
from graphql_jwt.settings import jwt_settings

from .compat import mock
from .decorators import override_jwt_settings
from .testcases import TestCase


class JWTPayloadTests(TestCase):

    @mock.patch('django.contrib.auth.models.User.get_username',
                return_value=mock.Mock(pk='test'))
    def test_foreign_key_pk(self, *args):
        payload = utils.jwt_payload(self.user)
        username = jwt_settings.JWT_PAYLOAD_GET_USERNAME_HANDLER(payload)

        self.assertEqual(username, 'test')

    @override_jwt_settings(JWT_AUDIENCE='test')
    def test_audience(self):
        payload = utils.jwt_payload(self.user)
        self.assertEqual(payload['aud'], 'test')

    @override_jwt_settings(JWT_ISSUER='test')
    def test_issuer(self):
        payload = utils.jwt_payload(self.user)
        self.assertEqual(payload['iss'], 'test')


class GetAuthorizationHeaderTests(TestCase):

    def test_get_header(self):
        headers = {
            jwt_settings.JWT_AUTH_HEADER: '{} {}'.format(
                jwt_settings.JWT_AUTH_HEADER_PREFIX,
                self.token),
        }

        request = self.request_factory.get('/', **headers)
        authorization_header = utils.get_authorization_header(request)

        self.assertEqual(authorization_header, self.token)

    def test_invalid_header_prefix(self):
        headers = {
            jwt_settings.JWT_AUTH_HEADER: 'INVALID token',
        }

        request = self.request_factory.get('/', **headers)
        authorization_header = utils.get_authorization_header(request)

        self.assertIsNone(authorization_header)


class GetCredentialsTests(TestCase):

    @override_jwt_settings(JWT_ALLOW_ARGUMENT=True)
    def test_argument_allowed(self):
        kwargs = {
            jwt_settings.JWT_ARGUMENT_NAME: self.token,
        }

        request = self.request_factory.get('/')
        credentials = utils.get_credentials(request, **kwargs)

        self.assertEqual(credentials, self.token)

    @override_jwt_settings(JWT_ALLOW_ARGUMENT=True)
    def test_input_argument(self):
        kwargs = {
            'input': {
                jwt_settings.JWT_ARGUMENT_NAME: self.token,
            },
        }

        request = self.request_factory.get('/')
        credentials = utils.get_credentials(request, **kwargs)

        self.assertEqual(credentials, self.token)

    @override_jwt_settings(JWT_ALLOW_ARGUMENT=True)
    def test_missing_argument(self):
        request = self.request_factory.get('/')
        credentials = utils.get_credentials(request)

        self.assertIsNone(credentials)


class GetPayloadTests(TestCase):

    @override_jwt_settings(
        JWT_VERIFY_EXPIRATION=True,
        JWT_EXPIRATION_DELTA=timedelta(seconds=-1))
    def test_expired_signature(self):
        payload = utils.jwt_payload(self.user)
        token = utils.jwt_encode(payload)

        with self.assertRaises(exceptions.JSONWebTokenExpired):
            utils.get_payload(token)

    def test_decode_audience_missing(self):
        payload = utils.jwt_payload(self.user)
        token = utils.jwt_encode(payload)

        with override_jwt_settings(JWT_AUDIENCE='test'):
            with self.assertRaises(exceptions.JSONWebTokenError):
                utils.get_payload(token)

    def test_decode_error(self):
        with self.assertRaises(exceptions.JSONWebTokenError):
            utils.get_payload('invalid')


class GetUserByNaturalKeyTests(TestCase):

    def test_user_does_not_exists(self):
        user = utils.get_user_by_natural_key(0)
        self.assertIsNone(user)


class GetUserByPayloadTests(TestCase):

    def test_user_by_invalid_payload(self):
        with self.assertRaises(exceptions.JSONWebTokenError):
            utils.get_user_by_payload({})

    @mock.patch('django.contrib.auth.models.User.is_active',
                new_callable=mock.PropertyMock,
                return_value=False)
    def test_user_disabled_by_payload(self, *args):
        payload = utils.jwt_payload(self.user)

        with self.assertRaises(exceptions.JSONWebTokenError):
            utils.get_user_by_payload(payload)
