import express, { type Request, type Response, type NextFunction } from "express";
import cookieSession from "cookie-session";
import crypto from "node:crypto";
import path from "node:path";
import fs from "node:fs";
import React from "react";
import { renderToString } from "react-dom/server";
import { App, titles, type PageState, type Flash } from "../shared/App";
import * as store from "./db";

const SECRET = process.env.SECRET_KEY ?? "hjshjhdjah kjshkjdhjs";
const ROOT = process.cwd();
const clientDir = path.join(ROOT, "dist", "client");
const staticDir = path.join(ROOT, "public", "static");

type Sess = { userId?: number; flashes?: Flash[] } | null | undefined;
const sess = (req: Request) => req.session as unknown as NonNullable<Sess>;

const app = express();
app.disable("x-powered-by");
app.set("strict routing", true);
app.use(cookieSession({ name: "session", keys: [SECRET], httpOnly: true, sameSite: "lax" }));
app.use(express.urlencoded({ extended: false }));
app.use(express.text({ type: () => true }));

// ---- remember-me cookie ----
const sign = (v: string) => crypto.createHmac("sha256", SECRET).update(v).digest("hex");
const REMEMBER_MAX_AGE = 365 * 24 * 3600 * 1000;
function setRemember(res: Response, userId: number) {
  const v = String(userId);
  res.cookie("remember_token", `${v}|${sign(v)}`, { httpOnly: true, maxAge: REMEMBER_MAX_AGE, path: "/" });
}
function rememberedUser(req: Request): number | undefined {
  const raw = (req.headers.cookie ?? "").split(/;\s*/).find((c) => c.startsWith("remember_token="));
  if (!raw) return undefined;
  const [v, mac] = decodeURIComponent(raw.slice("remember_token=".length)).split("|");
  if (!v || !mac) return undefined;
  const a = Buffer.from(mac), b = Buffer.from(sign(v));
  return a.length === b.length && crypto.timingSafeEqual(a, b) ? Number(v) : undefined;
}

function currentUser(req: Request): store.User | undefined {
  let id = sess(req).userId;
  if (id === undefined) {
    id = rememberedUser(req);
    if (id !== undefined) sess(req).userId = id;
  }
  return id === undefined ? undefined : store.findUserById(id);
}

function flash(req: Request, message: string, category: "error" | "success") {
  const s = sess(req);
  s.flashes = [...(s.flashes ?? []), { category, message }];
}
function takeFlashes(req: Request): Flash[] {
  const s = sess(req);
  const f = s.flashes ?? [];
  if (s.flashes) delete s.flashes;
  return f;
}

function login(req: Request, res: Response, userId: number) {
  sess(req).userId = userId;
  setRemember(res, userId);
}

// ---- page rendering (React SSR; hydrated by the client bundle) ----
const esc = (s: string) => s.replace(/</g, "\\u003c").replace(/>/g, "\\u003e").replace(/&/g, "\\u0026");
const shell = fs.existsSync(path.join(clientDir, "assets", "app.js"));

function render(req: Request, res: Response, page: PageState["page"], user: store.User | undefined) {
  const state: PageState = {
    page,
    authenticated: !!user,
    flashes: takeFlashes(req),
    notes: page === "home" && user ? store.notesFor(user.id) : [],
  };
  const body = renderToString(React.createElement(App, { state })).replace(/ data-onclick="/g, ' onclick="');
  res.type("html").send(`<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.4.1/css/bootstrap.min.css" integrity="sha384-Vkoo8x4CGsO3+Hhxv8T/Q5PaXtkKtu6ug5TOeNV6gBiFeWPGFN9MuhOf23Q9Ifjh" crossorigin="anonymous" />
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/font-awesome/4.7.0/css/font-awesome.min.css" crossorigin="anonymous" />
    <title>${titles[page]}</title>
  </head>
  <body>
    <div id="root">${body}</div>
    <script src="https://code.jquery.com/jquery-3.2.1.slim.min.js" integrity="sha384-KJ3o2DKtIkvYIK3UENzmM7KCkRr/rE9/Qpg6aAZGJwFDMVNA/GpGFF93hXpG5KkN" crossorigin="anonymous"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.12.9/umd/popper.min.js" integrity="sha384-ApNbgh9B+Y1QKtv3Rn7W3mgPxhU9K/ScQsAP7hUibX39j7fakFPskvXusvfa0b4Q" crossorigin="anonymous"></script>
    <script src="https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0/js/bootstrap.min.js" integrity="sha384-JZR6Spejh4U02d8jOt6vLEHfe/JQGiRRSQQxSfFWpi1MquVdAyjUar5+76PVCmYl" crossorigin="anonymous"></script>
    <script type="text/javascript">
      function deleteNote(noteId) {
        fetch("/delete-note", { method: "POST", body: JSON.stringify({ noteId: noteId }) }).then((_res) => {
          window.location.href = "/";
        });
      }
    </script>
    <script type="application/json" id="__state">${esc(JSON.stringify(state))}</script>
    ${shell ? '<script type="module" src="/assets/app.js"></script>' : ""}
  </body>
</html>`);
}

// ---- helpers ----
const len = (s: unknown): number => {
  if (typeof s !== "string") throw new TypeError("object of type 'NoneType' has no len()");
  return [...s].length;
};
const field = (req: Request, k: string): string | undefined => {
  const v = (req.body ?? {})[k];
  return typeof v === "string" ? v : undefined;
};

function methods(path: string, handlers: Partial<Record<"get" | "post", express.RequestHandler>>) {
  const allow = [...Object.keys(handlers).map((m) => m.toUpperCase()), ...(handlers.get ? ["HEAD"] : []), "OPTIONS"].join(", ");
  const r = app.route(path);
  if (handlers.get) r.get(handlers.get);
  if (handlers.post) r.post(handlers.post);
  r.all((req, res) => {
    res.set("Allow", allow);
    if (req.method === "OPTIONS") return void res.status(200).send();
    res.status(405).type("html").send("<!doctype html><title>405 Method Not Allowed</title><h1>Method Not Allowed</h1><p>The method is not allowed for the requested URL.</p>");
  });
}

function loginRequired(h: express.RequestHandler): express.RequestHandler {
  return (req, res, next) => {
    const user = currentUser(req);
    if (!user) return void res.redirect(302, `/login?next=${encodeURIComponent(req.originalUrl)}`);
    (req as any).user = user;
    return h(req, res, next);
  };
}
const userOf = (req: Request) => (req as any).user as store.User;

// ---- routes ----
methods("/login", {
  get: (req, res) => render(req, res, "login", currentUser(req)),
  post: (req, res) => {
    const email = field(req, "email");
    const user = store.findUserByEmail(email);
    if (user) {
      const pw = field(req, "password");
      if (pw === undefined) throw new TypeError("password is None");
      if (store.checkPassword(user.password, pw)) {
        flash(req, "Logged in successfully!", "success");
        login(req, res, user.id);
        return void res.redirect(302, "/");
      }
      flash(req, "Incorrect password, try again.", "error");
    } else {
      flash(req, "Email does not exist.", "error");
    }
    render(req, res, "login", currentUser(req));
  },
});

methods("/logout", {
  get: loginRequired((req, res) => {
    delete sess(req).userId;
    res.clearCookie("remember_token", { path: "/" });
    res.redirect(302, "/login");
  }),
});

methods("/sign-up", {
  get: (req, res) => render(req, res, "sign-up", currentUser(req)),
  post: (req, res) => {
    const email = field(req, "email");
    const firstName = field(req, "firstName");
    const p1 = field(req, "password1");
    const p2 = field(req, "password2");
    if (store.findUserByEmail(email)) flash(req, "Email already exists.", "error");
    else if (len(email) < 4) flash(req, "Email must be greater than 3 characters.", "error");
    else if (len(firstName) < 2) flash(req, "First name must be greater than 1 character.", "error");
    else if (p1 !== p2) flash(req, "Passwords don't match.", "error");
    else if (len(p1) < 7) flash(req, "Password must be at least 7 characters.", "error");
    else {
      const id = store.createUser(email!, firstName!, store.hashPassword(p1!));
      login(req, res, id);
      flash(req, "Account created!", "success");
      return void res.redirect(302, "/");
    }
    render(req, res, "sign-up", currentUser(req));
  },
});

methods("/", {
  get: loginRequired((req, res) => render(req, res, "home", userOf(req))),
  post: loginRequired((req, res) => {
    const note = field(req, "note");
    if (len(note) < 1) flash(req, "Note is too short!", "error");
    else {
      store.addNote(note!, userOf(req).id);
      flash(req, "Note added!", "success");
    }
    render(req, res, "home", userOf(req));
  }),
});

methods("/delete-note", {
  post: (req, res) => {
    const body = JSON.parse(typeof req.body === "string" ? req.body : "");
    if (body.noteId === undefined) throw new Error("KeyError: noteId");
    const user = currentUser(req);
    if (!user) throw new Error("anonymous user has no id");
    const note = store.findNote(body.noteId);
    if (note && note.user_id === user.id) store.deleteNoteById(note.id);
    res.json({});
  },
});

app.use("/static", express.static(staticDir, { fallthrough: true }));
app.use("/assets", express.static(path.join(clientDir, "assets"), { fallthrough: true }));

app.use((_req, res) => {
  res.status(404).type("html").send("<!doctype html><title>404 Not Found</title><h1>Not Found</h1><p>The requested URL was not found on the server.</p>");
});
app.use((err: unknown, _req: Request, res: Response, _next: NextFunction) => {
  console.error(err);
  res.status(500).type("html").send("<!doctype html><title>500 Internal Server Error</title><h1>Internal Server Error</h1>");
});

const port = Number(process.env.PORT ?? 5001);
app.listen(port, "0.0.0.0", () => console.log(`listening on ${port}`));
