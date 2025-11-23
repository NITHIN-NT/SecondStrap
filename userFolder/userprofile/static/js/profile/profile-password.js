document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("passwordForm");
    if (!form) return;

    const newPwd = document.getElementById("new_password");
    const confirmPwd = document.getElementById("confirm_password");
    const errorEl = document.getElementById("passwordMatchError");
    const csrfInput = document.querySelector('input[name="csrfmiddlewaretoken"]');

    form.addEventListener("submit", function (e) {
        e.preventDefault(); // stop normal form submit

        // simple frontend validation
        if (newPwd.value !== confirmPwd.value) {
            if (errorEl) errorEl.style.display = "block";
            return;
        } else {
            if (errorEl) errorEl.style.display = "none";
        }

        const csrfToken = csrfInput ? csrfInput.value : "";
        const url = form.action;

        const formData = new FormData(form);

        axios.post(url, formData, {
            headers: {
                "X-CSRFToken": csrfToken,
            },
        })
        .then(function (response) {
            const data = response.data;

            if (data.status === "success") {
                toastr.success(data.message || "Password updated successfully! (frontend)");
                form.reset();
            } else {
                // just in case backend sends 200 with status=error
                toastr.error(data.message || "Something went wrong while updating password. (frontend)");
            }
        })
        .catch(function (error) {
            let msg = "Something went wrong while updating password. (frontend)";

            if (error.response && error.response.data) {
                // backend uses "message", not "error"
                if (error.response.data.message) {
                    msg = error.response.data.message;
                }
            }

            toastr.error(msg);
        });
    });
});
