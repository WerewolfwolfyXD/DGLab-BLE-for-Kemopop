import locale
import os
import sys


def detect_system_language():
    """返回用 - 作连接符的小写语言

    比如
      'en_US' -> 'en-us'
      'zh_CN' -> 'zh-cn'

    如果无法检测，则返回None
    """
    # Try locale.getdefaultlocale()
    try:
        loc = locale.getdefaultlocale()
        if loc and loc[0]:
            tag = loc[0].replace('_', '-').lower()
            return tag
    except Exception:
        pass

    # Try environment variables (LANG, LC_ALL)
    for env in ("LANG", "LC_ALL", "LC_MESSAGES"):
        val = os.environ.get(env)
        if val:
            # LANG can be like en_US.UTF-8
            tag = val.split('.')[0].replace('_', '-').lower()
            return tag

    # Fallback:
    # Windows fallback using sys.getwindowsversion is not helpful for locale code,
    # but locale.getlocale may help
    try:
        loc2 = locale.getlocale()
        if loc2 and loc2[0]:
            tag = loc2[0].replace('_', '-').lower()
            return tag
    except Exception:
        pass

    return None


__all__ = ["detect_system_language"]
