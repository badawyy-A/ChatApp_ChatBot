import numpy as np
from urllib.parse import urlparse
import joblib
import re


def extract_features(url):
    shorteners = ['bit.ly', 'goo.gl', 'tinyurl', 'ow.ly', 't.co', 'is.gd', 'buff.ly']
    
    return np.array([[
        len(url),                            # url_length
        url.count('.'),                      # dot_count
        1 if re.match(r'^(http[s]?://)?(\d{1,3}\.){3}\d{1,3}', url) else 0,  # has_ip
        url.count('-'),                      # hyphen_count
        url.count('@'),                      # at_count
        url.count('=') + url.count('&') + url.count('%'),  # suspicious_char_count
        len(urlparse(url).path),             # path_length
        len(urlparse(url).query),            # query_length
        1 if url.startswith('https') else 0, # is_https
        1 if any(s in url for s in shorteners) else 0       # is_shortened
    ]])


