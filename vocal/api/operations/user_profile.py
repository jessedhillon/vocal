from enum import Enum

from sqlalchemy import func as f
from sqlalchemy.sql.expression import exists, literal, select

from vocal.api.models.user_profile import UserRole, ContactMethodType
from vocal.api.util import operation
from vocal.api.storage.sql import user_profile, user_auth, contact_method, email_contact_method,\
        phone_contact_method, contact_method_type, user_role


@operation
async def get_user_profile(session, user_profile_id):
    r = await session.execute(\
        user_profile.select().where(user_profile.c.user_profile_id == user_profile_id))
    return r.one()


@operation
async def create_user_profile(session, display_name, name, password, role, email_address=None,
                              phone_number=None):
    if email_address is None and phone_number is None:
        raise ValueError('one of email_address or phone_number is required')

    r = await session.execute(
        user_profile.\
            insert().\
            values(
                name=name,
                display_name=display_name,
                role=role.value).\
            returning(user_profile.c.user_profile_id))
    profile_id = r.scalar()

    await session.execute(
        user_auth.\
            insert().\
            values(
                user_profile_id=profile_id,
                password_crypt=f.crypt(password, f.gen_salt('bf', 8))))

    if email_address is not None:
        await add_contact_method(profile_id, email_address=email_address).execute(session)
    if phone_number is not None:
        await add_contact_method(profile_id, phone_number=phone_number).execute(session)

    return profile_id


@operation
async def add_contact_method(session, user_profile_id, email_address=None, phone_number=None):
    if email_address is not None:
        email_exists = exists().where(email_contact_method.c.email_address == email_address)
        q = select(literal(True)).\
            select_from(user_profile.join(contact_method).join(email_contact_method)).\
            where(email_exists)
        result = await session.execute(q)
        ex = result.scalar()
        if ex:
            raise ValueError(f"user_profile with email {email} already exists")

        r = await session.execute(
                contact_method.\
                    insert().\
                    values(
                        user_profile_id=user_profile_id,
                        contact_method_type=ContactMethodType.Email.value,
                        verified=False).\
                    returning(contact_method.c.contact_method_id))
        email_id = r.scalar()
        await session.execute(
            email_contact_method.\
                insert().\
                values(
                    user_profile_id=user_profile_id,
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
            raise ValueError(f"user_profile with phone number {phone_number} already exists")

        r = await session.execute(
                contact_method.\
                    insert().\
                    values(
                        user_profile_id=user_profile_id,
                        contact_method_type=ContactMethodType.Phone.value,
                        verified=False).\
                    returning(contact_method.c.contact_method_id))
        pn_id = r.scalar()
        await session.execute(
            phone_contact_method.\
                insert().\
                values(
                    user_profile_id=user_profile_id,
                    contact_method_id=pn_id,
                    phone_number=phone_number))
        return pn_id

    raise ValueError("one of email_address or phone_number is required")
