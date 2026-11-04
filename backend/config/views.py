from django.http import JsonResponse


def health(request):
    """Liveness endpoint: startup migrations finish before Daphne starts."""
    return JsonResponse({"status": "ok"})
