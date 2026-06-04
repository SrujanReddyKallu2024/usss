import ssl
import httpx
import os

os.environ["CURL_CA_BUNDLE"] = ""
os.environ["REQUESTS_CA_BUNDLE"] = ""
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

_original_client_init = httpx.Client.__init__
_original_async_init = httpx.AsyncClient.__init__


def _patched_client_init(self, *args, **kwargs):
    kwargs["verify"] = False
    _original_client_init(self, *args, **kwargs)


def _patched_async_init(self, *args, **kwargs):
    kwargs["verify"] = False
    _original_async_init(self, *args, **kwargs)


httpx.Client.__init__ = _patched_client_init
httpx.AsyncClient.__init__ = _patched_async_init

ssl._create_default_https_context = ssl._create_unverified_context

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
