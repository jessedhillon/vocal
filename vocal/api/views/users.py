from aiohttp.web import Response, json_response


async def list_user_profiles(request):
    return json_response({
        'status': 'ok',
    }, status=200)
