import calendar
import re as regex
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Literal, NewType, Optional, Union

from vocal.constants import ISO3166Country, PaymentMethodType
from vocal.locale.en_us import USState, USAddress


CustomerProfileID = NewType('CustomerProfileID', str)
RecurringChargeID = NewType('RecurringChargeID', str)
PaymentMethodID = NewType('PaymentMethodID', str)


class ACHAccountType(Enum):
    Checking = 'checking'
    Savings = 'savings'
    BusinessChecking = 'business_checking'
    BusinessSavings = 'business_savings'


@dataclass
class PaymentCredential:
    method_type: PaymentMethodType
    method_family: str

    @property
    def expire_after_date(self) -> Optional[datetime]:
        return None

    @property
    def display_name(self):
        raise NotImplementedError()

    @property
    def safe_account_number_fragment(self):
        raise NotImplementedError()

    @classmethod
    def unmarshal_request(cls, body: dict) -> 'PaymentCredential':
        method_type = PaymentMethodType(body['methodType'])
        if method_type is PaymentMethodType.CreditCard:
            return CreditCardPaymentCredential.unmarshal_request(body)
        elif method_type is PaymentMethodType.EFT:
            if body['methodFamily'] == 'ACH':
                return ACHPaymentCredential.unmarshal_request(body)
            else:
                raise ValueError(body['methodFamily'])
        raise ValueError(body['methodType'])


@dataclass
class CreditCardPaymentCredential(PaymentCredential):
    _family_names = {
        'visa': "Visa",
        'mastercard': "Mastercard",
        'amex': "American Express",
        'dc': "Diner's Club",
        'discover': "Disover",
    }

    method_type: Literal[PaymentMethodType.CreditCard]
    method_family: Optional[str]
    card_number: str
    exp_month: int
    exp_year: int
    cvv: str

    @property
    def expire_after_date(self):
        eom = calendar.monthrange(self.exp_year, self.exp_month)
        return datetime(self.exp_year, self.exp_month, eom[1])

    @property
    def _family_name(self) -> str:
        return self._family_names.get(self.method_family, None)

    @property
    def display_name(self) -> str:
        return f'{self._family_name} {self.safe_account_number_fragment}'

    @property
    def safe_account_number_fragment(self) -> str:
        return self.card_number[-4:]

    @staticmethod
    def family_from_card_number(card_number: str) -> str:
        if regex.match('^4[0-9]{6,}$', card_number):
            return 'visa'
        if regex.match('^5[1-5][0-9]{5,}|222[1-9][0-9]{3,}'
                    '|22[3-9][0-9]{4,}|2[3-6][0-9]{5,}'
                    '|27[01][0-9]{4,}|2720[0-9]{3,}$', card_number):
            return 'mastercard'
        if regex.match('^3[47][0-9]{5,}$', card_number):
            return 'amex'
        if regex.match('^3(?:0[0-5]|[68][0-9])[0-9]{4,}$', card_number):
            return 'dc'
        if regex.match('^6(?:011|5[0-9]{2})[0-9]{3,}$', card_number):
            return 'discover'
        return None

    @classmethod
    def unmarshal_request(cls, body: dict) -> 'CreditCardPaymentCredential':
        number = body['cardNumber']
        return CreditCardPaymentCredential(method_type=PaymentMethodType.CreditCard,
                                           method_family=cls.family_from_card_number(number),
                                           card_number=number,
                                           exp_month=int(body['expMonth']),
                                           exp_year=int(body['expYear']),
                                           cvv=body['cvv'])


@dataclass
class ACHPaymentCredential(PaymentCredential):
    method_type: Literal[PaymentMethodType.EFT]
    method_family: Literal['ACH']
    account_number: str
    routing_number: str
    account_type: ACHAccountType

    @property
    def display_name(self) -> str:
        # TODO: lookup RTN somewhere
        return f"Routing: {self.routing_number}, Account: ****{self.safe_account_number_fragment}"

    @property
    def safe_account_number(self) -> str:
        return self.account_number[-4:]

    @classmethod
    def unmarshal_request(cls, body: dict) -> 'ACHPaymentCredential':
        return ACHPaymentCredential(method_type=PaymentMethodType.EFT,
                                    method_family='ACH',
                                    account_type=ACHAccountType(body['accountType']),
                                    account_number=body['accountNumber'],
                                    routing_number=body['routingNumber'])
