from enum import Enum
from uuid import UUID
from typing import Union

import sqlalchemy.exc
from sqlalchemy import func as f
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.sql.expression import alias, exists, false, join, literal, select, true

from vocal.api.models.user_profile import UserRole, ContactMethodType
from vocal.api.util import operation
from vocal.api.storage.record import UserProfileRecord, EmailContactMethodRecord,\
        PhoneContactMethodRecord
from vocal.api.storage.sql import user_profile, user_auth, contact_method, email_contact_method,\
        phone_contact_method


@operation
async def get_user_profile(session: AsyncSession, user_profile_id: UUID=None,
                           email_address: str=None, phone_number: str=None
                           ) -> UserProfileRecord:
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
                  (email.c.contact_method_type == ContactMethodType.Email.value)).\
        outerjoin(phone,
                  (user_profile.c.user_profile_id == phone.c.user_profile_id) &
                  (phone.c.contact_method_type == ContactMethodType.Phone.value)).\
        outerjoin(email_contact_method,
                  (email.c.user_profile_id == email_contact_method.c.user_profile_id) &
                  (email.c.contact_method_id == email_contact_method.c.contact_method_id)).\
        outerjoin(phone_contact_method,
                  (phone.c.user_profile_id == phone_contact_method.c.user_profile_id) &
                  (phone.c.contact_method_id == phone_contact_method.c.contact_method_id))

    if user_profile_id is not None:
        q = q.where(user_profile.c.user_profile_id == str(user_profile_id))
    if email_address is not None:
        q = q.where(email_contact_method.c.email_address == email_address)
    if phone_number is not None:
        q = q.where(phone_contact_method.c.phone_number == phone_number)

    rs = await session.execute(q)

    try:
        row = rs.one()
        return UserProfileRecord.unmarshal_row(row)
    except sqlalchemy.exc.NoResultFound:
        return None


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
               role=role.value).
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

    return UUID(profile_id)


@operation
async def add_contact_method(session: AsyncSession, user_profile_id: UUID,
                             email_address: str=None, phone_number: str=None
                             ) -> UUID:
    user_profile_id = str(user_profile_id)

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
                   contact_method_type=ContactMethodType.Email.value,
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
                       contact_method_type=ContactMethodType.Phone.value,
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


@operation
async def get_contact_method(session: AsyncSession, contact_method_id: UUID,
                             user_profile_id: UUID=None
                            ) -> Union[PhoneContactMethodRecord, EmailContactMethodRecord]:
    contact_method_id = str(contact_method_id)
    user_profile_id = str(user_profile_id)

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
                  (contact_method.c.contact_method_type == ContactMethodType.Email.value)).\
        outerjoin(phone_contact_method,
                  (contact_method.c.user_profile_id == phone_contact_method.c.user_profile_id) &
                  (contact_method.c.contact_method_type == ContactMethodType.Phone.value)).\
        where(contact_method.c.contact_method_id == contact_method_id)

    if user_profile_id is None:
        q = q.where(contact_method.c.user_profile_id == user_profile_id)

    rs = await session.execute(q)
    try:
        cm = rs.one()
        cmtype = ContactMethodType(cm[3])
        if cmtype is ContactMethodType.Phone:
            return PhoneContactMethodRecord.unmarshal_row(cm)
        elif cmtype is ContactMethodType.Email:
            return EmailContactMethodRecord.unmarshal_row(cm)
        raise ValueError(cmtype)
    except sqlalchemy.exc.NoResultFound:
        return None


@operation
async def mark_contact_method_verified(session: AsyncSession, contact_method_id: UUID,
                                       user_profile_id: UUID=None) -> int:
    u = contact_method.\
        update().\
        values(verified=True).\
        where(contact_method.c.contact_method_id == str(contact_method_id)).\
        where(contact_method.c.verified == false())

    if user_profile_id is not None:
        u = u.where(contact_method.c.user_profile_id == user_profile_id)

    rs = await session.execute(u)
    c = rs.rowcount
    if c == 0:
        raise ValueError(f"no unverified contact method exists with "
                          "contact_method_id {contact_method_id!s}")
    return c
