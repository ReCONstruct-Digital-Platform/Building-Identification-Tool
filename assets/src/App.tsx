import * as React from "react";
import { useState } from "react";

function MyButton() {
  const [count, setCount] = useState(0);
  return <button onClick={() => setCount(count + 1)}>Pressed {count} times!</button>;
}

export default function MyApp(title: string) {
  return (
    <div>
      <h1>{title}</h1>
      <MyButton />
    </div>
  );
}
