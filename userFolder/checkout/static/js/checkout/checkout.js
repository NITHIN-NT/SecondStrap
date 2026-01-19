document.addEventListener("DOMContentLoaded", () => {

    // ==========================================
    // 1. AXIOS CONFIGURATION
    // ==========================================
    axios.defaults.xsrfCookieName = 'csrftoken';
    axios.defaults.xsrfHeaderName = 'X-CSRFToken';

    // ==========================================
    // 2. SELECTION LOGIC (Visual Styles)
    // ==========================================
    const selectionCards = document.querySelectorAll('.selection-card');

    selectionCards.forEach(card => {
        card.addEventListener('click', function (e) {
            if (e.target.closest('.edit-btn')) return;
            if (e.target.closest('#addNewAddressBtn') || this.classList.contains('add-new-trigger')) return;

            const radio = this.querySelector('input[type="radio"]');
            if (radio) {
                const groupName = radio.name;

                document.querySelectorAll(`input[name="${groupName}"]`).forEach(input => {
                    const parentCard = input.closest('.selection-card');
                    if (parentCard) parentCard.classList.remove('selected');
                });

                radio.checked = true;
                this.classList.add('selected');
            }
        });

        const innerRadio = card.querySelector('input[type="radio"]');
        if (innerRadio) {
            innerRadio.addEventListener('change', function () {
                if (!this.checked) return;
                const groupName = this.name;
                document.querySelectorAll(`input[name="${groupName}"]`).forEach(input => {
                    const parentCard = input.closest('.selection-card');
                    if (parentCard) parentCard.classList.remove('selected');
                });
                const parent = this.closest('.selection-card');
                if (parent) parent.classList.add('selected');
            });
        }
    });

    // ==========================================
    // 3. ADDRESS MODAL & FORM LOGIC (Axios)
    // ==========================================

    const modal = document.getElementById("addressModal");
    const form = document.getElementById("addressForm");
    const modalTitle = document.getElementById("addressModalTitle");

    const openAddBtn = document.getElementById("addNewAddressBtn");
    const closeBtn = document.getElementById("closeAddressModalBtn");
    const cancelBtn = document.getElementById("cancelAddressBtn");
    const saveBtn = document.getElementById("saveAddressBtn");

    const addressIdInput = document.getElementById("address_id");
    const fullNameInput = document.getElementById("full_name");
    const line1Input = document.getElementById("address_line_1");
    const line2Input = document.getElementById("address_line_2");
    const cityInput = document.getElementById("city");
    const stateInput = document.getElementById("state");
    const postalCodeInput = document.getElementById("postal_code");
    const phoneInput = document.getElementById("phone_number");
    const countryInput = document.getElementById("country");
    const isDefaultInput = document.getElementById("is_default");

    const fetchUrlBaseElem = document.getElementById("fetchUrlBase");
    const fetchUrlBase = fetchUrlBaseElem ? fetchUrlBaseElem.getAttribute("data-url-base") : null;

    const toggleModal = (show = true) => {
        if (!modal) return;
        if (show) {
            modal.classList.add("active");
            modal.setAttribute('aria-hidden', 'false');
            document.body.classList.add("modal-open");
        } else {
            modal.classList.remove("active");
            modal.setAttribute('aria-hidden', 'true');
            document.body.classList.remove("modal-open");
        }
    };

    const resetForm = () => {
        if (!form) return;
        form.reset();
        if (addressIdInput) addressIdInput.value = "";
        if (modalTitle) modalTitle.textContent = "Add New Address";
        document.querySelectorAll('input[name="address_type"]').forEach(r => r.checked = false);
    };

    if (openAddBtn) {
        openAddBtn.addEventListener("click", (e) => {
            e.preventDefault();
            resetForm();
            toggleModal(true);
        });

        openAddBtn.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                openAddBtn.click();
            }
        });
    }

    document.querySelectorAll(".edit-address-trigger").forEach((btn) => {
        btn.addEventListener("click", async (e) => {
            e.preventDefault();

            const addressId = btn.getAttribute("data-id");
            if (!addressId) return;

            resetForm();
            if (modalTitle) modalTitle.textContent = "Edit Address";
            if (addressIdInput) addressIdInput.value = addressId;

            let fetchUrl = fetchUrlBase
                ? fetchUrlBase.replace("__ADDR_ID__", addressId).replace("0", addressId)
                : `/addresses/manage/${addressId}/`;

            try {
                const response = await axios.get(fetchUrl);

                if (response.data.status === "success") {
                    const addr = response.data.address;

                    if (fullNameInput) fullNameInput.value = addr.full_name;
                    if (line1Input) line1Input.value = addr.address_line_1;
                    if (line2Input) line2Input.value = addr.address_line_2;
                    if (cityInput) cityInput.value = addr.city;
                    if (stateInput) stateInput.value = addr.state;
                    if (postalCodeInput) postalCodeInput.value = addr.postal_code;
                    if (phoneInput) phoneInput.value = addr.phone_number;
                    if (countryInput) countryInput.value = addr.country;
                    if (isDefaultInput) isDefaultInput.checked = addr.is_default;

                    if (addr.address_type) {
                        const radio = document.querySelector(`input[name="address_type"][value="${addr.address_type}"]`);
                        if (radio) radio.checked = true;
                    }

                    toggleModal(true);
                } else {
                    toastr.error("Could not load address details.");
                }
            } catch (error) {
                console.error("Fetch Error:", error);
                toastr.error("Error fetching address details.");
            }
        });
    });

    if (form) {
        form.addEventListener("submit", async (e) => {
            e.preventDefault();

            // 1. Clear previous error messages
            document.querySelectorAll('.error-msg').forEach(el => el.textContent = '');

            // 2. Manage Button State
            const originalBtnText = saveBtn ? saveBtn.innerText : "Save";
            if (saveBtn) {
                saveBtn.innerText = "Saving...";
                saveBtn.disabled = true;
            }

            try {
                const formData = new FormData(form);

                // Construct payload manually to ensure types (bools/nulls) are correct
                const payload = {
                    address_id: formData.get("address_id") || null,
                    address_type: formData.get("address_type") || 'OTHER',
                    full_name: formData.get("full_name"),
                    address_line_1: formData.get("address_line_1"),
                    address_line_2: formData.get("address_line_2") || null,
                    city: formData.get("city"),
                    state: formData.get("state"),
                    postal_code: formData.get("postal_code"),
                    phone_number: formData.get("phone_number"),
                    country: formData.get("country"),
                    is_default: isDefaultInput ? isDefaultInput.checked : false
                };

                const url = form.getAttribute("action");

                // 3. Send Request
                const response = await axios.post(url, payload);

                // 4. Handle Success
                if (response.data.status === "success") {
                    toggleModal(false);
                    toastr.success(response.data.message || "Address saved successfully!");

                    // Small delay to allow the toastr to be seen before reload
                    setTimeout(() => window.location.reload(), 500);
                } else {
                    // Handle logical error passed with success status 200 but logical failure
                    toastr.error(response.data.message || "Error saving address.");
                }

            } catch (error) {
                console.error("Save Error:", error);

                // 5. Handle Validation Errors from Server
                if (error.response && error.response.data && error.response.data.errors) {
                    const errors = error.response.data.errors;

                    // Loop through errors and display them in the HTML spans
                    Object.keys(errors).forEach(key => {
                        // Look for id="error_field_name" (e.g., error_full_name)
                        const errorSpan = document.getElementById(`error_${key}`);

                        if (errorSpan) {
                            errorSpan.textContent = Array.isArray(errors[key]) ? errors[key][0] : errors[key];
                        }
                    });
                } else {
                    // Generic fallback for server crash or network error
                    toastr.error(error.response?.data?.message || "An unexpected error occurred.");
                }
            } finally {
                // 6. Reset Button
                if (saveBtn) {
                    saveBtn.innerText = originalBtnText;
                    saveBtn.disabled = false;
                }
            }
        });
    }

    if (closeBtn) closeBtn.addEventListener("click", () => toggleModal(false));
    if (cancelBtn) cancelBtn.addEventListener("click", () => toggleModal(false));

    window.addEventListener("click", (e) => {
        if (e.target === modal) toggleModal(false);
    });

    window.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
            if (modal && modal.classList.contains('active')) toggleModal(false);
        }
    });

});