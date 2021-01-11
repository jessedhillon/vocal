from decimal import Decimal
from uuid import uuid4

import pytest

import vocal.api.operations as op
from vocal.constants import UserRole

from .. import DatabaseTestCase


class ContentOperationsTestCase(DatabaseTestCase):
    async def test_create_article(self):
        async with op.session(self.appctx) as ss:
            profile_id = await op.user_profile.\
                create_user_profile(display_name='Jesse',
                                    name='Jesse Dhillon',
                                    password='123foobar^#@',
                                    role=UserRole.Subscriber,
                                    email_address='jesse@dhillon.com',
                                    phone_number='+14155551234').\
                execute(ss)

            article_id, version_key = await op.content.\
                create_article(author_id=profile_id,
                               title="Foo Article",
                               excerpt={},
                               document={},
                               text="").\
                execute(ss)
            assert article_id is not None
            assert version_key is not None

    async def test_get_article(self):
        async with op.session(self.appctx) as ss:
            profile_id = await op.user_profile.\
                create_user_profile(display_name='Jesse',
                                    name='Jesse Dhillon',
                                    password='123foobar^#@',
                                    role=UserRole.Subscriber,
                                    email_address='jesse@dhillon.com',
                                    phone_number='+14155551234').\
                execute(ss)

            article_id, version_key = await op.content.\
                create_article(author_id=profile_id,
                               title="Foo Article",
                               excerpt={},
                               document={},
                               text="").\
                execute(ss)

            article = await op.content.\
                get_article(article_id=article_id).\
                execute(ss)

    async def test_update_article(self):
        async with op.session(self.appctx) as ss:
            profile_id = await op.user_profile.\
                create_user_profile(display_name='Jesse',
                                    name='Jesse Dhillon',
                                    password='123foobar^#@',
                                    role=UserRole.Subscriber,
                                    email_address='jesse@dhillon.com',
                                    phone_number='+14155551234').\
                execute(ss)

            article_id, vk1 = await op.content.\
                create_article(author_id=profile_id,
                               title="Foo Article",
                               excerpt={},
                               document={},
                               text="").\
                execute(ss)

            article = await op.content.\
                get_article(article_id=article_id).\
                execute(ss)

            vk2 = await op.content.\
                update_article(article_id=article_id,
                               version_key=vk1,
                               author_id=profile_id,
                               title="New Foo Article",
                               excerpt={},
                               document={},
                               text="new text",
                               status=article.status).\
                execute(ss)

        async with op.session(self.appctx) as ss:
            with pytest.raises(RuntimeError) as excinfo:
                await op.content.\
                    update_article(article_id=article_id,
                                   version_key=vk1,
                                   author_id=profile_id,
                                   title="New Foo Article",
                                   excerpt={},
                                   document={},
                                   text="new text",
                                   status=article.status).\
                    execute(ss)
            assert str(excinfo.value) == (f"attempted to insert over stale version {vk1}")

            await op.content.\
                update_article(article_id=article_id,
                               version_key=vk2,
                               author_id=profile_id,
                               title="New Foo Article",
                               excerpt={},
                               document={},
                               text="new text",
                               status=article.status).\
                execute(ss)
