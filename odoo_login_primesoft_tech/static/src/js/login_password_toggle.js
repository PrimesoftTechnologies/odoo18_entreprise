/** @odoo-module **/
// PrimeSoft Tech - show/hide password toggle for the login page.

function enhancePasswordInput(input) {
    if (input.dataset.pstToggle === "1") {
        return;
    }
    input.dataset.pstToggle = "1";

    const wrapper = document.createElement("div");
    wrapper.className = "o_pst_password_wrapper";
    input.parentNode.insertBefore(wrapper, input);
    wrapper.appendChild(input);

    const button = document.createElement("button");
    button.type = "button";
    button.className = "o_pst_password_toggle";
    button.tabIndex = -1;
    button.setAttribute("aria-label", "Show password");
    button.setAttribute("title", "Show password");
    button.innerHTML = '<i class="fa fa-eye" aria-hidden="true"></i>';
    wrapper.appendChild(button);

    button.addEventListener("click", (ev) => {
        ev.preventDefault();
        const show = input.type === "password";
        input.type = show ? "text" : "password";
        const icon = button.querySelector("i");
        icon.className = show ? "fa fa-eye-slash" : "fa fa-eye";
        const label = show ? "Hide password" : "Show password";
        button.setAttribute("aria-label", label);
        button.setAttribute("title", label);
        input.focus();
    });
}

function init() {
    document
        .querySelectorAll(
            ".oe_login_form input[type='password'], .oe_signup_form input[type='password'], .oe_reset_password_form input[type='password']"
        )
        .forEach(enhancePasswordInput);
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
} else {
    init();
}
