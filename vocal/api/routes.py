from aiohttp.web import RouteTableDef, RouteDef

from .views import users


routes = [
    # users
    RouteDef('GET', '/users', users.list_user_profiles, kwargs={})
]
