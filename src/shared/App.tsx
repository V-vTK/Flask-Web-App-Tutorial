import React from "react";

export type Flash = { category: string; message: string };
export type NoteView = { id: number; data: string };
export type PageState = {
  page: "home" | "login" | "sign-up";
  authenticated: boolean;
  flashes: Flash[];
  notes: NoteView[];
};

export const titles = { home: "Home", login: "Login", "sign-up": "Sign Up" } as const;

export function deleteNote(noteId: number): void {
  fetch("/delete-note", { method: "POST", body: JSON.stringify({ noteId }) }).then(() => {
    window.location.href = "/";
  });
}

function Navbar({ authenticated }: { authenticated: boolean }) {
  return (
    <nav className="navbar navbar-expand-lg navbar-dark bg-dark">
      <button className="navbar-toggler" type="button" data-toggle="collapse" data-target="#navbar">
        <span className="navbar-toggler-icon"></span>
      </button>
      <div className="collapse navbar-collapse" id="navbar">
        <div className="navbar-nav">
          {authenticated ? (
            <>
              <a className="nav-item nav-link" id="home" href="/">Home</a>
              <a className="nav-item nav-link" id="logout" href="/logout">Logout</a>
            </>
          ) : (
            <>
              <a className="nav-item nav-link" id="login" href="/login">Login</a>
              <a className="nav-item nav-link" id="signUp" href="/sign-up">Sign Up</a>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}

function Alerts({ flashes }: { flashes: Flash[] }) {
  return (
    <>
      {flashes.map((f, i) => (
        <div
          key={i}
          className={`alert ${f.category === "error" ? "alert-danger" : "alert-success"} alter-dismissable fade show`}
          role="alert"
        >
          {f.message}
          <button type="button" className="close" data-dismiss="alert">
            <span aria-hidden="true">&times;</span>
          </button>
        </div>
      ))}
    </>
  );
}

function Field(props: { id: string; label: string; type: string; placeholder: string }) {
  return (
    <div className="form-group">
      <label htmlFor={props.id}>{props.label}</label>
      <input type={props.type} className="form-control" id={props.id} name={props.id} placeholder={props.placeholder} />
    </div>
  );
}

function Login() {
  return (
    <form method="POST">
      <h3 {...{ align: "center" }}>Login</h3>
      <Field id="email" label="Email Address" type="email" placeholder="Enter email" />
      <Field id="password" label="Password" type="password" placeholder="Enter password" />
      <br />
      <button type="submit" className="btn btn-primary">Login</button>
    </form>
  );
}

function SignUp() {
  return (
    <form method="POST">
      <h3 {...{ align: "center" }}>Sign Up</h3>
      <Field id="email" label="Email Address" type="email" placeholder="Enter email" />
      <Field id="firstName" label="First Name" type="text" placeholder="Enter first name" />
      <Field id="password1" label="Password" type="password" placeholder="Enter password" />
      <Field id="password2" label="Password (Confirm)" type="password" placeholder="Confirm password" />
      <br />
      <button type="submit" className="btn btn-primary">Submit</button>
    </form>
  );
}

function Home({ notes }: { notes: NoteView[] }) {
  return (
    <>
      <h1 {...{ align: "center" }}>Notes</h1>
      <ul className="list-group list-group-flush" id="notes">
        {notes.map((n) => (
          <li className="list-group-item" key={n.id}>
            {n.data}
            {/* server render rewrites data-onclick to a real onclick attribute */}
            <button type="button" className="close" {...{ "data-onclick": `deleteNote(${n.id})` }} onClick={() => deleteNote(n.id)}>
              <span aria-hidden="true">&times;</span>
            </button>
          </li>
        ))}
      </ul>
      <form method="POST">
        <textarea name="note" id="note" className="form-control"></textarea>
        <br />
        <div {...{ align: "center" }}>
          <button type="submit" className="btn btn-primary">Add Note</button>
        </div>
      </form>
    </>
  );
}

export function App({ state }: { state: PageState }) {
  return (
    <>
      <Navbar authenticated={state.authenticated} />
      <Alerts flashes={state.flashes} />
      <div className="container">
        {state.page === "login" && <Login />}
        {state.page === "sign-up" && <SignUp />}
        {state.page === "home" && <Home notes={state.notes} />}
      </div>
    </>
  );
}
