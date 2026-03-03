from functools import wraps
from django.shortcuts import redirect


def journal_access_required(view_func):
    """Guard journal views: session must contain the matching journal UUID."""
    @wraps(view_func)
    def wrapper(request, pk, *args, **kwargs):
        if request.session.get('journal_id') != str(pk):
            return redirect('open_journal')
        return view_func(request, pk, *args, **kwargs)
    return wrapper
