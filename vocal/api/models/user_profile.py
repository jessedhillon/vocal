from enum import Enum


class UserRole(Enum):
    Superuser = 'superuser'
    Manager = 'manager'
    Creator = 'creator'
    Member = 'member'
    Subscriber = 'subscriber'


class ContactMethodType(Enum):
    Email = 'email'
    Phone = 'phone'
    Address = 'address'
