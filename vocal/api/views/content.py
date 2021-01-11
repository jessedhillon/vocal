import vocal.api.operations as op
import vocal.api.security as security
from vocal.config import AppConfig
from vocal.api.security import AuthnSession, Capability
from vocal.api.models.content import Article


async def get_article(request, ctx: AppConfig, session: AuthnSession):
    article_id = request.match_info['article_id']

    async with op.session(ctx) as ss:
        article = await op.content.\
            get_article(article_id=article_id).\
            unmarshal_with(Article).\
            execute(ss)

    return article.get_view('public')
