const classesTabActive = [
  "text-black",
  "underline",
  "underline-offset-[11px]",
  "decoration-gray-900",
  "decoration-[3px]",
];
const inactiveClasses = ["text-gray-900"];

document.addEventListener("DOMContentLoaded", function () {
  setUpTabGroups("tabs-activity", classesTabActive, inactiveClasses);
});

// document.addEventListener("htmx:afterRequest", (e) => {
//   setUpTabGroups("tabs-activity", classesTabActive, inactiveClasses);
// });
