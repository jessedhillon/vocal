from aiohttp.web import HTTPAccepted, HTTPBadRequest, HTTPUnauthorized, Response, json_response

import vocal.api.operations as op
import vocal.api.security as security
import vocal.api.util as util
from vocal.api.models.membership import SubscriptionPlan
from vocal.api.security import Capabilities as caps
from vocal.util.web import with_context, with_session, json_response


@json_response
@util.message
@with_session(new=True)
@with_context
async def get_subscription_plans(request, session, ctx):
    async with op.session(ctx) as ss:
        plans = await op.membership.\
            get_subscription_plans().\
            execute(ss)

    return SubscriptionPlan.unmarshal_recordset(plans)
