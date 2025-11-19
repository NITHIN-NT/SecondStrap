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

            // 1. Get the rendered URL from the HTML form
            // This will be "/profile/api/update-profile/", NOT "{% url ... %}"
            const url = editForm.action;
            const formDataObj = new FormData(editForm);
            const formData = Object.fromEntries(formDataObj.entries());
            // const firstName = document.getElementById("firstName").value.trim();
            // const lastName = document.getElementById("lastName").value.trim();
            // const phoneNumber = document.getElementById("phoneNumber").value.trim();

            // const formData = {
            //     first_name: firstName,
            //     last_name: lastName,
            //     phone: phoneNumber
            // };

            const originalBtnText = saveBtn.innerText;
            saveBtn.innerText = "Saving...";
            saveBtn.disabled = true;


            try {
                // 2. Use the variable 'url' here
                const response = await axios.post(url, formData, {
                    headers: {
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                    }
                });

                if (response.data.status === 'success') {

                    const displayName = document.getElementById('display_fullname');
                    const displayPhone = document.getElementById('display_phone');

                    displayName.textContent = `${formData.first_name} ${formData.last_name}`;

                    if (formData.phone) {
                        displayPhone.textContent = `+91 ${formData.phone}`;
                    } else {
                        displayPhone.textContent = "Not provided";
                    }
                    closeModal();
                    // 2. TRIGGER THE TOAST (The new part)
                    toastr.success(response.data.message);

                } else {
                    // alert("Error updating profile: " + response.data.message);
                    Swal.fire({
                        // icon: "error",
                        title: "Oops...",
                        text: "Error updating profile " + response.data.message,
                        // The footer link will now automatically be black with Barlow font
                        // footer: '<a href="#">Why do I have this issue?</a>',
                        // Optional: If you want a black confirm button explicitly
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