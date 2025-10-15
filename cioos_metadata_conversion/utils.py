import re

def drop_empty_values(dictionary):
    return {k: v for k, v in dictionary.items() if v}

def camel_to_title(s: str) -> str:
    """
    Convert camelCase / PascalCase / mixed-with_separators to Title Case.
    Examples:
      surfaceTemperature -> Surface Temperature
      SurfaceTemperature -> Surface Temperature
      XMLHTTPRequest     -> XML HTTP Request
      httpServerError    -> Http Server Error
    """
    if not s:
        return ""
    s = re.sub(r'[_\-]+', ' ', s)  # turn separators into spaces
    s = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', s)  # split acronym + word
    s = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', s)     # split camel hump
    words = s.split()
    out = []
    for w in words:
        if w.isupper() and len(w) > 1:    # keep acronyms
            out.append(w)
        else:
            out.append(w[:1].upper() + w[1:].lower())
    return " ".join(out)
