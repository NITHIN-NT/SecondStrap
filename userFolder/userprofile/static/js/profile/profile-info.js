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
            referralInput.setSelectionRange(0, 99999); // Mobile compatibility
            try {
                navigator.clipboard.writeText(referralInput.value);
                if (copyText) copyText.textContent = "Copied!";
                if (copyIcon) copyIcon.className = "bx bx-check";
                copyButton.classList.add("copied");
                setTimeout(() => {
                    if (copyText) copyText.textContent = "Share";
                    if (copyIcon) copyIcon.className = "bx bx-share";
                    copyButton.classList.remove("copied");
                }, 2000);
            } catch (err) {
                console.error("Failed to share text: ", err);
            }
        });
    }

    // ==================================================
    // 2. EDIT PROFILE MODAL & LOGIC
    // ==================================================
    const modal = document.getElementById("editProfileModal");
    const openBtn = document.querySelector(".edit-link");
    const closeBtn = document.getElementById("closeModalBtn");
    const cancelBtn = document.getElementById("cancelBtn");
    const editForm = document.getElementById("editProfileForm");
    const saveBtn = document.getElementById("saveBtn");

    // Email UI Elements
    const emailWrapper = document.querySelector(".email-with-status");
    const displayEmail = document.getElementById("display_email");
    const verifiedIcon = document.querySelector(".verified-tick");
    const notVerifiedPill = document.querySelector(".verify-pill");
    let originalEmail = displayEmail ? displayEmail.textContent.trim() : null;

    // --- Helper: Toggle UI ---
    function setEmailVerifiedUI(isVerified) {
        if (!emailWrapper) return;
        if (isVerified) {
            emailWrapper.classList.add("row-layout");
            emailWrapper.classList.remove("col-layout");
            if (verifiedIcon) verifiedIcon.style.display = "inline-flex";
            if (notVerifiedPill) notVerifiedPill.style.display = "none";
        } else {
            emailWrapper.classList.remove("row-layout");
            emailWrapper.classList.add("col-layout");
            if (verifiedIcon) verifiedIcon.style.display = "none";
            if (notVerifiedPill) notVerifiedPill.style.display = "inline-flex";
        }
    }

    // --- Open/Close Modal ---
    const openModal = (e) => {
        e.preventDefault();
        if (modal) modal.classList.add("active");
    };
    const closeModal = () => {
        if (modal) modal.classList.remove("active");
    };

    if (openBtn) openBtn.addEventListener("click", openModal);
    if (closeBtn) closeBtn.addEventListener("click", closeModal);
    if (cancelBtn) cancelBtn.addEventListener("click", closeModal);
    window.addEventListener("click", (e) => {
        if (e.target === modal) closeModal();
    });

    // --- Edit Profile Submission (FIXED TO SEND JSON) ---
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

            const csrfTokenEl = document.querySelector("[name=csrfmiddlewaretoken]");
            const csrfToken = csrfTokenEl ? csrfTokenEl.value : "";

            const originalBtnText = saveBtn ? saveBtn.innerText : "";
            if (saveBtn) {
                saveBtn.innerText = "Saving...";
                saveBtn.disabled = true;
            }

            try {
                const response = await axios.post(url, JSON.stringify(payload), {
                    headers: {
                        "X-CSRFToken": csrfToken,
                        "Content-Type": "application/json",
                    },
                });

                if (response.data.status === "success") {
                    const dName = document.getElementById("display_fullname");
                    const dPhone = document.getElementById("display_phone");

                    if (dName) {
                        dName.textContent = `${payload.first_name || ""} ${payload.last_name || ""}`.trim();
                    }
                    if (dPhone) {
                        dPhone.textContent = payload.phone ? `+91 ${payload.phone}` : "Not provided";
                    }
                    if (displayEmail) {
                        displayEmail.textContent = payload.email || "";
                    }

                    const newEmail = (payload.email || "").trim();
                    if (originalEmail && newEmail && newEmail !== originalEmail) {
                        // Email changed -> mark as not verified in UI
                        setEmailVerifiedUI(false);
                    } else if (typeof response.data.is_verified !== "undefined") {
                        setEmailVerifiedUI(!!response.data.is_verified);
                    }

                    // Update originalEmail so subsequent changes compare correctly
                    if (newEmail) {
                        originalEmail = newEmail;
                    }

                    closeModal();
                    toastr.success(response.data.message);
                } else {
                    toastr.error(response.data.message || "Error updating profile");
                }
            } catch (error) {
                console.error("Axios Error:", error);
                toastr.error("Error updating profile");
            } finally {
                if (saveBtn) {
                    saveBtn.innerText = originalBtnText;
                    saveBtn.disabled = false;
                }
            }
        });
    }

    // ==================================================
    // 3. OTP MODAL, TIMER & VERIFICATION LOGIC
    // ==================================================

    const otpModal = document.getElementById("otpModal");
    const verifyNowBtn = document.getElementById("verifyNowBtn");
    const closeOtpBtn = document.getElementById("closeOtpBtn");
    const otpInputs = document.querySelectorAll(".otp-letters");
    const resendBtn = document.getElementById("resendOtpBtn");
    const timerSpan = document.getElementById("resendTimer");
    const otpForm = document.getElementById("otpForm");
    const realOtpValue = document.getElementById("realOtpValue");

    let resendInterval;

    // --- A. Helper: Start 1 Minute Timer ---
    function startResendTimer() {
        if (!resendBtn || !timerSpan) return;

        let timeLeft = 60;
        resendBtn.disabled = true;
        timerSpan.textContent = `(${timeLeft}s)`;

        if (resendInterval) clearInterval(resendInterval);

        resendInterval = setInterval(() => {
            timeLeft--;
            timerSpan.textContent = `(${timeLeft}s)`;

            if (timeLeft <= 0) {
                clearInterval(resendInterval);
                resendBtn.disabled = false;
                timerSpan.textContent = "";
            }
        }, 1000);
    }

    // --- B. Input Auto-Focus Logic ---
    otpInputs.forEach((input, index) => {
        input.addEventListener("input", (e) => {
            if (e.target.value.length === 1 && index < otpInputs.length - 1) {
                otpInputs[index + 1].focus();
            }
        });

        input.addEventListener("keydown", (e) => {
            if (e.key === "Backspace" && e.target.value === "" && index > 0) {
                otpInputs[index - 1].focus();
            }
        });
    });

    // --- C. "Verify Now" Click (Send OTP + Open Modal) ---
    if (verifyNowBtn && otpModal) {
        const originalHTML = verifyNowBtn.innerHTML;
        verifyNowBtn.addEventListener("mouseover", () => {
            verifyNowBtn.innerHTML = "<i class='bx bxs-check-circle'></i> Verify Now";
        });
        verifyNowBtn.addEventListener("mouseleave", () => {
            verifyNowBtn.innerHTML = originalHTML;
        });

        verifyNowBtn.addEventListener("click", function (e) {
            e.preventDefault();

            verifyNowBtn.innerHTML = '<i class="bx bx-loader-alt bx-spin"></i> Sending...';
            const url = verifyNowBtn.getAttribute("href");

            axios
                .get(url)
                .then(function (response) {
                    if (response.data.status === "success") {
                        otpModal.classList.add("active");

                        if (otpInputs.length > 0) {
                            otpInputs.forEach((i) => (i.value = ""));
                            otpInputs[0].focus();
                        }

                        startResendTimer();
                        toastr.success("OTP sent to your email.");
                    } else {
                        toastr.error(response.data.message);
                    }
                })
                .catch(function (error) {
                    console.error("Error:", error);
                    toastr.error("Could not send OTP.");
                })
                .finally(() => {
                    verifyNowBtn.innerHTML = originalHTML;
                });
        });
    }

    // --- D. "Resend" Click Logic ---
    if (resendBtn && verifyNowBtn) {
        resendBtn.addEventListener("click", function (e) {
            e.preventDefault();

            const url = verifyNowBtn.getAttribute("href");
            if (!url) return;

            axios
                .get(url)
                .then((response) => {
                    if (response.data.status === "success") {
                        toastr.success("OTP Resent successfully!");
                        startResendTimer();
                    } else {
                        toastr.error(response.data.message);
                    }
                })
                .catch((err) => {
                    console.error(err);
                    toastr.error("Could not resend OTP.");
                });
        });
    }

    // --- E. Verify OTP Form Submission ---
    if (otpForm) {
        otpForm.addEventListener("submit", function (e) {
            e.preventDefault();

            let otpCode = "";
            otpInputs.forEach((input) => (otpCode += input.value));

            if (realOtpValue) realOtpValue.value = otpCode;

            const url = otpForm.action || "/verify_otp_axios/";

            const formData = new FormData(otpForm);
            formData.append("otp", otpCode);

            const csrfTokenEl = document.querySelector("[name=csrfmiddlewaretoken]");
            const csrfToken = csrfTokenEl ? csrfTokenEl.value : "";

            const submitBtn = document.getElementById("verifyBtn");
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerText = "Verifying...";
            }

            axios
                .post(url, formData, {
                    headers: { "X-CSRFToken": csrfToken },
                })
                .then((response) => {
                    if (response.data.status === "success") {
                        toastr.success("Email verified successfully!");
                        if (otpModal) otpModal.classList.remove("active");
                        setEmailVerifiedUI(true);
                    } else {
                        toastr.error(response.data.message || "Invalid OTP");
                    }
                })
                .catch((error) => {
                    console.error(error);
                    toastr.error("Verification failed.");
                })
                .finally(() => {
                    if (submitBtn) {
                        submitBtn.disabled = false;
                        submitBtn.innerText = "Verify";
                    }
                });
        });
    }

    // --- F. Close Modal Logic ---
    if (closeOtpBtn && otpModal) {
        closeOtpBtn.addEventListener("click", () => {
            otpModal.classList.remove("active");
            if (resendInterval) clearInterval(resendInterval);
        });
    }

    window.addEventListener("click", (e) => {
        if (e.target === otpModal) {
            otpModal.classList.remove("active");
            if (resendInterval) clearInterval(resendInterval);
        }
    });
});
