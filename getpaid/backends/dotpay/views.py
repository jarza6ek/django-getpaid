import logging

from django import http
from django.urls import reverse
from django.views.generic.base import View
from django.views.generic.detail import DetailView

from getpaid.backends.dotpay import PaymentProcessor
from getpaid.models import Payment

logger = logging.getLogger('getpaid.backends.dotpay')


class OnlineView(View):
    """
    This View answers on PayU online request that is acknowledge of payment
    status change.

    The most important logic of this view is delegated to ``PaymentProcessor.online()`` method
    """
    def post(self, request, *args, **kwargs):

        try:
            params = {
                'id': request.POST['id'],
                'control': request.POST['control'],
                'operation_amount': request.POST['operation_amount'],
                'signature': request.POST['signature'],
                'operation_status': request.POST['operation_status'],
                'operation_number': request.POST.get('operation_number', ''),
                'operation_type': request.POST.get('operation_type', ''),
                'operation_currency': request.POST.get('operation_currency', 'PLN'),
                'operation_withdrawal_amount': request.POST.get('operation_withdrawal_amount', ''),
                'operation_commission_amount': request.POST.get('operation_commission_amount', ''),
                'is_completed': request.POST.get('is_completed', ''),
                'operation_original_amount': request.POST.get('operation_original_amount', ''),
                'operation_original_currency': request.POST.get('operation_original_currency', ''),
                'operation_datetime': request.POST.get('operation_datetime', ''),
                'operation_related_number': request.POST.get('operation_related_number', ''),
                'description': request.POST.get('description', ''),
                'email': request.POST.get('email', ''),
                'p_info': request.POST.get('p_info', ''),
                'p_email': request.POST.get('p_email', ''),
                'credit_card_issuer_identification_number': request.POST.get('credit_card_issuer_identification_number',
                                                                             ''),
                'credit_card_masked_number': request.POST.get('credit_card_masked_number', ''),
                'credit_card_expiration_year': request.POST.get('credit_card_expiration_year', ''),
                'credit_card_expiration_month': request.POST.get('credit_card_expiration_month', ''),
                'credit_card_brand_codename': request.POST.get('credit_card_brand_codename', ''),
                'credit_card_brand_code': request.POST.get('credit_card_brand_code', ''),
                'credit_card_unique_identifier': request.POST.get('credit_card_unique_identifier', ''),
                'credit_card_id': request.POST.get('credit_card_id', ''),
                'channel': request.POST.get('channel', ''),
                'channel_country': request.POST.get('channel_country', ''),
                'geoip_country': request.POST.get('geoip_country', ''),
            }
        except KeyError:
            logger.warning('Got malformed POST request: %s' % str(request.POST))
            return http.HttpResponseBadRequest('MALFORMED')

        status = PaymentProcessor.online(params, ip=request.META['REMOTE_ADDR'])
        return http.HttpResponse(status)


class ReturnView(DetailView):
    """
    This view just redirects to standard backend success or failure link.
    """
    model = Payment

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def render_to_response(self, context, **response_kwargs):
        if self.request.POST['status'] == 'OK':
            return http.HttpResponseRedirect(reverse('getpaid:success-fallback', kwargs={'pk': self.object.pk}))
        else:
            return http.HttpResponseRedirect(reverse('getpaid:failure-fallback', kwargs={'pk': self.object.pk}))
