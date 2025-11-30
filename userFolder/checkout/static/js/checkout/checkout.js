document.addEventListener("DOMContentLoaded", () => {

    // ==========================================
    // 1. AXIOS CONFIGURATION
    // ==========================================
    // Automatically attach CSRF token to every request
    axios.defaults.xsrfCookieName = 'csrftoken';
    axios.defaults.xsrfHeaderName = 'X-CSRFToken';

    // ==========================================
    // 2. SELECTION LOGIC (Visual Styles)
    // ==========================================
    // This handles the blue border/radio selection when clicking cards
    const selectionCards = document.querySelectorAll('.selection-card');

    selectionCards.forEach(card => {
        card.addEventListener('click', function (e) {
            // Ignore if clicking "Edit" button or "Add New" button
            if (e.target.closest('.edit-btn')) return;
            if (e.target.closest('#addNewAddressBtn') || this.classList.contains('add-new-trigger')) return;

            const radio = this.querySelector('input[type="radio"]');
            if (radio) {
                const groupName = radio.name;

                // Unselect others in the same group
                document.querySelectorAll(`input[name="${groupName}"]`).forEach(input => {
                    const parentCard = input.closest('.selection-card');
                    if (parentCard) parentCard.classList.remove('selected');
                });

                // Select this one
                radio.checked = true;
                this.classList.add('selected');
            }
        });

        // Also allow clicking the actual radio button to update styles
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

    // --- Elements ---
    const modal = document.getElementById("addressModal");
    const form = document.getElementById("addressForm");
    const modalTitle = document.getElementById("addressModalTitle");

    // Buttons
    const openAddBtn = document.getElementById("addNewAddressBtn");
    const closeBtn = document.getElementById("closeAddressModalBtn");
    const cancelBtn = document.getElementById("cancelAddressBtn");
    const saveBtn = document.getElementById("saveAddressBtn");

    // Inputs
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

    // URL Base
    const fetchUrlBaseElem = document.getElementById("fetchUrlBase");
    const fetchUrlBase = fetchUrlBaseElem ? fetchUrlBaseElem.getAttribute("data-url-base") : null;

    // --- Helper Functions ---

    const toggleModal = (show = true) => {
        if (!modal) return;
        if (show) {
            modal.classList.add("active");
            modal.setAttribute('aria-hidden', 'false');
        } else {
            modal.classList.remove("active");
            modal.setAttribute('aria-hidden', 'true');
        }
    };

    const resetForm = () => {
        if (!form) return;
        form.reset();

        // Clear hidden ID (Critical: sets "Add" mode)
        if (addressIdInput) addressIdInput.value = "";

        // Reset Title
        if (modalTitle) modalTitle.textContent = "Add New Address";

        // Clear Radio Buttons manually
        document.querySelectorAll('input[name="address_type"]').forEach(r => r.checked = false);
    };

    // --- Logic: Add New Address ---
    if (openAddBtn) {
        openAddBtn.addEventListener("click", (e) => {
            e.preventDefault();
            resetForm();
            toggleModal(true);
        });

        // Keyboard accessibility
        openAddBtn.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                openAddBtn.click();
            }
        });
    }

    // --- Logic: Edit Address (Fetch via Axios) ---
    document.querySelectorAll(".edit-address-trigger").forEach((btn) => {
        btn.addEventListener("click", async (e) => {
            e.preventDefault();

            const addressId = btn.getAttribute("data-id");
            if (!addressId) return;

            // 1. Prepare UI
            resetForm();
            if (modalTitle) modalTitle.textContent = "Edit Address";
            if (addressIdInput) addressIdInput.value = addressId; // Sets "Edit" mode

            // 2. Construct URL
            let fetchUrl = fetchUrlBase
                ? fetchUrlBase.replace("__ADDR_ID__", addressId).replace("0", addressId)
                : `/addresses/manage/${addressId}/`;

            // 3. Fetch Data
            try {
                const response = await axios.get(fetchUrl);

                if (response.data.status === "success") {
                    const addr = response.data.address;

                    // Populate Fields
                    if (fullNameInput) fullNameInput.value = addr.full_name;
                    if (line1Input) line1Input.value = addr.address_line_1;
                    if (line2Input) line2Input.value = addr.address_line_2;
                    if (cityInput) cityInput.value = addr.city;
                    if (stateInput) stateInput.value = addr.state;
                    if (postalCodeInput) postalCodeInput.value = addr.postal_code;
                    if (phoneInput) phoneInput.value = addr.phone_number;
                    if (countryInput) countryInput.value = addr.country;
                    if (isDefaultInput) isDefaultInput.checked = addr.is_default;

                    // Populate Radio Buttons
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

    // --- Logic: Save Address (Submit via Axios) ---
    if (form) {
        form.addEventListener("submit", async (e) => {
            e.preventDefault();

            // UI Feedback
            const originalBtnText = saveBtn ? saveBtn.innerText : "Save";
            if (saveBtn) {
                saveBtn.innerText = "Saving...";
                saveBtn.disabled = true;
            }

            try {
                const formData = new FormData(form);

                // Construct JSON Payload
                const payload = {
                    address_id: formData.get("address_id") || null,
                    full_name: formData.get("full_name"),
                    address_line_1: formData.get("address_line_1"),
                    address_line_2: formData.get("address_line_2"),
                    city: formData.get("city"),
                    state: formData.get("state"),
                    postal_code: formData.get("postal_code"),
                    phone_number: formData.get("phone_number"),
                    country: formData.get("country"),
                    address_type: formData.get("address_type"),
                    is_default: isDefaultInput ? isDefaultInput.checked : false
                };

                const url = form.getAttribute("action");

                // Send POST Request
                const response = await axios.post(url, payload);

                if (response.data.status === "success") {
                    toggleModal(false);
                    toastr.success(response.data.message);

                    // Reload to show changes
                    setTimeout(() => window.location.reload(), 500);
                } else {
                    toastr.error(response.data.message || "Error saving address.");
                }

            } catch (error) {
                console.error("Save Error:", error);

                // Handle Django Validation Errors
                if (error.response && error.response.data && error.response.data.errors) {
                    const errors = error.response.data.errors;
                    Object.keys(errors).forEach(key => {
                        toastr.error(`${key}: ${errors[key]}`);
                    });
                } else {
                    toastr.error(error.response?.data?.message || "An error occurred.");
                }
            } finally {
                // Reset UI
                if (saveBtn) {
                    saveBtn.innerText = originalBtnText;
                    saveBtn.disabled = false;
                }
            }
        });
    }

    // --- Logic: Close Modal ---
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