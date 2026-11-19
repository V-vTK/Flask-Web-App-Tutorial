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


def _auth_session():
    import uuid
    s = requests.Session()
    email = f"h{uuid.uuid4().hex[:10]}@example.com"
    r = s.post(BASE_URL + "/sign-up", data={"email": email, "firstName": "Hh",
               "password1": "secret-pass-1", "password2": "secret-pass-1"},
               allow_redirects=False, timeout=15)
    assert r.status_code == 302
    return s


def test_placeholders_and_input_ids():
    s = page("/login")
    assert {i["name"]: i.get("placeholder") for i in s.find("form").find_all("input")} == {
        "email": "Enter email", "password": "Enter password"}
    s = page("/sign-up")
    ph = {i["name"]: i.get("placeholder") for i in s.find("form").find_all("input")}
    assert ph["email"] == "Enter email" and ph["firstName"] == "Enter first name"
    assert ph["password1"] == "Enter password" and ph["password2"] == "Confirm password"


def test_navbar_ids_anonymous():
    s = page("/login")
    assert [a["id"] for a in s.find("nav").find_all("a")] == ["login", "signUp"]


def test_home_page_semantics_authenticated():
    sess = _auth_session()
    r = sess.get(BASE_URL + "/", timeout=15)
    s = BeautifulSoup(r.text, "html.parser")
    assert s.title.get_text(strip=True) == "Home"
    assert [h.get_text(strip=True) for h in s.find_all(["h1", "h2", "h3"])] == ["Notes"]
    assert nav_links(s) == [("Home", "/"), ("Logout", "/logout")]
    assert [a["id"] for a in s.find("nav").find_all("a")] == ["home", "logout"]
    ul = s.find("ul", id="notes")
    assert ul is not None and ul.find_all("li") == []
    ta = s.find("form").find("textarea")
    assert ta["name"] == "note" and ta["id"] == "note"
    assert [b.get_text(strip=True) for b in s.find("form").find_all("button")] == ["Add Note"]
    # one-time "Account created!" success alert
    alerts = s.find_all(attrs={"role": "alert"})
    assert len(alerts) == 1 and "alert-success" in alerts[0]["class"]
    assert "Account created!" in alerts[0].get_text()
    assert alerts[0].find("button", class_="close") is not None


def test_home_note_list_item_markup():
    sess = _auth_session()
    r = sess.post(BASE_URL + "/", data={"note": "markup-note"}, timeout=15)
    s = BeautifulSoup(r.text, "html.parser")
    lis = s.find("ul", id="notes").find_all("li")
    assert len(lis) == 1 and "list-group-item" in lis[0]["class"]
    assert "markup-note" in lis[0].get_text()
    btn = lis[0].find("button", class_="close")
    assert btn is not None and btn["onclick"].startswith("deleteNote(")
    assert s.find("div", class_="alert-success") is not None


def test_error_alert_uses_danger_class():
    r = requests.post(BASE_URL + "/login", data={"email": "zz-nobody@example.com", "password": "x"}, timeout=15)
    s = BeautifulSoup(r.text, "html.parser")
    a = s.find(attrs={"role": "alert"})
    assert "alert-danger" in a["class"]
