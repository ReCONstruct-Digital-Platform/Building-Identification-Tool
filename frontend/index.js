function component() {
  const element = document.createElement("div");
  element.innerHTML = "Hello webpack!! super awesome HMR";
  return element;
}
document.body.appendChild(component());
