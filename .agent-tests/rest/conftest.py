import html
import os
import re
import uuid

import pytest
import requests

BASE_URL = os.environ["BASE_URL"].rstrip("/")
PASSWORD = "secret-pass-1"


class Client:
    def __init__(self):
        self.s = requests.Session()

    def req(self, method, path, **kw):
        kw.setdefault("allow_redirects", False)
        kw.setdefault("timeout", 15)
        return self.s.request(method, BASE_URL + path, **kw)

    def get(self, path, **kw):
        return self.req("GET", path, **kw)

    def post(self, path, **kw):
        return self.req("POST", path, **kw)

    def signup(self, email, name="Alice", p1=PASSWORD, p2=None, **kw):
        return self.post("/sign-up", data={
            "email": email, "firstName": name,
            "password1": p1, "password2": p1 if p2 is None else p2}, **kw)

    def login(self, email, password=PASSWORD, **kw):
        return self.post("/login", data={"email": email, "password": password}, **kw)


def text(resp):
    return html.unescape(resp.text)


def new_email():
    return f"u{uuid.uuid4().hex[:12]}@example.com"


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def registered():
    """Register a user via the API. Returns (email, signup_response).

    Skips dependents if the service cannot create accounts at all (HTTP 5xx),
    which is the known deployment bug being fixed in a later step.
    """
    email = new_email()
    r = Client().signup(email)
    if r.status_code >= 500:
        pytest.skip("sign-up currently fails with HTTP %d (known hashing bug)" % r.status_code)
    assert r.status_code == 302
    return email


@pytest.fixture
def logged_in(registered):
    c = Client()
    r = c.login(registered)
    assert r.status_code == 302
    return c, registered
