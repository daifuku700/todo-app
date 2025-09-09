# auth.py
import os
import msal
from functools import wraps
from flask import session, redirect, url_for


def build_msal_app(cache=None):
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    authority = os.getenv("AUTHORITY")  # https://login.microsoftonline.com/{TENANT_ID}
    return msal.ConfidentialClientApplication(
        client_id,
        authority=authority,
        client_credential=client_secret,
        token_cache=cache,
    )


def build_auth_url(flow):
    return flow["auth_uri"]


def load_cache():
    return msal.SerializableTokenCache()


def save_cache(cache):
    pass  # 今回はトークン再利用しないため何もしない


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("signin"))
        return view(*args, **kwargs)

    return wrapped
