from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from web.models.character import Character
from web.services.characters import character_data


class HomepageIndexView(APIView):
    authentication_classes = []

    def get(self, request):
        try:
            offset = max(0, int(request.query_params.get('items_count', 0)))
            cursor = int(request.query_params.get('cursor', 0))
        except (ValueError, TypeError):
            return Response({'result': '分页参数不合法'}, status=400)
        query = request.query_params.get('search_query', '').strip()[:200]
        queryset = Character.objects.filter(status='published', visibility='public').select_related('author__user')
        if query:
            queryset = queryset.filter(Q(name__icontains=query) | Q(public_description__icontains=query))
        if cursor:
            queryset = queryset.filter(id__lt=cursor)
            offset = 0
        rows = list(queryset.order_by('-id')[offset:offset+21])
        return Response({'result': 'success', 'characters': [character_data(c) for c in rows[:20]],
            'has_more': len(rows)>20, 'next_cursor': rows[19].id if len(rows)>20 else None})
