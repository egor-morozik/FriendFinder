import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'FriendFinder.settings')

django_asgi_app = get_asgi_application()

def get_websocket_application():
    from channels.routing import ProtocolTypeRouter, URLRouter
    from channels.auth import AuthMiddlewareStack
    import Main.routing  
    return ProtocolTypeRouter({
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(
            URLRouter(
                Main.routing.websocket_urlpatterns
            )
        ),
    })

application = get_websocket_application()