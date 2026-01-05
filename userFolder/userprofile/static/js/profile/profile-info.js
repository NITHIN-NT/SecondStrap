document.addEventListener("DOMContentLoaded", () => {

    // ==================================================
    // 1. COPY REFERRAL CODE LOGIC
    // ==================================================
    const copyButton = document.getElementById("shareBtn");
    const referralInput = document.getElementById("referralLink");
    const copyText = document.getElementById("shareText");
    const copyIcon = document.getElementById("shareIcon");

    if (copyButton && referralInput) {
        copyButton.addEventListener("click", () => {
            referralInput.select();
            referralInput.setSelectionRange(0, 99999);

            navigator.clipboard.writeText(referralInput.value)
                .then(() => {
                    if (copyText) copyText.textContent = "Copied!";
                    if (copyIcon) copyIcon.className = "bx bx-check";
                    copyButton.classList.add("copied");

                    setTimeout(() => {
                        if (copyText) copyText.textContent = "Share";
                        if (copyIcon) copyIcon.className = "bx bx-share";
                        copyButton.classList.remove("copied");
                    }, 2000);
                })
                .catch(err => console.error("Copy failed:", err));
        });
    }

    // ==================================================
    // 2. EDIT PROFILE MODAL LOGIC
    // ==================================================
    const modal = document.getElementById("editProfileModal");
    const openBtn = document.querySelector(".edit-link");
    const closeBtn = document.getElementById("closeModalBtn");
    const cancelBtn = document.getElementById("cancelBtn");

    const openModal = (e) => {
        e.preventDefault();
        modal?.classList.add("active");
    };

    const closeModal = () => {
        modal?.classList.remove("active");
    };

    openBtn?.addEventListener("click", openModal);
    closeBtn?.addEventListener("click", closeModal);
    cancelBtn?.addEventListener("click", closeModal);

    window.addEventListener("click", (e) => {
        if (e.target === modal) closeModal();
    });

    // ==================================================
    // 3. EDIT PROFILE SUBMIT (AJAX + REDIRECT)
    // ==================================================
    const editForm = document.getElementById("editProfileForm");
    const saveBtn = document.getElementById("saveBtn");

    const displayEmail = document.getElementById("display_email");
    const displayName = document.getElementById("display_fullname");
    const displayPhone = document.getElementById("display_phone");

    if (editForm) {
        editForm.addEventListener("submit", async (e) => {
            e.preventDefault();

            const url = editForm.action;
            const formData = new FormData(editForm);

            const payload = {
                first_name: formData.get("first_name"),
                last_name: formData.get("last_name"),
                email: formData.get("email"),
                phone: formData.get("phone"),
            };

            const csrfToken =
                document.querySelector("[name=csrfmiddlewaretoken]")?.value || "";

            const originalBtnText = saveBtn?.innerText || "";

            if (saveBtn) {
                saveBtn.innerText = "Saving...";
                saveBtn.disabled = true;
            }

            try {
                const response = await axios.post(url, payload, {
                    headers: {
                        "X-CSRFToken": csrfToken,
                        "Content-Type": "application/json",
                    },
                });

                if (response.data.status === "email_changed") {
                    toastr.info(response.data.message);
                    window.location.href = response.data.redirect_url;
                    return;
                }
                
                if (response.data.status === "success") {
                    if (displayName) {
                        displayName.textContent =
                            `${payload.first_name} ${payload.last_name}`.trim();
                    }

                    if (displayPhone) {
                        displayPhone.textContent =
                            payload.phone ? `+91 ${payload.phone}` : "Not provided";
                    }

                    if (displayEmail) {
                        displayEmail.textContent = payload.email;
                    }

                    closeModal();
                    toastr.success(response.data.message);
                } else {
                    toastr.error(response.data.message || "Profile update failed");
                }
            } catch (error) {
                console.error("Axios Error:", error);
                toastr.error("Something went wrong");
            } finally {
                if (saveBtn) {
                    saveBtn.innerText = originalBtnText;
                    saveBtn.disabled = false;
                }
            }
        });
    }
});
