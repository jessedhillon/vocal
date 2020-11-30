from enum import Enum

from vocal.api.constants import ISO4217Currency, PaymentDemandType, PeriodicPaymentDemandPeriod,\
        SubscriptionPlanStatus

class SubscriptionPlanStatus(Enum):
    Active = 'active'
    Inactive = 'inactive'


class PaymentDemandType(Enum):
    Periodic = 'periodic'
    Immediate = 'immediate'
    PayAsYouGo = 'pay-go'


class PeriodicPaymentDemandPeriod(Enum):
    Daily = 'daily'
    Weekly = 'weekly'
    Monthly = 'monthly'
    Quarterly = 'quarterly'
    Annually = 'annually'
