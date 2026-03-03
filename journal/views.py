import base64

from django.core.cache import cache
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password

from .models import Journal, Entry
from .forms import NewJournalForm, OpenJournalForm, EntryForm, FrontMatterForm
from .decorators import journal_access_required


_MAP_PREFIX  = 'data:image/png;base64,'
_MAP_MAX_LEN = 3 * 1024 * 1024  # 3 MB as a base64 string

def _valid_map_image(data):
    """Return True only for a size-bounded, well-formed base64 PNG data URI."""
    if not data.startswith(_MAP_PREFIX):
        return False
    if len(data) > _MAP_MAX_LEN:
        return False
    try:
        decoded = base64.b64decode(data[len(_MAP_PREFIX):], validate=True)
        return decoded[:8] == b'\x89PNG\r\n\x1a\n'
    except Exception:
        return False


def landing(request):
    return render(request, 'journal/landing.html')


def new_journal(request):
    form = NewJournalForm()

    if request.method == 'POST':
        ip        = request.META.get('REMOTE_ADDR', 'unknown')
        cache_key = f'codeword_attempts_{ip}'
        attempts  = cache.get(cache_key, 0)

        if attempts >= _RATE_LIMIT_ATTEMPTS:
            form.add_error(None, 'Too many attempts. Please wait before trying again.')
            return render(request, 'journal/new.html', {'form': form})

        form = NewJournalForm(request.POST)
        if form.is_valid():
            codeword = form.cleaned_data['codeword']
            cache.set(cache_key, attempts + 1, _RATE_LIMIT_WINDOW)
            # Reject codewords already used by an existing journal
            for journal in Journal.objects.all():
                if check_password(codeword, journal.codeword_hash):
                    form.add_error('codeword', 'This codeword is already in use.')
                    return render(request, 'journal/new.html', {'form': form})
            cache.delete(cache_key)
            journal = Journal.objects.create(
                codeword_hash=make_password(codeword),
            )
            request.session['journal_id'] = str(journal.id)
            return redirect('journal_view', pk=journal.id)

    return render(request, 'journal/new.html', {'form': form})


_RATE_LIMIT_ATTEMPTS = 10
_RATE_LIMIT_WINDOW   = 600  # seconds (10 minutes)

def open_journal(request):
    error = None
    form  = OpenJournalForm()

    if request.method == 'POST':
        ip        = request.META.get('REMOTE_ADDR', 'unknown')
        cache_key = f'codeword_attempts_{ip}'
        attempts  = cache.get(cache_key, 0)

        if attempts >= _RATE_LIMIT_ATTEMPTS:
            error = "Too many attempts. Please wait before trying again."
        else:
            form = OpenJournalForm(request.POST)
            if form.is_valid():
                codeword = form.cleaned_data['codeword']
                cache.set(cache_key, attempts + 1, _RATE_LIMIT_WINDOW)
                # Check all journals without early exit to avoid timing leaks
                matched = None
                for journal in Journal.objects.all():
                    if check_password(codeword, journal.codeword_hash):
                        matched = journal
                if matched:
                    cache.delete(cache_key)
                    request.session['journal_id'] = str(matched.id)
                    return redirect('journal_view', pk=matched.id)
                error = "No journal found with that codeword."

    return render(request, 'journal/open.html', {'form': form, 'error': error})


_FRONT = 4   # number of fixed front-matter pages

def _build_page(idx, entries, journal):
    """Return a dict describing the page at logical index idx.

    Index layout:
      0            → decorative (placeholder)
      1            → front matter ("This journal belongs to")
      2            → map left  (heading + textarea)
      3            → map right (visual continuation)
      4 .. N+3     → entries oldest-first (entries[idx-4])
      N+4          → compose
    """
    total = len(entries)
    num = idx + 1
    if idx == 0:
        return {'type': 'decorative', 'page_num': num}
    elif idx == 1:
        return {'type': 'front_matter', 'form': FrontMatterForm(instance=journal), 'page_num': num}
    elif idx == 2:
        return {'type': 'map_left', 'page_num': num}
    elif idx == 3:
        return {'type': 'map_right', 'page_num': num}
    elif _FRONT <= idx < _FRONT + total:
        return {'type': 'entry', 'entry': entries[idx - _FRONT], 'page_num': num}
    elif idx == _FRONT + total:
        return {'type': 'compose', 'form': EntryForm(), 'page_num': num}
    else:
        return {'type': 'blank', 'page_num': num}


@journal_access_required
def journal_view(request, pk):
    journal = get_object_or_404(Journal, pk=pk)
    # Oldest first so page indices are stable
    entries = list(journal.entries.order_by('created_at'))
    total = len(entries)

    # Pages: 2 front matter + N entries + 1 compose
    total_pages = _FRONT + total + 1
    total_spreads = (total_pages + 1) // 2

    # Always open to the first spread (decorative + front matter)
    default_spread = 0

    spread_param = request.GET.get('spread')
    if spread_param is None:
        spread_num = default_spread
    else:
        try:
            spread_num = int(spread_param)
            if spread_num < 0 or spread_num >= total_spreads:
                raise ValueError
        except (ValueError, TypeError):
            return redirect('journal_view', pk=pk)

    left_idx  = spread_num * 2
    right_idx = spread_num * 2 + 1

    left_page  = _build_page(left_idx,  entries, journal)
    right_page = _build_page(right_idx, entries, journal)

    # Navigation: None = disabled
    nav_first = 0 if spread_num > 0 else None
    nav_prev  = spread_num - 1 if spread_num > 0 else None
    nav_next  = spread_num + 1 if spread_num < total_spreads - 1 else None
    nav_last  = total_spreads - 1 if spread_num < total_spreads - 1 else None

    return render(request, 'journal/journal.html', {
        'journal':       journal,
        'left_page':     left_page,
        'right_page':    right_page,
        'spread_num':    spread_num,
        'total_spreads': total_spreads,
        'nav_first':     nav_first,
        'nav_prev':      nav_prev,
        'nav_next':      nav_next,
        'nav_last':      nav_last,
        'delete_error':  request.GET.get('delete_error') == '1',
    })


@journal_access_required
def add_entry(request, pk):
    journal = get_object_or_404(Journal, pk=pk)
    if request.method == 'POST':
        form = EntryForm(request.POST)
        if form.is_valid():
            Entry.objects.create(
                journal=journal,
                content=form.cleaned_data['content'],
            )
            # Redirect to the spread containing the new entry
            entries = list(journal.entries.order_by('created_at'))
            spread = (_FRONT + len(entries) - 1) // 2
            return redirect(reverse('journal_view', kwargs={'pk': pk}) + f'?spread={spread}')
    return redirect('journal_view', pk=pk)


@journal_access_required
def save_meta(request, pk):
    journal = get_object_or_404(Journal, pk=pk)
    if request.method == 'POST':
        form = FrontMatterForm(request.POST, instance=journal)
        if form.is_valid():
            form.save()
    return redirect(reverse('journal_view', kwargs={'pk': pk}) + '?spread=0')


@journal_access_required
def save_map(request, pk):
    journal = get_object_or_404(Journal, pk=pk)
    if request.method == 'POST':
        left  = request.POST.get('map_image_left',  '')
        right = request.POST.get('map_image_right', '')
        if left  and _valid_map_image(left):  journal.map_image_left = left
        if right and _valid_map_image(right): journal.map_image      = right
        journal.save()
    return redirect(reverse('journal_view', kwargs={'pk': pk}) + '?spread=1')


@journal_access_required
def delete_journal(request, pk):
    journal = get_object_or_404(Journal, pk=pk)
    if request.method == 'POST':
        codeword = request.POST.get('codeword', '').strip()
        if check_password(codeword, journal.codeword_hash):
            journal.delete()
            request.session.pop('journal_id', None)
            return redirect('landing')
    return redirect(reverse('journal_view', kwargs={'pk': pk}) + '?spread=0&delete_error=1')


@journal_access_required
def edit_entry(request, pk, entry_pk):
    journal = get_object_or_404(Journal, pk=pk)
    entry = get_object_or_404(Entry, pk=entry_pk, journal=journal)
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if content:
            entry.content = content
            entry.edited_at = timezone.now()
            entry.save()
            entries = list(journal.entries.order_by('created_at'))
            idx = next((i for i, e in enumerate(entries) if e.pk == entry.pk), 0)
            spread = (_FRONT + idx) // 2
        else:
            # Empty content — delete the entry and return to its former spread
            entries = list(journal.entries.order_by('created_at'))
            idx = next((i for i, e in enumerate(entries) if e.pk == entry.pk), 0)
            spread = (_FRONT + idx) // 2
            entry.delete()
    return redirect(reverse('journal_view', kwargs={'pk': pk}) + f'?spread={spread}')
