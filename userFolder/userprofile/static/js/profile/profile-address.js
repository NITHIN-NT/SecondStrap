document.addEventListener("DOMContentLoaded", () => {

    // =========================================================
    // 1. SELECTORS
    // =========================================================
    
    // -- Add/Edit Modal Elements --
    const modal = document.getElementById("addressModal");
    const openBtn = document.getElementById("addNewAddress");
    const closeBtn = document.getElementById("closeAddressModalBtn");
    const cancelBtn = document.getElementById("cancelAddressBtn");
    const saveBtn = document.getElementById("saveAddressBtn");
    const form = document.getElementById("addressForm");
    const modalTitle = document.getElementById("addressModalTitle");
    const addressIdInput = document.getElementById("address_id");

    // -- Form Inputs --
    const fullNameInput = document.getElementById("full_name");
    const line1Input = document.getElementById("address_line_1");
    const line2Input = document.getElementById("address_line_2");
    const cityInput = document.getElementById("city");
    const stateInput = document.getElementById("state");
    const postalCodeInput = document.getElementById("postal_code");
    const phoneInput = document.getElementById("phone_number");
    const countryInput = document.getElementById("country");
    const isDefaultInput = document.getElementById("is_default");

    // -- Delete Modal Elements --
    const deleteModal = document.getElementById("deleteConfirmModal");
    const deleteForm = document.getElementById("deleteAddressForm");
    const deleteLabel = document.getElementById("deleteAddressLabel");
    const closeDeleteBtn = document.getElementById("closeDeleteModalBtn");
    const cancelDeleteBtn = document.getElementById("cancelDeleteBtn");


    // =========================================================
    // 2. UTILITY FUNCTIONS
    // =========================================================

    // Clear all inline red error messages
    function clearErrors() {
        document.querySelectorAll(".error-msg").forEach(e => e.innerHTML = "");
    }

    // Fetch CSRF token for Axios requests
    function getCsrfToken() {
        const token = document.querySelector("[name=csrfmiddlewaretoken]");
        return token ? token.value : "";
    }

    // Open Add/Edit Modal
    function openModal() {
        modal.classList.add("active");
    }

    // Close Add/Edit Modal & Reset Form
    function closeModal() {
        modal.classList.remove("active");
        form.reset();
        clearErrors();
        modalTitle.textContent = "Add New Address";
        addressIdInput.value = "";
        
        // Reset radio buttons manually
        const radios = document.getElementsByName("address_type");
        radios.forEach(r => r.checked = false);
        
        // Reset button text just in case it was stuck on "Error"
        saveBtn.innerText = "Save Address"; 
    }

    // Close Delete Modal
    function closeDeleteModal() {
        deleteModal.classList.remove("active");
    }


    // =========================================================
    // 3. EVENT LISTENERS (MODAL CONTROLS)
    // =========================================================

    // Open "Add New Address"
    openBtn.addEventListener("click", () => {
        closeModal(); // Ensure clean state
        openModal();
    });

    // Close "Add/Edit" Modal
    closeBtn.addEventListener("click", closeModal);
    cancelBtn.addEventListener("click", closeModal);

    // Close Modals on Click Outside
    window.addEventListener("click", (e) => {
        if (e.target === modal) closeModal();
        if (e.target === deleteModal) closeDeleteModal();
    });


    // =========================================================
    // 4. EVENT LISTENERS (DELETE FLOW)
    // =========================================================

    // Open Delete Confirmation
    document.querySelectorAll(".delete-address-link").forEach(link => {
        link.addEventListener("click", (e) => {
            e.preventDefault();

            // Get data from the clicked link
            const deleteUrl = link.getAttribute("href");
            const label = link.dataset.addressLabel;

            // Update modal content
            deleteLabel.textContent = label;
            deleteForm.action = deleteUrl;

            // Show modal
            deleteModal.classList.add("active");
        });
    });

    // Close Delete Modal
    closeDeleteBtn.addEventListener("click", closeDeleteModal);
    cancelDeleteBtn.addEventListener("click", closeDeleteModal);

    // Submit Delete Form
    deleteForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        const confirmBtn = deleteForm.querySelector("button[type='submit']");
        const originalText = confirmBtn.innerText;
        confirmBtn.disabled = true;
        confirmBtn.innerText = "Deleting...";

        const csrf = getCsrfToken();

        try {
            const response = await axios.post(deleteForm.action, {}, {
                headers: { "X-CSRFToken": csrf }
            });

            if (response.data.status === "success") {
                toastr.success("Address deleted successfully.");
                closeDeleteModal();
                setTimeout(() => window.location.reload(), 1000);
            } else {
                toastr.error(response.data.message || "Failed to delete address.");
                closeDeleteModal();
            }
        } catch (error) {
            toastr.error("An error occurred while deleting.");
        } finally {
            confirmBtn.innerText = originalText;
            confirmBtn.disabled = false;
        }
    });


    // =========================================================
    // 5. EVENT LISTENERS (EDIT FLOW)
    // =========================================================
    
    document.querySelectorAll(".edit-address-link").forEach(btn => {
        btn.addEventListener("click", async (e) => {
            e.preventDefault();
            clearErrors();

            const id = btn.dataset.addressId;
            addressIdInput.value = id;
            modalTitle.textContent = "Edit Address";

            openModal();

            // Construct fetch URL dynamically
            const fetchUrl = document
                .getElementById("fetchUrlBase")
                .getAttribute("data-url-base")
                .replace("0/", `${id}/`);

            try {
                const response = await axios.get(fetchUrl);

                if (response.data.status === "success") {
                    const a = response.data.address;

                    // Populate fields
                    fullNameInput.value = a.full_name;
                    line1Input.value = a.address_line_1;
                    line2Input.value = a.address_line_2;
                    cityInput.value = a.city;
                    stateInput.value = a.state;
                    postalCodeInput.value = a.postal_code;
                    phoneInput.value = a.phone_number;
                    countryInput.value = a.country;
                    isDefaultInput.checked = a.is_default;

                    // Handle Radio Buttons
                    if (a.address_type) {
                        const type = a.address_type.toLowerCase();
                        const radio = document.getElementById(`type_${type}`);
                        if (radio) radio.checked = true;
                    }

                } else {
                    toastr.error("Error fetching address details.");
                    closeModal();
                }
            } catch {
                toastr.error("Error fetching address details.");
                closeModal();
            }
        });
    });


    // =========================================================
    // 6. EVENT LISTENER (SAVE/UPDATE SUBMIT)
    // =========================================================

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        clearErrors();

        const formData = new FormData(form);

        // -- Simple Frontend Validation --
        if (!formData.get("address_type")) {
            const errorSpan = document.getElementById("error_address_type");
            if (errorSpan) errorSpan.innerHTML = "Please select an address type.";
            return;
        }

        const payload = {
            address_id: formData.get("address_id"),
            full_name: formData.get("full_name"),
            address_line_1: formData.get("address_line_1"),
            address_line_2: formData.get("address_line_2"),
            city: formData.get("city"),
            state: formData.get("state"),
            postal_code: formData.get("postal_code"),
            phone_number: formData.get("phone_number"),
            country: formData.get("country"),
            is_default: formData.get("is_default") === "on",
            address_type: formData.get("address_type"),
        };

        const csrf = getCsrfToken();

        saveBtn.disabled = true;
        const originalText = "Save Address"; // We know the default text
        saveBtn.innerText = "Saving...";

        try {
            const response = await axios.post(form.action, JSON.stringify(payload), {
                headers: {
                    "X-CSRFToken": csrf,
                    "Content-Type": "application/json",
                },
            });

            if (response.data.status === "success") {
                closeModal();
                toastr.success(response.data.message);
                setTimeout(() => window.location.reload(), 1000);
            }
            else if (response.data.errors) {
                // -- Logic: Button Text = "Error" --
                saveBtn.innerText = "Error"; 

                Object.entries(response.data.errors).forEach(([field, messages]) => {
                    const target = document.getElementById(`error_${field}`);
                    if (target) target.innerHTML = messages.join("<br>");
                });
            }
        } catch (error) {
            // -- Logic: Button Text = "Error" --
            saveBtn.innerText = "Error";

            const errors = error.response?.data?.errors;
            if (errors) {
                Object.entries(errors).forEach(([field, messages]) => {
                    const target = document.getElementById(`error_${field}`);
                    if (target) target.innerHTML = messages.join("<br>");
                });
            } else {
                toastr.error("Unexpected error occurred.");
            }
        } finally {
            saveBtn.disabled = false;

            // If the button says "Error", wait 2 seconds before resetting to "Save Address"
            if (saveBtn.innerText === "Error") {
                setTimeout(() => {
                    saveBtn.innerText = originalText;
                }, 2000);
            } else {
                // If successful (and page hasn't reloaded yet), revert immediately
                saveBtn.innerText = originalText;
            }
        }
    });

});