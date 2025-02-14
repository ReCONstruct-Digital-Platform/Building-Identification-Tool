class Toast {
  constructor(elem) {
    this.elem = elem;
  }
  hide() {
    console.debug("hiding");
    this.elem.classList.add("hidden");
    this.elem.classList.remove("flex");
  }
  show() {
    console.debug("showing");
    this.elem.classList.remove("hidden");
    this.elem.classList.add("flex");
    setTimeout(() => {
      console.debug("timeout");
      this.hide();
    }, 2000);
  }
}

const toasts = {};

function setUpToasts() {
  const toastElements = document.getElementsByClassName("my-toast");
  Array.from(toastElements).forEach((toast) => {
    console.debug("Setting up toast", toast);
    const id = toast.id;
    const closeButton = toast.querySelector(".close-toast-button");
    closeButton.addEventListener("click", (event) => {
      event.preventDefault();
      toast.classList.remove("flex");
      toast.classList.add("hidden");
    });
    toasts[id] = new Toast(toast);
  });
}

function getCookie(name) {
  var cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    var cookies = document.cookie.split(";");
    for (var i = 0; i < cookies.length; i++) {
      var cookie = jQuery.trim(cookies[i]);
      // Does this cookie string begin with the name we want?
      if (cookie.substring(0, name.length + 1) === name + "=") {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

/**
 * Adapted from https://stackoverflow.com/a/30106551
 */
function b64EncodeUnicode(str) {
  if (!str) return null;
  // first we use encodeURIComponent to get percent-encoded Unicode,
  // then we convert the percent encodings into raw bytes which
  // can be fed into btoa.
  return btoa(
    encodeURIComponent(str).replace(/%([0-9A-F]{2})/g, function toSolidBytes(match, p1) {
      return String.fromCharCode("0x" + p1);
    })
  );
}
function b64DecodeUnicode(str) {
  if (!str) return null;
  // Going backwards: from bytestream, to percent-encoding, to original string.
  return decodeURIComponent(
    atob(str)
      .split("")
      .map(function (c) {
        return "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2);
      })
      .join("")
  );
}

/**
 * Our own simple modals.
 * Modals have an open button, two close buttons (top and bottom).
 * Clicking anywhere outside or pressing the escape key will also close the modal.
 * All modals share a backdrop.
 */
function setUpModal(modal) {
  console.debug("Setting up modal", modal);
  const modalBackdrop = document.getElementById("modal-backdrop");

  const modalIdPrefix = modal.dataset.modalIdPrefix;
  const closeButtonTop = document.getElementById(modalIdPrefix + "_close_top");
  const closeButtonBottom = document.getElementById(modalIdPrefix + "_close_bottom");

  closeButtonTop.addEventListener("click", (e) => {
    e.preventDefault();
    modal.classList.add("hidden");
    modalBackdrop.classList.add("hidden");
    modal.classList.remove("block");
    modalBackdrop.classList.remove("block");
  });

  closeButtonBottom.addEventListener("click", (e) => {
    e.preventDefault();
    modal.classList.add("hidden");
    modalBackdrop.classList.add("hidden");
    modal.classList.remove("block");
    modalBackdrop.classList.remove("block");
  });

  // When the user clicks anywhere outside of the modal, close it
  window.addEventListener("click", (e) => {
    if (e.target === modal) {
      modal.classList.add("hidden");
      modalBackdrop.classList.add("hidden");
      modal.classList.remove("block");
      modalBackdrop.classList.remove("block");
    }
  });
}

function setUpModals() {
  const modals = document.getElementsByClassName("my-modal");
  const modalOpenButtons = document.getElementsByClassName("modal-open-button");
  const modalBackdrop = document.getElementById("modal-backdrop");

  window.addEventListener("keydown", (e) => {
    Array.from(modals).forEach((modal) => {
      if (modal.checkVisibility()) {
        modal.classList.add("hidden");
        modalBackdrop.classList.add("hidden");
        modal.classList.remove("block");
        modalBackdrop.classList.remove("block");
      }
    });
  });

  Array.from(modals).forEach((modal) => setUpModal(modal));

  Array.from(modalOpenButtons).forEach((button) => {
    const target = document.getElementById(button.dataset.targetModal);
    button.addEventListener("click", (e) => {
      e.preventDefault();
      console.debug("clicked", e);
      target.classList.remove("hidden");
      modalBackdrop.classList.remove("hidden");
      target.classList.add("block");
      modalBackdrop.classList.add("block");
    });
  });
}

// From https://blog.logrocket.com/programmatically-downloading-files-browser/
function downloadBlob(blob, filename) {
  // Create an object URL for the blob object
  const url = URL.createObjectURL(blob);

  // Create a new anchor element
  const a = document.createElement("a");

  // Set the href and download attributes for the anchor element
  // You can optionally set other attributes like `title`, etc
  // Especially, if the anchor element will be attached to the DOM
  a.href = url;
  a.download = filename || "download";

  // Click handler that releases the object URL after the element has been clicked
  // This is required for one-off downloads of the blob content
  const clickHandler = () => {
    setTimeout(() => {
      URL.revokeObjectURL(url);
      removeEventListener("click", clickHandler);
    }, 150);
  };

  // Add the click event listener on the anchor element
  // Comment out this line if you don't want a one-off download of the blob content
  a.addEventListener("click", clickHandler, false);

  // Programmatically trigger a click on the anchor element
  // Useful if you want the download to happen automatically
  // Without attaching the anchor element to the DOM
  // Comment out this line if you don't want an automatic download of the blob content
  a.click();

  // Return the anchor element
  // Useful if you want a reference to the element
  // in order to attach it to the DOM or use it in some other way
  return a;
}

/**
 * Custom tab group. Needs each tab's id to be the id of the pane it controls + "-tab".
 * Pass in the classes to add and remove when activating.
 */
function setUpTabGroups(tabGroupId, activeClasses = [], inactiveClasses = []) {
  const allTabLinks = Array.from(document.getElementById(tabGroupId).children);

  allTabLinks.forEach((tablink, i) => {
    
    const tabContentId = tablink.id.replace("-tab", "");
    const tabContent = document.getElementById(tabContentId);

    // Set the first tab as active
    if (i === 0) {
      console.debug("Should be visible", tablink);
      tablink.classList.remove(...inactiveClasses);
      tablink.classList.add(...activeClasses);
      tablink.setAttribute("aria-selected", "true");
      tabContent.classList.add("block");
      tabContent.classList.remove("hidden");
    } else {
      console.debug("Should be hidden", tablink);
      tablink.classList.add(...inactiveClasses);
      tablink.classList.remove(...activeClasses);
      tablink.setAttribute("aria-selected", "false");
      tabContent.classList.remove("block");
      tabContent.classList.add("hidden");
    }

    // Add an event listener to each tab
    tablink.addEventListener("click", (e) => {
      const clickedTab = e.target;

      // Set the clicked tab to visible
      clickedTab.classList.remove(...inactiveClasses);
      clickedTab.classList.add(...activeClasses);
      clickedTab.setAttribute("aria-selected", "true");

      const clickedTabContentId = clickedTab.id.replace("-tab", "");

      const tabContent = document.getElementById(clickedTabContentId);
      tabContent.classList.add("block");
      tabContent.classList.remove("hidden");

      // Hide all other tablinks
      for (const otherTab of allTabLinks) {
        if (otherTab.id !== clickedTab.id) {
          const tabContentElementId = otherTab.id.replace("-tab", "");
          const associatedTabContent = document.getElementById(tabContentElementId);
          otherTab.classList.remove(...activeClasses);
          otherTab.classList.add(...inactiveClasses);
          otherTab.setAttribute("aria-selected", "false");
          associatedTabContent.classList.remove("block");
          associatedTabContent.classList.add("hidden");
          // associatedTabContent.style.display = "none";
        }
      }
    });
  });
}

/**
 * Collapsibles need class="collapsible" and data-collapse-target=<id of target> on the clickable element,
 * and a collapsible icon as a child of the clickable element.
 */
function setUpCollapsibles() {

  function toggleCollapsible(collapsible, target, icon) {
    const isCollapsed = target.classList.contains("max-h-0")
    if (isCollapsed) {
      openCollapsible(collapsible, target, icon)
    } else {
      closeCollapsible(collapsible, target, icon)
    }
  }

  function closeCollapsible(collapsible, target, icon) {
    console.debug("closing collapsible", collapsible);
    target.classList.add("max-h-0");
    target.classList.remove("max-h-[500px]");
    collapsible.setAttribute("collapsed", "");
    icon.classList.remove("rotate-180");
  }

  function openCollapsible(collapsible, target, icon) {
    console.debug("opening collapsible", collapsible);
    target.classList.remove("max-h-0");
    target.classList.add("max-h-[500px]");
    collapsible.setAttribute("collapsed", "");
    icon.classList.add("rotate-180");
  }


  const collapsibles = document.getElementsByClassName("collapsible");

  Array.from(collapsibles).forEach((collapsible) => {
    const targetId = collapsible.dataset.collapseTarget;
    const target = document.getElementById(targetId);
    const icon = collapsible.querySelector(".collapse-icon");

    // Set initial state based on collapsed attribute presence
    const shouldBeCollapsed = collapsible.hasAttribute('collapsed');
    
    if (shouldBeCollapsed) {
      console.log("should be collapsed", collapsible)
      closeCollapsible(collapsible, target, icon, true)
    }
    else {
      console.log("should be open", collapsible)
      openCollapsible(collapsible, target, icon, false)
    }
    
    collapsible.addEventListener("click", (e) => {
      console.debug("toggling collapsible", collapsible);
      toggleCollapsible(collapsible, target, icon);
    });
  });
}