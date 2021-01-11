import json
from decimal import Decimal

import vocal.api.operations as op
from vocal.api.models.content import Article
from vocal.api.models.user_profile import PaymentProfile
from vocal.constants import ArticleStatus, UserRole

from .. import AppTestCase


class ArticleViewTestCase(AppTestCase):
    async def test_get_article(self):
        profile_id = await self.authenticate_as(UserRole.Superuser)
        async with op.session(self.appctx) as ss:
            article_id, version_key = await op.content.\
                create_article(author_id=profile_id,
                               title="Foo Article",
                               excerpt={},
                               document={},
                               text="").\
                execute(ss)

        resp = await self.client.request('GET', f'/articles/{article_id}')
        j = await resp.json()
        assert j['status']['success']
        assert j['data']['article_id'] == str(article_id)
        assert j['data']['version_key'] == str(version_key)
