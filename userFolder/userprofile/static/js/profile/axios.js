document.addEventListener("DOMContentLoaded", () => {

    // ==================================================
    // 1. COPY REFERRAL CODE LOGIC
    // ==================================================
    const copyButton = document.getElementById("copyBtn");
    const referralInput = document.getElementById("referralLink");
    const copyText = document.getElementById("copyText");
    const copyIcon = document.getElementById("copyIcon");

    if (copyButton) {
        copyButton.addEventListener("click", () => {
            referralInput.select();
            referralInput.setSelectionRange(0, 99999); // Mobile compatibility
            try {
                navigator.clipboard.writeText(referralInput.value);
                copyText.textContent = "Copied!";
                copyIcon.className = 'bx bx-check';
                copyButton.classList.add("copied");
                setTimeout(() => {
                    copyText.textContent = "Copy";
                    copyIcon.className = 'bx bx-copy';
                    copyButton.classList.remove("copied");
                }, 2000);
            } catch (err) {
                console.error("Failed to copy text: ", err);
            }
        });
    }

    // ==================================================
    // 2. EDIT PROFILE MODAL & LOGIC
    // ==================================================
    const modal = document.getElementById('editProfileModal');
    const openBtn = document.querySelector('.edit-link');
    const closeBtn = document.getElementById('closeModalBtn');
    const cancelBtn = document.getElementById('cancelBtn');
    const editForm = document.getElementById('editProfileForm');
    const saveBtn = document.getElementById('saveBtn');

    // Email UI Elements
    const emailWrapper = document.querySelector(".email-with-status");
    const displayEmail = document.getElementById("display_email");
    const verifiedIcon = document.querySelector(".verified-tick");
    const notVerifiedPill = document.querySelector(".verify-pill");
    const originalEmail = displayEmail ? displayEmail.textContent.trim() : null;

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
    const openModal = (e) => { e.preventDefault(); if (modal) modal.classList.add('active'); };
    const closeModal = () => { if (modal) modal.classList.remove('active'); };

    if (openBtn) openBtn.addEventListener('click', openModal);
    if (closeBtn) closeBtn.addEventListener('click', closeModal);
    if (cancelBtn) cancelBtn.addEventListener('click', closeModal);
    window.addEventListener('click', (e) => { if (e.target === modal) closeModal(); });

    // --- Edit Profile Submission ---
    if (editForm) {
        editForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const url = editForm.action;
            const formData = new FormData(editForm);

            const originalBtnText = saveBtn.innerText;
            saveBtn.innerText = "Saving...";
            saveBtn.disabled = true;

            try {
                const response = await axios.post(url, formData, {
                    headers: { 'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value }
                });

                if (response.data.status === 'success') {
                    // Update DOM
                    const dName = document.getElementById('display_fullname');
                    const dPhone = document.getElementById('display_phone');

                    if (dName) dName.textContent = `${formData.get('first_name')} ${formData.get('last_name')}`;
                    if (dPhone) dPhone.textContent = formData.get('phone') ? `+91 ${formData.get('phone')}` : "Not provided";
                    if (displayEmail) displayEmail.textContent = formData.get('email');

                    // Check if email changed -> Reset Verification
                    const newEmail = (formData.get('email') || "").trim();
                    if (originalEmail && newEmail && newEmail !== originalEmail) {
                        setEmailVerifiedUI(false);
                    } else if (typeof response.data.is_verified !== "undefined") {
                        setEmailVerifiedUI(!!response.data.is_verified);
                    }

                    closeModal();
                    toastr.success(response.data.message);
                } else {
                    toastr.error(response.data.message || "Error updating profile");
                }
            } catch (error) {
                console.error("Axios Error:", error);
            } finally {
                saveBtn.innerText = originalBtnText;
                saveBtn.disabled = false;
            }
        });
    }

    // ==================================================
    // 3. OTP MODAL, TIMER & VERIFICATION LOGIC
    // ==================================================

    const otpModal = document.getElementById('otpModal');
    const verifyNowBtn = document.getElementById('verifyNowBtn');
    const closeOtpBtn = document.getElementById('closeOtpBtn');
    const otpInputs = document.querySelectorAll('.otp-letters'); // Updated class name
    const resendBtn = document.getElementById('resendOtpBtn');
    const timerSpan = document.getElementById('resendTimer');
    const otpForm = document.getElementById('otpForm');
    const realOtpValue = document.getElementById('realOtpValue');

    let resendInterval; // Variable to store the timer

    // --- A. Helper: Start 1 Minute Timer ---
    function startResendTimer() {
        if (!resendBtn || !timerSpan) return;

        let timeLeft = 60; // 60 seconds

        // Reset UI
        resendBtn.disabled = true;
        timerSpan.textContent = `(${timeLeft}s)`;

        if (resendInterval) clearInterval(resendInterval);

        resendInterval = setInterval(() => {
            timeLeft--;
            timerSpan.textContent = `(${timeLeft}s)`;

            if (timeLeft <= 0) {
                clearInterval(resendInterval);
                resendBtn.disabled = false;
                timerSpan.textContent = ''; // Clear text
            }
        }, 1000);
    }

    // --- B. Input Auto-Focus Logic (UX) ---
    otpInputs.forEach((input, index) => {
        // Move to next input on typing
        input.addEventListener('input', (e) => {
            if (e.target.value.length === 1) {
                if (index < otpInputs.length - 1) {
                    otpInputs[index + 1].focus();
                }
            }
        });

        // Move to previous input on Backspace
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Backspace' && e.target.value === '') {
                if (index > 0) {
                    otpInputs[index - 1].focus();
                }
            }
        });
    });

    // --- C. "Verify Now" Click (Send OTP + Open Modal) ---
    if (verifyNowBtn) {
        // Hover Effects
        const originalHTML = verifyNowBtn.innerHTML;
        verifyNowBtn.addEventListener('mouseover', () => verifyNowBtn.innerHTML = "<i class='bx bxs-check-circle'></i> Verify Now");
        verifyNowBtn.addEventListener('mouseleave', () => verifyNowBtn.innerHTML = originalHTML);

        // Click Logic
        verifyNowBtn.addEventListener('click', function (e) {
            e.preventDefault();

            verifyNowBtn.innerHTML = '<i class="bx bx-loader-alt bx-spin"></i> Sending...';
            const url = verifyNowBtn.getAttribute('href');

            axios.get(url)
                .then(function (response) {
                    if (response.data.status === 'success') {
                        // Open Modal
                        otpModal.classList.add('active');

                        // Focus first input
                        if (otpInputs.length > 0) {
                            otpInputs.forEach(i => i.value = ''); // Clear old values
                            otpInputs[0].focus();
                        }

                        // Start Timer
                        startResendTimer();

                        toastr.success("OTP sent to your email.");
                    } else {
                        toastr.error(response.data.message);
                    }
                })
                .catch(function (error) {
                    console.error('Error:', error);
                    toastr.error("Could not send OTP.");
                })
                .finally(() => {
                    verifyNowBtn.innerHTML = originalHTML;
                });
        });
    }

    // --- D. "Resend" Click Logic ---
    if (resendBtn) {
        resendBtn.addEventListener('click', function (e) {
            e.preventDefault();

            // Use the same URL as the initial send
            const url = verifyNowBtn.getAttribute('href');

            axios.get(url)
                .then(response => {
                    if (response.data.status === 'success') {
                        toastr.success("OTP Resent successfully!");
                        startResendTimer(); // Restart timer
                    } else {
                        toastr.error(response.data.message);
                    }
                })
                .catch(err => console.error(err));
        });
    }

    // --- E. Verify OTP Form Submission ---
    if (otpForm) {
        otpForm.addEventListener('submit', function (e) {
            e.preventDefault();

            // Combine the 4 boxes into one string
            let otpCode = '';
            otpInputs.forEach(input => otpCode += input.value);

            if (realOtpValue) realOtpValue.value = otpCode;

            const url = otpForm.action || "/verify_otp_axios/";

            const formData = new FormData(otpForm);
            formData.append('otp', otpCode);

            const submitBtn = document.getElementById('verifyBtn');
            submitBtn.disabled = true;
            submitBtn.innerText = "Verifying...";

            axios.post(url, formData, {
                headers: { 'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value }
            })
                .then(response => {
                    if (response.data.status === 'success') {
                        toastr.success("Email verified successfully!");
                        otpModal.classList.remove('active');
                        setEmailVerifiedUI(true);
                    } else {
                        toastr.error(response.data.message || "Invalid OTP");
                    }
                })
                .catch(error => {
                    console.error(error);
                    toastr.error("Verification failed.");
                })
                .finally(() => {
                    submitBtn.disabled = false;
                    submitBtn.innerText = "Verify";
                });
        });
    }

    // --- F. Close Modal Logic ---
    if (closeOtpBtn) {
        closeOtpBtn.addEventListener('click', () => {
            otpModal.classList.remove('active');
            if (resendInterval) clearInterval(resendInterval); // Optional: stop timer on close
        });
    }

    window.addEventListener('click', (e) => {
        if (e.target === otpModal) {
            otpModal.classList.remove('active');
            if (resendInterval) clearInterval(resendInterval);
        }
    });

});