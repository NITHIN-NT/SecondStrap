document.addEventListener("DOMContentLoaded", () => {

    // --- Existing Copy Logic ---
    const copyButton = document.getElementById("copyBtn");
    const referralInput = document.getElementById("referralLink");
    const copyText = document.getElementById("copyText");
    const copyIcon = document.getElementById("copyIcon");

    if (copyButton) {
        copyButton.addEventListener("click", () => {
            referralInput.select();
            referralInput.setSelectionRange(0, 99999);
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

    // --- MODAL & AXIOS LOGIC ---

    const modal = document.getElementById('editProfileModal');
    const openBtn = document.querySelector('.edit-link');
    const closeBtn = document.getElementById('closeModalBtn');
    const cancelBtn = document.getElementById('cancelBtn');
    const editForm = document.getElementById('editProfileForm');
    const saveBtn = document.getElementById('saveBtn');

    // Email + verification elements
    const emailWrapper = document.querySelector(".email-with-status");
    const displayEmail = document.getElementById("display_email");
    const verifiedIcon = document.querySelector(".verified-tick");
    const notVerifiedPill = document.querySelector(".verify-pill");

    // Capture initial email from page
    const originalEmail = displayEmail ? displayEmail.textContent.trim() : null;

    // Helper: toggle UI between verified / not verified
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

    // Hover text change Verify
    const verifBtn = document.getElementById('verifyNowBtn');

    if (verifBtn) {
        const originalHTML = verifBtn.innerHTML; // "<i ...> Not Verified"

        verifBtn.addEventListener('mouseover', () => {
            verifBtn.innerHTML = "<i class='bx bxs-check-circle'></i> Verify Now";
        });

        verifBtn.addEventListener('mouseleave', () => {
            verifBtn.innerHTML = originalHTML;
        });
    }
    
    // Open/Close Logic
    const openModal = (e) => {
        e.preventDefault();
        if (modal) modal.classList.add('active');
    };

    const closeModal = () => {
        if (modal) modal.classList.remove('active');
    };

    if (openBtn) openBtn.addEventListener('click', openModal);
    if (closeBtn) closeBtn.addEventListener('click', closeModal);
    if (cancelBtn) cancelBtn.addEventListener('click', closeModal);

    window.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeModal();
        }
    });

    // Form Submission Logic
    if (editForm) {
        editForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const url = editForm.action;
            const formDataObj = new FormData(editForm);
            const formData = Object.fromEntries(formDataObj.entries());

            const originalBtnText = saveBtn.innerText;
            saveBtn.innerText = "Saving...";
            saveBtn.disabled = true;

            try {
                const response = await axios.post(url, formData, {
                    headers: {
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                    }
                });

                if (response.data.status === 'success') {

                    const displayName = document.getElementById('display_fullname');
                    const displayPhone = document.getElementById('display_phone');

                    if (displayName) {
                        displayName.textContent = `${formData.first_name} ${formData.last_name}`;
                    }

                    if (displayPhone) {
                        if (formData.phone) {
                            displayPhone.textContent = `+91 ${formData.phone}`;
                        } else {
                            displayPhone.textContent = "Not provided";
                        }
                    }

                    // Update email on page
                    if (displayEmail && formData.email) {
                        displayEmail.textContent = formData.email;
                    }

                    // --- EMAIL VERIFICATION RULE ---
                    // If email changed compared to what was originally loaded => force NOT VERIFIED
                    const newEmail = (formData.email || "").trim();
                    if (originalEmail && newEmail && newEmail !== originalEmail) {
                        setEmailVerifiedUI(false);
                    } else if (typeof response.data.is_verified !== "undefined") {
                        setEmailVerifiedUI(!!response.data.is_verified);
                    }

                    closeModal();
                    toastr.success(response.data.message);

                } else {
                    Swal.fire({
                        title: "Oops...",
                        text: "Error updating profile " + response.data.message,
                        confirmButtonText: "Close"
                    });
                }

            } catch (error) {
                console.error("Axios Error:", error);
                alert("An error occurred while saving. Check console for details.");
            } finally {
                saveBtn.innerText = originalBtnText;
                saveBtn.disabled = false;
            }
        });
    }
});
