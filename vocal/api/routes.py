from aiohttp.web import RouteTableDef, RouteDef

from .views import users, authn


async def configure(appctx):
    appctx.declare('routes')
    appctx.routes.set([
        # users
        RouteDef('GET', '/users', users.list_user_profiles, kwargs={}),

        # authn
        RouteDef('POST', '/authn/session', authn.init_authn_session, kwargs={}),
        RouteDef('GET', '/authn/challenge', authn.get_authn_challenge, kwargs={}),
    ])
