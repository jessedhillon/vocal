from datetime import datetime
from uuid import UUID
from typing import Optional, Union

import sqlalchemy.exc
from sqlalchemy import func as f
from sqlalchemy.engine.result import Result
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.sql.expression import alias, exists, false, join, literal, select, true

from vocal.constants import ContactMethodType, PaymentMethodType, PaymentMethodStatus, UserRole
from vocal.api.storage.record import UserProfileRecord, ContactMethodRecord,\
        PaymentMethodRecord, PaymentProfileRecord, Recordset
from vocal.api.storage.sql import user_profile, user_auth, contact_method, email_contact_method,\
        phone_contact_method, payment_profile, payment_method
from vocal.api.util import operation


@operation(UserProfileRecord, single_result=True, default=None)
async def get_user_profile(session: AsyncSession, user_profile_id: UUID=None,
                           email_address: str=None, phone_number: str=None
                           ) -> Result:
    if not any([user_profile_id, email_address, phone_number]):
        raise ValueError("one of user_profile_id, email_address, phone_number are required")

    email = contact_method.alias()
    phone = contact_method.alias()
    q = select(user_profile.c.user_profile_id,
               user_profile.c.display_name,
               user_profile.c.created_at,
               user_profile.c.name,
               user_profile.c.role,
               email.c.contact_method_id,
               email.c.verified,
               email_contact_method.c.email_address,
               phone.c.contact_method_id,
               phone.c.verified,
               phone_contact_method.c.phone_number).\
        select_from(user_profile).\
        outerjoin(email,
                  (user_profile.c.user_profile_id == email.c.user_profile_id) &
                  (email.c.contact_method_type == ContactMethodType.Email)).\
        outerjoin(phone,
                  (user_profile.c.user_profile_id == phone.c.user_profile_id) &
                  (phone.c.contact_method_type == ContactMethodType.Phone)).\
        outerjoin(email_contact_method,
                  (email.c.user_profile_id == email_contact_method.c.user_profile_id) &
                  (email.c.contact_method_id == email_contact_method.c.contact_method_id)).\
        outerjoin(phone_contact_method,
                  (phone.c.user_profile_id == phone_contact_method.c.user_profile_id) &
                  (phone.c.contact_method_id == phone_contact_method.c.contact_method_id))

    if user_profile_id is not None:
        q = q.where(user_profile.c.user_profile_id == user_profile_id)
    if email_address is not None:
        q = q.where(email_contact_method.c.email_address == email_address)
    if phone_number is not None:
        q = q.where(phone_contact_method.c.phone_number == phone_number)

    return await session.execute(q)


@operation
async def create_user_profile(session: AsyncSession, display_name: str, name: str, password: str,
                              role: UserRole, email_address: str=None, phone_number: str=None
                              ) -> UUID:
    if email_address is None and phone_number is None:
        raise ValueError("one of email address or phone number is required")

    r = await session.execute(
        user_profile.
        insert().
        values(name=name,
               display_name=display_name,
               role=role).
        returning(user_profile.c.user_profile_id))
    profile_id = r.scalar()

    await session.execute(
        user_auth.
        insert().
        values(user_profile_id=profile_id,
               password_crypt=f.crypt(password, f.gen_salt('bf', 8))))

    if email_address is not None:
        await add_contact_method(profile_id, email_address=email_address).execute(session)
    if phone_number is not None:
        await add_contact_method(profile_id, phone_number=phone_number).execute(session)

    return profile_id


@operation
async def add_contact_method(session: AsyncSession, user_profile_id: UUID,
                             email_address: str=None, phone_number: str=None
                             ) -> UUID:
    if email_address is not None:
        email_exists = exists().where(email_contact_method.c.email_address == email_address)
        q = select(literal(True)).\
            select_from(user_profile.join(contact_method).join(email_contact_method)).\
            where(email_exists)
        result = await session.execute(q)
        ex = result.scalar()
        if ex:
            raise ValueError(f"user profile with email {email_address} already exists")

        r = await session.execute(
            contact_method.
            insert().
            values(user_profile_id=user_profile_id,
                   contact_method_type=ContactMethodType.Email,
                   verified=False).
            returning(contact_method.c.contact_method_id))
        email_id = r.scalar()
        await session.execute(
            email_contact_method.
            insert().
            values(user_profile_id=user_profile_id,
                   contact_method_id=email_id,
                   email_address=email_address))
        return email_id

    elif phone_number is not None:
        pn_exists = exists().where(phone_contact_method.c.phone_number == phone_number)
        q = select(literal(True)).\
            select_from(user_profile.join(contact_method).join(phone_contact_method)).\
            where(pn_exists)
        result = await session.execute(q)
        ex = result.scalar()
        if ex:
            raise ValueError(f"user profile with phone number {phone_number} already exists")

        r = await session.execute(
                contact_method.
                insert().
                values(user_profile_id=user_profile_id,
                       contact_method_type=ContactMethodType.Phone,
                       verified=False).
                returning(contact_method.c.contact_method_id))
        pn_id = r.scalar()
        await session.execute(
            phone_contact_method.
            insert().
            values(user_profile_id=user_profile_id,
                   contact_method_id=pn_id,
                   phone_number=phone_number))
        return pn_id

    raise ValueError("one of email_address or phone_number is required")


@operation(record_cls=ContactMethodRecord, single_result=True)
async def get_contact_method(session: AsyncSession, contact_method_id: UUID,
                             user_profile_id: UUID=None
                             ) -> Result:
    email = contact_method.alias()
    phone = contact_method.alias()

    q = select(contact_method.c.user_profile_id,
               contact_method.c.contact_method_id,
               contact_method.c.verified,
               contact_method.c.contact_method_type,
               email_contact_method.c.email_address,
               phone_contact_method.c.phone_number).\
        select_from(contact_method).\
        outerjoin(email_contact_method,
                  (contact_method.c.user_profile_id == email_contact_method.c.user_profile_id) &
                  (contact_method.c.contact_method_type == ContactMethodType.Email)).\
        outerjoin(phone_contact_method,
                  (contact_method.c.user_profile_id == phone_contact_method.c.user_profile_id) &
                  (contact_method.c.contact_method_type == ContactMethodType.Phone)).\
        where(contact_method.c.contact_method_id == contact_method_id)

    if user_profile_id is None:
        q = q.where(contact_method.c.user_profile_id == user_profile_id)

    rs = await session.execute(q)
    return rs


@operation
async def mark_contact_method_verified(session: AsyncSession, contact_method_id: UUID,
                                       user_profile_id: UUID=None):
    u = contact_method.\
        update().\
        values(verified=True).\
        where(contact_method.c.contact_method_id == contact_method_id).\
        where(contact_method.c.verified == false())

    if user_profile_id is not None:
        u = u.where(contact_method.c.user_profile_id == user_profile_id)

    rs = await session.execute(u)
    c = rs.rowcount
    if c == 0:
        raise ValueError(f"no unverified contact method exists with "
                          "contact_method_id {contact_method_id!s}")
    assert c == 1


@operation
async def add_payment_profile(session: AsyncSession, user_profile_id: UUID, processor_id: str,
                              processor_customer_profile_id: str
                              ) -> UUID:
    q = payment_profile.\
        insert().\
        values(user_profile_id=user_profile_id,
               processor_id=processor_id,
               processor_customer_profile_id=processor_customer_profile_id).\
        returning(payment_profile.c.payment_profile_id)
    rs = await session.execute(q)
    return rs.scalar()


@operation
async def add_payment_method(session: AsyncSession, user_profile_id: UUID,
                             payment_profile_id: UUID, processor_payment_method_id: str,
                             payment_method_type: PaymentMethodType, payment_method_family: str,
                             display_name: str, safe_account_number_fragment: str,
                             expires_after: datetime
                             ) -> UUID:
    q = payment_method.\
        insert().\
        values(user_profile_id=user_profile_id,
               payment_profile_id=payment_profile_id,
               processor_payment_method_id=processor_payment_method_id,
               payment_method_type=payment_method_type,
               payment_method_family=payment_method_family,
               display_name=display_name,
               safe_account_number_fragment=safe_account_number_fragment,
               status=PaymentMethodStatus.Current,
               expires_after=expires_after).\
        returning(payment_method.c.payment_method_id)
    rs = await session.execute(q)
    return rs.scalar()


@operation(single_result=True, record_cls=PaymentProfileRecord, default=None)
async def get_payment_profile(session: AsyncSession, user_profile_id: UUID,
                              processor_id: str
                              ) -> PaymentProfileRecord:
    q = select(payment_profile.c.user_profile_id,
               payment_profile.c.payment_profile_id,
               payment_profile.c.processor_id,
               payment_profile.c.processor_customer_profile_id).\
        where(payment_profile.c.user_profile_id == user_profile_id).\
        where(payment_profile.c.processor_id == processor_id)
    return await session.execute(q)


@operation(record_cls=PaymentMethodRecord)
async def get_payment_methods(session: AsyncSession, user_profile_id: UUID,
                              payment_profile_id: Optional[UUID]=None,
                              payment_method_id: Optional[UUID]=None,
                              processor_id: Optional[str]=None,
                              status: Optional[PaymentMethodStatus]=PaymentMethodStatus.Current,
                              ) -> Recordset:
    if not any([payment_profile_id, payment_method_id, processor_id]):
        raise ValueError("one of payment_profile_id, payment_method_id, processor_id "
                         "are required")

    q = select(payment_profile.c.user_profile_id,
               payment_profile.c.payment_profile_id,
               payment_profile.c.processor_id,
               payment_profile.c.processor_customer_profile_id,
               payment_method.c.payment_method_id,
               payment_method.c.processor_payment_method_id,
               payment_method.c.payment_method_type,
               payment_method.c.payment_method_family,
               payment_method.c.display_name,
               payment_method.c.safe_account_number_fragment,
               payment_method.c.status,
               payment_method.c.expires_after).\
        select_from(payment_profile).\
        join(payment_method).\
        where(payment_profile.c.user_profile_id == user_profile_id)

    if payment_method_id is not None:
        q = q.where(payment_method.c.payment_method_id == payment_method_id)
    if payment_profile_id is not None:
        q = q.where(payment_profile.c.payment_profile_id == payment_profile_id)
    if processor_id is not None:
        q = q.where(payment_profile.c.processor_id == processor_id)
    if status is not None:
        q = q.where(payment_method.c.status == status)

    return await session.execute(q)
