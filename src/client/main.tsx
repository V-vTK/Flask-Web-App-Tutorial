import React from "react";
import { hydrateRoot } from "react-dom/client";
import { App, type PageState } from "../shared/App";

const state = JSON.parse(document.getElementById("__state")!.textContent!) as PageState;
hydrateRoot(document.getElementById("root")!, <App state={state} />);
