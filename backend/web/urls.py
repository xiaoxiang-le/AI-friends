from django.urls import path, re_path

from .views.friend.message.asr.asr import ASRView
from web.views.friend.message.chat.chat import MessageChatView

from .views.create.character.create import CreateCharacterView
from .views.create.character.get_list import GetListCharacterView
from .views.create.character.get_single import GetSingleCharacterView
from .views.create.character.remove import RemoveCharacterView
from .views.create.character.update import UpdateCharacterView
from .views.create.character.voice.get_list import GetVoiceList
from .views.friend.get_list import GetListFriendView
from .views.friend.get_or_create import GetOrCreateFriendView
from .views.friend.message.get_history import GetHistoryView
from .views.friend.remove import RemoveFriendView
from .views.homepage.index import HomepageIndexView
from .views.index import index
from .views.user.account.get_user_info import GetUserInfo
from .views.user.account.logout import LogoutView
from .views.user.account.login import Login
from .views.user.account.register import Register
from .views.user.account.refresh_token import RefreshTokenView
from .views.user.profile.update import UpdateProfile

urlpatterns = [
    path("api/user/account/login/", Login.as_view()),
    path("api/user/account/logout/", LogoutView.as_view()),
    path("api/user/account/register/", Register.as_view()),
    path("api/user/account/refresh_token/", RefreshTokenView.as_view()),
    path("api/user/account/get_user_info/", GetUserInfo.as_view()),

    path('api/create/character/create/', CreateCharacterView.as_view()),
    path('api/create/character/update/', UpdateCharacterView.as_view()),
    path('api/create/character/remove/', RemoveCharacterView.as_view()),
    path('api/create/character/get_single/', GetSingleCharacterView.as_view()),
    path('api/user/profile/update/', UpdateProfile.as_view()),
    path('api/create/character/get_list/', GetListCharacterView.as_view()),
    path('api/create/character/voice/get_list/', GetVoiceList.as_view()),
    path('api/homepage/index/', HomepageIndexView.as_view()),
    path('api/friend/get_or_create/', GetOrCreateFriendView.as_view()),
    path('api/friend/remove/', RemoveFriendView.as_view()),
    path('api/friend/get_list/', GetListFriendView.as_view()),
    path('api/friend/message/chat/', MessageChatView.as_view()),
    path('api/friend/message/get_history/', GetHistoryView.as_view()),
    path('api/friend/message/asr/asr/', ASRView.as_view()),

    path("", index, name="index"),
    # 前端 history 模式：除 media/static/assets 外的任意路径都交给前端路由
    re_path(r"^(?!media/|static/|assets/).*$", index),
]
