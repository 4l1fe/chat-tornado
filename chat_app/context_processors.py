from tornadochat import settings

def tornado_host_port(request):
    return {'tornado_host': settings.TORNADO_HOST,
            'tornado_port': settings.TORNADO_PORT,
            'tornado_full_address': settings.TORNADO_HOST+':'+settings.TORNADO_PORT}
