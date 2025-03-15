
// data-collapse-target=<id of target>
function setUpCollapsibleInfoBox() {
  
    const infoBox = document.getElementById('bldg-cols-display');
    const collapseButton = document.getElementById('infobox-collapse-button')
    const iconCollapse = document.getElementById("infobox-collapse-icon");
    const iconExpand = document.getElementById("infobox-expand-icon");
    const horizontalRule = document.getElementById('infobox-hr')

    collapseButton.addEventListener("click", (e) => {
        const isCollapsed = infoBox.classList.contains("max-h-0")
        if (isCollapsed) {
            console.debug("opening collapsible", infoBox);
            infoBox.classList.remove("max-h-0");
            infoBox.classList.add("max-h-[100vh]");
            infoBox.classList.add("grid");

            infoBox.removeAttribute("collapsed");
            iconCollapse.classList.remove("hidden");
            iconExpand.classList.add("hidden");
            horizontalRule.classList.remove("hidden")
        } else {
            console.debug("closing collapsible", infoBox);
            infoBox.classList.add("max-h-0");
            infoBox.classList.remove("max-h-[100vh]");
            infoBox.setAttribute("collapsed", "");
            infoBox.classList.remove("grid");
            
            iconExpand.classList.remove("hidden");
            iconCollapse.classList.add("hidden");
            horizontalRule.classList.add("hidden")
        }
    });
  }
  

document.addEventListener("DOMContentLoaded", function () {
    setUpCollapsibleInfoBox();
});