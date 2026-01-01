import json
import os
from . import lang_detector

_LANG = 'zh-cn'
_TRANSLATIONS = {}

def _load_lang_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def available_languages(langs_dir=None):
    if langs_dir is None:
        base = os.path.join(os.path.dirname(__file__), '..', 'langs')
    else:
        base = langs_dir
    base = os.path.normpath(base)
    if not os.path.isdir(base):
        return []
    items = []
    for fn in os.listdir(base):
        if fn.endswith('.json'):
            items.append(fn[:-5])
    return sorted(items)

def set_language(lang_code):
    global _LANG, _TRANSLATIONS
    _LANG = lang_code
    langs_dir = os.path.join(os.path.dirname(__file__), '..', 'langs')
    langs_dir = os.path.normpath(langs_dir)
    path = os.path.join(langs_dir, f"{lang_code}.json")
    _TRANSLATIONS = _load_lang_file(path)


def set_language_from_system(fallback='en-us'):
    """Detect system language and set the closest available translation.

    The function will try exact match first, then primary-subtag match (e.g. 'en-us' -> 'en'),
    then the provided fallback (prefer 'en-us'), and finally the first available language.
    Returns the language code that was set.
    """
    sys_lang = lang_detector.detect_system_language()
    avail = available_languages()
    if not avail:
        # nothing available
        return None

    candidates = []
    if sys_lang:
        candidates.append(sys_lang)
        # add primary subtag
        if '-' in sys_lang:
            primary = sys_lang.split('-')[0]
            candidates.append(primary)

    # ensure fallback preference
    if fallback:
        candidates.append(fallback)
        if '-' in fallback:
            candidates.append(fallback.split('-')[0])

    # finally try default 'en' then first available
    candidates.append('en')
    candidates.extend(avail)

    # choose first matching available language
    chosen = None
    for c in candidates:
        if not c:
            continue
        normalized = c.lower()
        # some files may use 'en' while candidates use 'en-us'
        if normalized in avail:
            chosen = normalized
            break
        # try replacing '_' with '-'
        normalized2 = normalized.replace('_', '-')
        if normalized2 in avail:
            chosen = normalized2
            break

    if not chosen:
        chosen = avail[0]

    set_language(chosen)
    return chosen

def t(key, **kwargs):
    val = _TRANSLATIONS.get(key)
    if val is None:
        return key.format(**kwargs) if kwargs else key
    try:
        return val.format(**kwargs) if kwargs else val
    except Exception:
        return val

set_language(_LANG)

__all__ = ["set_language", "t", "available_languages", "set_language_from_system"]
