import { createRoot } from "react-dom/client";

import MyApp from "./src/App";

const app = createRoot(document.getElementById("root"));
app.render(MyApp("Welcome to my Django, Typescript React app"));
