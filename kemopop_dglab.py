from kemopop import run
from kemopop import i18n


if __name__ == "__main__":
    # Set language based on system preferences with fallback to en-us
    try:
        i18n.set_language_from_system(fallback='en-us')
    except Exception:
        pass
    run()
