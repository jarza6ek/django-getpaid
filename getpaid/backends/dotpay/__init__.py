# Implemented using dotpay documentation version 1.49.11.1
# https://ssl.dotpay.pl/s2/login/cloudfs1/magellan_media/common_file/dotpay_instrukcja_techniczna_implementacji_platnosci.pdf

import datetime
import hashlib
import logging
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse
from django.utils import six
from django.utils.timezone import utc
from django.utils.translation import ugettext_lazy as _
from six.moves.urllib.parse import urlencode

from getpaid import signals
from getpaid.backends import PaymentProcessorBase
from getpaid.utils import get_domain

logger = logging.getLogger('getpaid.backends.dotpay')


class DotpayTransactionStatus:
    NEW = 'new'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    REJECTED = 'rejected'
    PROCESSING_REALIZATION_WAITING = 'processing_realization_waiting'
    PROCESSING_REALIZATION = 'processing_realization'


class PaymentProcessor(PaymentProcessorBase):
    BACKEND = 'getpaid.backends.dotpay'
    BACKEND_NAME = _('Dotpay')
    BACKEND_ACCEPTED_CURRENCY = ('PLN', 'EUR', 'USD', 'GBP', 'JPY', 'CZK', 'SEK', 'UAH', 'RON')
    BACKEND_LOGO_URL = 'getpaid/backends/dotpay/dotpay_logo.png'

    _ALLOWED_IP = ('195.150.9.37',)
    _ACCEPTED_LANGS = ('pl', 'en', 'de', 'it', 'fr', 'es', 'cs', 'ru', 'hu', 'ro')
    _GATEWAY_URL = 'https://ssl.dotpay.pl/t2/'
    _ONLINE_SIG_FIELDS = (
        'id', 'operation_number', 'operation_type', 'operation_status', 'operation_amount', 'operation_currency',
        'operation_withdrawal_amount', 'operation_commission_amount', 'is_completed', 'operation_original_amount',
        'operation_original_currency', 'operation_datetime', 'operation_related_number', 'control', 'description',
        'email', 'p_info', 'p_email', 'credit_card_issuer_identification_number', 'credit_card_masked_number',
        'credit_card_expiration_year', 'credit_card_expiration_month', 'credit_card_brand_codename',
        'credit_card_brand_code', 'credit_card_unique_identifier', 'credit_card_id', 'channel', 'channel_country',
        'geoip_country')

    @staticmethod
    def compute_sig(params, fields, PIN):
        text = PIN + ("".join(map(lambda field: params.get(field, ''), fields)))
        return hashlib.sha256(text.encode('utf8')).hexdigest()

    @classmethod
    def online(cls, params, ip):

        allowed_ip = cls.get_backend_setting('allowed_ip', cls._ALLOWED_IP)

        if len(allowed_ip) != 0 and ip not in allowed_ip:
            logger.warning('Got message from not allowed IP %s' % str(ip))
            return 'IP ERR'

        PIN = cls.get_backend_setting('PIN', '')

        if params['signature'] != cls.compute_sig(params, cls._ONLINE_SIG_FIELDS, PIN):
            logger.warning('Got message with wrong sig, %s' % str(params))
            return u'SIG ERR'

        try:
            params['id'] = int(params['id'])
        except ValueError:
            return u'ID ERR'
        if params['id'] != int(cls.get_backend_setting('id')):
            return u'ID ERR'

        from getpaid.models import Payment
        try:
            payment = Payment.objects.get(pk=int(params['control']))
        except (ValueError, Payment.DoesNotExist):
            logger.error('Got message for non existing Payment, %s' % str(params))
            return u'PAYMENT ERR'

        payment.external_id = params.get('operation_number', '')
        payment.description = params.get('email', '')

        amount = params.get('operation_amount')
        currency = params.get('operation_currency')
        commission_amount = params.get('operation_commission_amount')

        if currency != payment.currency.upper():
            logger.error('Got message with wrong currency, %s' % str(params))
            return u'CURRENCY ERR'

        if params['operation_status'] == DotpayTransactionStatus.COMPLETED:
            payment.amount_paid = Decimal(amount)
            try:
                payment.commission_amount = Decimal(commission_amount)
            except InvalidOperation:
                logger.info('No commission amount information in message, %s' % str(params))
            payment.paid_on = datetime.datetime.utcnow().replace(tzinfo=utc)
            try:
                if payment.amount <= Decimal(amount):
                    # Amount is correct or it is overpaid
                    payment.change_status('paid')
                else:
                    payment.change_status('partially_paid')
            except InvalidOperation:
                logger.error('Got message with malformed amount value, %s' % str(params))
                return u'AMOUNT ERR'
        elif params['operation_status'] == DotpayTransactionStatus.NEW:
            payment.change_status('new')
        elif params['operation_status'] in [DotpayTransactionStatus.PROCESSING,
                                            DotpayTransactionStatus.PROCESSING_REALIZATION_WAITING,
                                            DotpayTransactionStatus.PROCESSING_REALIZATION]:
            payment.change_status('in_progress')
        elif params['operation_status'] == DotpayTransactionStatus.REJECTED:
            payment.change_status('cancelled')
        else:
            payment.change_status('failed')

        return u'OK'

    def get_URLC(self):
        urlc = reverse('getpaid:dotpay:online')
        if self.get_backend_setting('force_ssl', False):
            return u'https://%s%s' % (get_domain(), urlc)
        else:
            return u'http://%s%s' % (get_domain(), urlc)

    def get_URL(self, pk):
        url = reverse('getpaid:dotpay:return', kwargs={'pk': pk})
        if self.get_backend_setting('force_ssl', False):
            return u'https://%s%s' % (get_domain(), url)
        else:
            return u'http://%s%s' % (get_domain(), url)

    def get_gateway_url(self, request):
        """
        Routes a payment to Gateway, should return URL for redirection.
        """
        params = {
            'id': self.get_backend_setting('id'),
            'description': self.get_order_description(self.payment, self.payment.order),
            'amount': self.payment.amount,
            'currency': self.payment.currency,
            'type': 0,  # 0 = show "return" button after finished payment
            'control': self.payment.pk,
            'URL': self.get_URL(self.payment.pk),
            'URLC': self.get_URLC(),
            'api_version': 'dev',
        }

        user_data = {
            'email': None,
            'lang': None,
        }
        signals.user_data_query.send(sender=None, order=self.payment.order, user_data=user_data)

        if user_data['email']:
            params['email'] = user_data['email']

        if user_data['lang'] and user_data['lang'].lower() in self._ACCEPTED_LANGS:
            params['lang'] = user_data['lang'].lower()
        elif self.get_backend_setting('lang', False
                                      ) and self.get_backend_setting('lang').lower() in self._ACCEPTED_LANGS:
            params['lang'] = self.get_backend_setting('lang').lower()

        if self.get_backend_setting('onlinetransfer', False):
            params['onlinetransfer'] = 1
        if self.get_backend_setting('p_email', False):
            params['p_email'] = self.get_backend_setting('p_email')
        if self.get_backend_setting('p_info', False):
            params['p_info'] = self.get_backend_setting('p_info')
        if self.get_backend_setting('tax', False):
            params['tax'] = 1

        gateway_url = self.get_backend_setting('gateway_url', self._GATEWAY_URL)

        if self.get_backend_setting('method', 'get').lower() == 'post':
            return gateway_url, 'POST', params
        elif self.get_backend_setting('method', 'get').lower() == 'get':
            for key in params.keys():
                params[key] = six.text_type(params[key]).encode('utf-8')
            return gateway_url + '?' + urlencode(params), "GET", {}
        else:
            raise ImproperlyConfigured('Dotpay payment backend accepts only GET or POST')
