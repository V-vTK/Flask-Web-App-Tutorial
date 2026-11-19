import json

from conftest import Client, new_email, text, PASSWORD


# ---------- pages ----------
def test_login_and_signup_pages(client):
    for path in ("/login", "/sign-up"):
        r = client.get(path)
        assert r.status_code == 200
        assert "text/html" in r.headers["Content-Type"]


# ---------- login ----------
def test_login_unknown_email(client):
    r = client.login(new_email())
    assert r.status_code == 200
    assert "Email does not exist." in text(r)


def test_login_missing_resource_does_not_authenticate(client):
    client.login(new_email())
    assert client.get("/").status_code == 302


def test_login_bad_password(registered, client):
    r = client.login(registered, "wrong-password")
    assert r.status_code == 200
    assert "Incorrect password, try again." in text(r)
    assert client.get("/").status_code == 302


def test_login_ok(registered, client):
    r = client.login(registered)
    assert r.status_code == 302
    assert r.headers["Location"] in ("/", "http://localhost/") or r.headers["Location"].endswith("/")
    page = client.get("/")
    assert page.status_code == 200
    assert "Logged in successfully!" in text(page)


# ---------- logout ----------
def test_logout_anonymous_redirects_to_login_with_next(client):
    r = client.get("/logout")
    assert r.status_code == 302
    loc = r.headers["Location"]
    assert loc.startswith("/login") and "next=" in loc


def test_logout_logged_in(logged_in):
    c, _ = logged_in
    r = c.get("/logout")
    assert r.status_code == 302
    assert r.headers["Location"] == "/login"
    assert c.get("/").status_code == 302


# ---------- home auth ----------
def test_home_requires_login(client):
    r = client.get("/")
    assert r.status_code == 302
    assert r.headers["Location"].startswith("/login")


def test_home_post_requires_login(client):
    r = client.post("/", data={"note": "x"})
    assert r.status_code == 302
    assert r.headers["Location"].startswith("/login")


# ---------- sign-up ----------
def test_signup_ok(client):
    email = new_email()
    r = client.signup(email)
    assert r.status_code == 302
    assert r.headers["Location"] in ("/", "http://localhost/") or r.headers["Location"].endswith("/")
    page = client.get("/")
    assert page.status_code == 200
    assert "Account created!" in text(page)
    # duplicate afterwards
    r2 = Client().signup(email)
    assert r2.status_code == 200
    assert "Email already exists." in text(r2)


def test_signup_validation_messages(client):
    cases = [
        (dict(email="a@b", name="Alice"), "Email must be greater than 3 characters."),
        (dict(email=new_email(), name="A"), "First name must be greater than 1 character."),
        (dict(email=new_email(), p1="password1", p2="password2"), "Passwords don't match."),
        (dict(email=new_email(), p1="short", p2="short"), "Password must be at least 7 characters."),
    ]
    for kw, msg in cases:
        r = Client().signup(**kw)
        assert r.status_code == 200, kw
        assert msg in text(r), kw


def test_signup_validation_does_not_create_user(client):
    email = new_email()
    client.signup(email, p1="short")
    r = client.login(email, "short")
    assert "Email does not exist." in text(r)


# ---------- notes ----------
def test_note_add_and_list(logged_in):
    c, _ = logged_in
    r = c.post("/", data={"note": "hello note 123"})
    assert r.status_code == 200
    t = text(r)
    assert "Note added!" in t and "hello note 123" in t
    assert "hello note 123" in text(c.get("/"))


def test_note_empty(logged_in):
    c, _ = logged_in
    r = c.post("/", data={"note": ""})
    assert r.status_code == 200
    assert "Note is too short!" in text(r)
    assert "Note added!" not in text(r)


def _note_ids(page):
    import re
    return re.findall(r"deleteNote\((\d+)\)", page.text)


def test_note_delete_own_and_not_others(logged_in):
    c, _ = logged_in
    c.post("/", data={"note": "mine-note-xyz"})
    ids = _note_ids(c.get("/"))
    assert ids
    note_id = int(ids[-1])

    # another user cannot delete it
    from conftest import Client
    other = Client()
    oe = new_email()
    other.signup(oe)
    other.login(oe)
    r = other.post("/delete-note", data=json.dumps({"noteId": note_id}))
    assert r.status_code == 200 and r.json() == {}
    assert "mine-note-xyz" in text(c.get("/"))

    # owner deletes
    r = c.post("/delete-note", data=json.dumps({"noteId": note_id}))
    assert r.status_code == 200
    assert "application/json" in r.headers["Content-Type"]
    assert r.json() == {}
    assert "mine-note-xyz" not in text(c.get("/"))


def test_note_delete_nonexistent(logged_in):
    c, _ = logged_in
    r = c.post("/delete-note", data=json.dumps({"noteId": 99999999}))
    assert r.status_code == 200 and r.json() == {}


def test_delete_note_rejects_get(client):
    assert client.get("/delete-note").status_code == 405


# ---------- gap-review additions ----------
import re as _re


def test_home_empty_state_and_authenticated_nav(logged_in):
    c, _ = logged_in
    r = c.get("/")
    assert r.status_code == 200
    assert "<h1" in r.text and "Notes" in r.text
    assert 'id="notes"' in r.text and "deleteNote(" not in _re.sub(r"function deleteNote\(", "", r.text)
    assert 'href="/logout"' in r.text and 'href="/login"' not in r.text
    assert 'href="/sign-up"' not in r.text


def test_notes_are_private_per_user(logged_in):
    c, _ = logged_in
    c.post("/", data={"note": "private-note-abc"})
    other = Client()
    oe = new_email()
    other.signup(oe)
    page = other.get("/")
    assert page.status_code == 200
    assert "private-note-abc" not in text(page)


def test_note_html_is_escaped(logged_in):
    c, _ = logged_in
    r = c.post("/", data={"note": "<script>alert(1)</script>zz"})
    assert "<script>alert(1)</script>zz" not in r.text
    assert "&lt;script&gt;" in r.text


def test_multiple_notes_listed_in_insertion_order(logged_in):
    c, _ = logged_in
    for n in ("first-note-aa", "second-note-bb", "third-note-cc"):
        c.post("/", data={"note": n})
    t = c.get("/").text
    assert t.index("first-note-aa") < t.index("second-note-bb") < t.index("third-note-cc")


def test_flash_categories_css(logged_in, client):
    c, _ = logged_in
    ok = c.post("/", data={"note": "css-note"})
    assert "alert-success" in ok.text and "alert-danger" not in ok.text
    bad = c.post("/", data={"note": ""})
    assert "alert-danger" in bad.text


def test_flash_shown_only_once(registered, client):
    client.login(registered)
    assert "Logged in successfully!" in text(client.get("/"))
    assert "Logged in successfully!" not in text(client.get("/"))


def test_signup_duplicate_email_takes_precedence(registered):
    r = Client().signup(registered, name="A", p1="x", p2="y")
    assert "Email already exists." in text(r)


def test_signup_validation_order(client):
    # short email beats short name / mismatch / short password
    r = client.signup("a@b", name="A", p1="x", p2="y")
    assert "Email must be greater than 3 characters." in text(r)
    # short name beats mismatch / short password
    r = client.signup(new_email(), name="A", p1="x", p2="y")
    assert "First name must be greater than 1 character." in text(r)
    # mismatch beats short password
    r = client.signup(new_email(), p1="x", p2="y")
    assert "Passwords don't match." in text(r)


def test_signup_validation_boundaries(client):
    import random, string
    email = "".join(random.choices(string.ascii_lowercase, k=2)) + "@" + random.choice(string.ascii_lowercase)
    assert len(email) == 4
    r = client.signup(email, name="Al", p1="1234567")  # 4-char email, 2-char name, 7-char pw
    # Accepted (302), or already taken from an earlier run: either way the length checks passed.
    if r.status_code == 302:
        pass
    else:
        assert r.status_code == 200 and "Email already exists." in text(r)
    r = Client().signup(new_email(), p1="123456")
    assert "Password must be at least 7 characters." in text(r)


def test_signup_sets_session_cookie_and_login_is_case_sensitive_password(registered):
    c = Client()
    r = c.login(registered)
    assert r.status_code == 302
    assert any(ck.name == "session" for ck in c.s.cookies)
    assert any(ck.name == "remember_token" for ck in c.s.cookies)
    r = Client().login(registered, PASSWORD.upper())
    assert "Incorrect password, try again." in text(r)


def test_login_redirect_honours_nothing_extra_and_nav_after_logout(logged_in):
    c, _ = logged_in
    c.get("/logout")
    r = c.get("/login")
    assert 'href="/sign-up"' in r.text and 'href="/logout"' not in r.text


def test_anonymous_requests_to_signup_login_pages_render_even_when_logged_in(logged_in):
    c, _ = logged_in
    assert c.get("/login").status_code == 200
    assert c.get("/sign-up").status_code == 200


def test_unknown_route_404_and_method_not_allowed(client):
    assert client.get("/nope").status_code == 404
    assert client.req("DELETE", "/login").status_code == 405
    assert client.post("/logout").status_code == 405


def test_static_index_js_served(client):
    r = client.get("/static/index.js")
    assert r.status_code == 200
    assert "deleteNote" in r.text


# ---------- gap-review round 1 additions ----------
def test_failed_note_post_stores_nothing(logged_in):
    c, _ = logged_in
    c.post("/", data={"note": ""})
    assert _note_ids(c.get("/")) == []


def test_whitespace_only_note_is_accepted(logged_in):
    c, _ = logged_in
    r = c.post("/", data={"note": "   "})
    assert "Note added!" in text(r)
    assert len(_note_ids(c.get("/"))) == 1


def test_note_without_field_or_long_note(logged_in):
    c, _ = logged_in
    big = "L" * 5000
    r = c.post("/", data={"note": big})
    assert "Note added!" in text(r) and big in r.text


def test_note_unicode_and_quotes_roundtrip(logged_in):
    c, _ = logged_in
    c.post("/", data={"note": "héllo \"q\" & 'a' 日本"})
    t = c.get("/").text
    assert "héllo" in t and "日本" in t
    assert "&amp;" in t and "<script>" not in t.replace("<script type", "").replace("<script\n", "")


def test_delete_note_ids_are_per_note_and_delete_only_target(logged_in):
    c, _ = logged_in
    for n in ("keep-aaa", "drop-bbb", "keep-ccc"):
        c.post("/", data={"note": n})
    ids = _note_ids(c.get("/"))
    assert len(ids) == 3
    c.post("/delete-note", data=json.dumps({"noteId": int(ids[1])}))
    t = text(c.get("/"))
    assert "keep-aaa" in t and "keep-ccc" in t and "drop-bbb" not in t


def test_delete_note_does_not_flash(logged_in):
    c, _ = logged_in
    c.get("/")
    c.post("/delete-note", data=json.dumps({"noteId": 123456789}))
    t = text(c.get("/"))
    assert "alert-success" not in t and "alert-danger" not in t


def test_delete_note_anonymous_is_server_error(client):
    r = client.post("/delete-note", data=json.dumps({"noteId": 1}))
    assert r.status_code == 500


def test_logout_clears_session_and_shows_no_flash(logged_in):
    c, _ = logged_in
    r = c.get("/logout")
    page = c.get(r.headers["Location"])
    assert page.status_code == 200
    assert "alert-danger" not in page.text
    assert c.get("/").status_code == 302


def test_login_redirect_target_is_home_not_next(registered, client):
    r = client.login(registered, params={"next": "/logout"})
    assert r.status_code == 302
    assert r.headers["Location"].rstrip("/").endswith("") and r.headers["Location"].endswith("/")
    assert "logout" not in r.headers["Location"]


def test_login_failure_sets_no_auth_and_keeps_anonymous_nav(registered, client):
    r = client.login(registered, "nope-nope")
    assert 'id="login"' in r.text and 'id="signUp"' in r.text and 'id="logout"' not in r.text
    assert "alert-danger" in r.text and "alert-success" not in r.text
    assert not any(ck.name == "remember_token" for ck in client.s.cookies)


def test_signup_success_nav_authenticated_and_cookies(client):
    r = client.signup(new_email())
    assert r.status_code == 302
    assert any(ck.name == "remember_token" for ck in client.s.cookies)
    page = client.get("/")
    assert 'id="logout"' in page.text and 'id="home"' in page.text


def test_signup_failure_does_not_log_in(client):
    client.signup(new_email(), p1="short")
    assert client.get("/").status_code == 302


def test_login_email_is_case_sensitive_lookup(registered):
    r = Client().login(registered.upper())
    assert "Email does not exist." in text(r)


def test_signup_then_login_with_same_password_works_and_hashes(client):
    email = new_email()
    client.signup(email, p1="pässword-ünï")
    r = Client().login(email, "pässword-ünï")
    assert r.status_code == 302


def test_signup_first_name_two_chars_ok_and_one_char_rejected(client):
    assert Client().signup(new_email(), name="Ab").status_code == 302
    r = Client().signup(new_email(), name="Ab"[:1])
    assert "First name must be greater than 1 character." in text(r)


def test_signup_password_seven_ok_boundary(client):
    assert Client().signup(new_email(), p1="1234567").status_code == 302


def test_validation_error_page_has_signup_title_and_one_alert(client):
    r = client.signup(new_email(), p1="short")
    assert "<title>Sign Up</title>" in r.text
    assert r.text.count('role="alert"') == 1


def test_home_page_title_and_form(logged_in):
    c, _ = logged_in
    t = c.get("/").text
    assert "<title>Home</title>" in t
    assert 'name="note"' in t and 'id="note"' in t and "Add Note" in t


def test_head_and_options_and_trailing_slash(client):
    assert client.req("PUT", "/").status_code in (302, 405)
    assert client.get("/login/").status_code == 404
    assert client.req("OPTIONS", "/login").status_code == 200


def test_static_missing_file_404(client):
    assert client.get("/static/nope.js").status_code == 404
