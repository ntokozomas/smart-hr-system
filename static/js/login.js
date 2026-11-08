// Login page: show/hide password and a Caps Lock warning.
(function () {
  var input = document.querySelector(".password-wrap input");
  var toggle = document.querySelector(".toggle-password");
  var caps = document.querySelector(".caps-warning");
  if (!input) return;

  if (toggle) {
    toggle.addEventListener("click", function () {
      var show = input.type === "password";
      input.type = show ? "text" : "password";
      toggle.setAttribute("aria-pressed", show ? "true" : "false");
      toggle.setAttribute("aria-label", show ? "Hide password" : "Show password");
      input.focus();
    });
  }

  function checkCaps(event) {
    if (caps && event.getModifierState) {
      caps.hidden = !event.getModifierState("CapsLock");
    }
  }
  input.addEventListener("keydown", checkCaps);
  input.addEventListener("keyup", checkCaps);
  input.addEventListener("blur", function () { if (caps) caps.hidden = true; });
})();
