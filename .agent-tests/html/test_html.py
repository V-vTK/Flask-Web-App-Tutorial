import os

import pytest
import requests
from bs4 import BeautifulSoup

BASE_URL = os.environ["BASE_URL"].rstrip("/")


def page(path):
    r = requests.get(BASE_URL + path, timeout=15)
    assert r.status_code == 200
    assert "text/html" in r.headers["Content-Type"]
    return BeautifulSoup(r.text, "html.parser")


def label_map(soup):
    """Map each form control name -> (label text, type, id) via label[for]."""
    out = {}
    for inp in soup.find("form").find_all("input"):
        lab = soup.find("label", attrs={"for": inp.get("id")})
        out[inp["name"]] = (lab.get_text(strip=True) if lab else None, inp["type"])
    return out


def nav_links(soup):
    nav = soup.find("nav")
    return [(a.get_text(strip=True), a["href"]) for a in nav.find_all("a")]


def test_login_page_semantics():
    s = page("/login")
    assert s.title.get_text(strip=True) == "Login"
    assert [h.get_text(strip=True) for h in s.find_all(["h1", "h2", "h3"])] == ["Login"]
    forms = s.find_all("form")
    assert len(forms) == 1 and forms[0]["method"].upper() == "POST"
    assert label_map(s) == {
        "email": ("Email Address", "email"),
        "password": ("Password", "password"),
    }
    buttons = forms[0].find_all("button")
    assert [(b.get_text(strip=True), b.get("type")) for b in buttons] == [("Login", "submit")]
    # anonymous navigation
    assert nav_links(s) == [("Login", "/login"), ("Sign Up", "/sign-up")]
    assert s.find("a", href="/logout") is None
    # no flash alerts on a fresh visit
    assert s.find(attrs={"role": "alert"}) is None


def test_signup_page_semantics():
    s = page("/sign-up")
    assert s.title.get_text(strip=True) == "Sign Up"
    assert [h.get_text(strip=True) for h in s.find_all(["h1", "h2", "h3"])] == ["Sign Up"]
    forms = s.find_all("form")
    assert len(forms) == 1 and forms[0]["method"].upper() == "POST"
    assert label_map(s) == {
        "email": ("Email Address", "email"),
        "firstName": ("First Name", "text"),
        "password1": ("Password", "password"),
        "password2": ("Password (Confirm)", "password"),
    }
    buttons = forms[0].find_all("button")
    assert [(b.get_text(strip=True), b.get("type")) for b in buttons] == [("Submit", "submit")]
    assert nav_links(s) == [("Login", "/login"), ("Sign Up", "/sign-up")]
    assert s.find(attrs={"role": "alert"}) is None


def test_login_error_alert_is_accessible():
    r = requests.post(BASE_URL + "/login",
                      data={"email": "nobody-html@example.com", "password": "whatever1"},
                      timeout=15)
    s = BeautifulSoup(r.text, "html.parser")
    alerts = s.find_all(attrs={"role": "alert"})
    assert len(alerts) == 1
    assert "Email does not exist." in alerts[0].get_text()
    assert s.title.get_text(strip=True) == "Login"


def test_signup_validation_alert_is_rendered():
    r = requests.post(BASE_URL + "/sign-up",
                      data={"email": "abc", "firstName": "Alice",
                            "password1": "secret-pass-1", "password2": "secret-pass-1"},
                      timeout=15)
    s = BeautifulSoup(r.text, "html.parser")
    alerts = s.find_all(attrs={"role": "alert"})
    assert len(alerts) == 1
    assert "Email must be greater than 3 characters." in alerts[0].get_text()


def test_anonymous_home_redirects_to_login():
    r = requests.get(BASE_URL + "/", allow_redirects=False, timeout=15)
    assert r.status_code == 302
    assert r.headers["Location"].startswith("/login")
