from aiohttp.web import RouteTableDef, RouteDef

from .views import users, authn


async def configure(appctx):
    appctx.declare('routes')
    appctx.routes.set([
        # authn
        RouteDef('POST', '/authn/session', authn.init_authn_session, kwargs={}),
        RouteDef('GET', '/authn/challenge', authn.get_authn_challenge, kwargs={}),
        RouteDef('POST', '/authn/challenge', authn.verify_authn_challenge, kwargs={}),

        # user
        RouteDef('GET', '/users/{user_profile_id}/contactMethods/{contact_method_id}/verify',
                 users.get_contact_method_verify_challenge, kwargs={}),
        RouteDef('POST', '/users/{user_profile_id}/contactMethods/{contact_method_id}/verify',
                 users.verify_contact_method, kwargs={}),
    ])
