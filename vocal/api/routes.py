from aiohttp.web import RouteTableDef, RouteDef

from .views import users, authn, plans


async def configure(appctx):
    appctx.declare('routes')
    appctx.routes.set([
        # authn
        RouteDef('POST', '/authn/session', authn.init_authn_session, {}),
        RouteDef('GET', '/authn/challenge', authn.get_authn_challenge, {}),
        RouteDef('POST', '/authn/challenge', authn.verify_authn_challenge, {}),

        # user
        RouteDef('GET', '/users/{user_profile_id}/contactMethods/{contact_method_id}/verify',
                 users.get_contact_method_verify_challenge, {}),
        RouteDef('POST', '/users/{user_profile_id}/contactMethods/{contact_method_id}/verify',
                 users.verify_contact_method, {}),

        # plan
        RouteDef('GET', '/plans', plans.get_subscription_plans, {}),
        RouteDef('POST', '/plans', plans.create_subscription_plan, {}),
    ])
