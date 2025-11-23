document.addEventListener("DOMContentLoaded", () => {
    // --- 1. Element References ---
    const modal = document.getElementById("addressModal");
    const openBtn = document.getElementById("addNewAddress");
    const closeBtn = document.getElementById("closeAddressModalBtn");
    const cancelBtn = document.getElementById("cancelAddressBtn");
    const saveBtn = document.getElementById("saveAddressBtn");
    const form = document.getElementById("addressForm");
    const modalTitle = document.getElementById("addressModalTitle");
    const addressIdInput = document.getElementById("address_id");

    // Input references for prefilling
    const fullNameInput = document.getElementById("full_name");
    const line1Input = document.getElementById("address_line_1");
    const line2Input = document.getElementById("address_line_2");
    const cityInput = document.getElementById("city");
    const stateInput = document.getElementById("state");
    const postalCodeInput = document.getElementById("postal_code");
    const phoneInput = document.getElementById("phone_number");
    const countryInput = document.getElementById("country");
    const isDefaultInput = document.getElementById("is_default");

    // Delete Address Conformation modal references
    const deleteLinks = document.querySelectorAll('.delete-address-link');
    const deleteModal = document.getElementById('deleteConfirmModal');
    const deleteForm = document.getElementById('deleteAddressForm');
    const deleteLabel = document.getElementById('deleteAddressLabel');
    const cancelDeleteBtn = document.getElementById('cancelDeleteBtn');
    const closeDeleteModalBtn = document.getElementById('closeDeleteModalBtn');

    if (!deleteModal) return; 

    // MODIFICATION START: Using 'active' class for consistency
    function openDeleteModal(url, labelText) {
        if (deleteForm) {
            deleteForm.action = url;          // set POST action
        }
        if (deleteLabel) {
            deleteLabel.textContent = labelText || '';
        }

        // Use 'active' class to show modal
        deleteModal.classList.add('active'); 
    }

    function closeDeleteModal() {
        // Use 'active' class to hide modal
        deleteModal.classList.remove('active'); 
    }
    // MODIFICATION END

    deleteLinks.forEach(link => {
        link.addEventListener('click', function (e) {
            e.preventDefault();

            const url = this.getAttribute('href');
            const labelText = this.dataset.addressLabel || '';

            if (!url) return;
            openDeleteModal(url, labelText);
        });
    });

    if (cancelDeleteBtn) {
        cancelDeleteBtn.addEventListener('click', function () {
            closeDeleteModal();
        });
    }

    if (closeDeleteModalBtn) {
        closeDeleteModalBtn.addEventListener('click', function () {
            closeDeleteModal();
        });
    }

    // Close when clicking outside the modal content
    deleteModal.addEventListener('click', function (e) {
        if (e.target === deleteModal) {
            closeDeleteModal();
        }
    });

    // --- 2. Modal Functions ---
    const openModal = (e) => {
        if (e) e.preventDefault();
        // Uses 'active' class to show modal
        if (modal) modal.classList.add("active"); 
    };

    const closeModal = () => {
        // Uses 'active' class to hide modal
        if (modal) modal.classList.remove("active");
        if (form) {
            form.reset();
            addressIdInput.value = ""; // Clear hidden ID
            modalTitle.textContent = "Add New Address";
        }
    };

    // Function to get the CSRF token from the meta tag or form input
    function getCsrfToken() {
        const csrfTokenEl = document.querySelector("[name=csrfmiddlewaretoken]");
        return csrfTokenEl ? csrfTokenEl.value : "";
    }

    // --- 3. Base Event Listeners ---
    if (openBtn) openBtn.addEventListener("click", () => {
        // Reset and then open for "Add New"
        closeModal();
        openModal();
    });
    if (closeBtn) closeBtn.addEventListener("click", closeModal);
    if (cancelBtn) cancelBtn.addEventListener("click", closeModal);

    // Close modal on outside click
    window.addEventListener("click", (e) => {
        if (e.target === modal) closeModal();
    });

    const fetchUrlBaseElement = document.getElementById("fetchUrlBase");
    const fetchUrlBase = fetchUrlBaseElement
        ? fetchUrlBaseElement.getAttribute("data-url-base")
        : null;

    // --- 4. Edit/Prefill Logic using Axios GET ---
    document.querySelectorAll(".edit-address-link").forEach((btn) => {
        btn.addEventListener("click", async (e) => {
            e.preventDefault();

            const addressId = btn.getAttribute("data-address-id");

            if (!addressId) {
                console.error("Address ID not found for editing.");
                toastr.error("Address ID not found for editing.");
                return;
            }

            // IMPORTANT CHANGE: reset BEFORE setting addressId so reset doesn't clear it
            if (form) {
                form.reset(); // Clear the form while loading data
            }

            modalTitle.textContent = "Edit Address";
            addressIdInput.value = addressId; // Set the hidden ID for the POST request
            openModal();

            let fetchUrl;
            if (fetchUrlBase) {
                fetchUrl = fetchUrlBase.replace("0/", `${addressId}/`);
            } else {
                fetchUrl = `addresses/fetch/${addressId}/`; // fallback with trailing slash
            }

            try {
                // Axios GET Request to fetch address details
                const response = await axios.get(fetchUrl);

                if (response.data.status === "success") {
                    const address = response.data.address;

                    // Prefill Form Fields
                    fullNameInput.value = address.full_name || '';
                    line1Input.value = address.address_line_1 || '';
                    line2Input.value = address.address_line_2 || '';
                    cityInput.value = address.city || '';
                    stateInput.value = address.state || '';
                    postalCodeInput.value = address.postal_code || '';
                    phoneInput.value = address.phone_number || '';
                    countryInput.value = address.country || '';
                    isDefaultInput.checked = address.is_default || false;

                    // Prefill Radio Buttons (HOME, WORK, OTHER)
                    const addressType = address.address_type ? address.address_type.toLowerCase() : '';
                    const addressTypeInput = document.getElementById(`type_${addressType}`);
                    if (addressTypeInput) {
                        addressTypeInput.checked = true;
                    }

                } else {
                    toastr.error(response.data.message || "Could not fetch address data.");
                    closeModal();
                }
            } catch (error) {
                console.error("Axios GET Error: ", error.response?.data || error.message);
                toastr.error("Error fetching address details.");
                closeModal();
            }
        });
    });

    // If somehow there's no form, skip submit logic
    if (!form) return;

    // --- 5. Form Submission (Add/Update) using Axios POST ---
    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const url = form.action; // Assumes form.action points to the POST endpoint
        const formData = new FormData(form);

        // 1. Construct Payload
        const payload = {
            full_name: formData.get("full_name"),
            address_line_1: formData.get("address_line_1"),
            address_line_2: formData.get("address_line_2"),
            city: formData.get("city"),
            state: formData.get("state"),
            postal_code: formData.get("postal_code"),
            phone_number: formData.get("phone_number"),
            country: formData.get("country"),
            // Checkbox value needs careful handling: if not checked, it won't be in FormData
            is_default: formData.get("is_default") === "on", 
            address_type: formData.get("address_type"),
            address_id: formData.get("address_id") || null,
        };

        // 2. Get CSRF Token
        const csrfToken = getCsrfToken();

        // 3. Update Save Button UI
        const originalBtnText = saveBtn ? saveBtn.innerText : "";
        if (saveBtn) {
            saveBtn.innerText = "Saving...";
            saveBtn.disabled = true;
        }

        try {
            // 4. Send Axios Request
            const response = await axios.post(url, JSON.stringify(payload), {
                headers: {
                    "X-CSRFToken": csrfToken,
                    "Content-Type": "application/json",
                },
            });

            if (response.data.status === "success") {
                closeModal();
                toastr.success(response.data.message);

                // Auto refresh page after successful add/update
                setTimeout(() => {
                    window.location.reload();
                }, 500);
            } else {
                // If there are specific field errors from Django/server
                if (response.data.errors) {
                    let errorMessage = response.data.message || "Please check the form for errors.";
                    // Optionally display specific error messages here using toastr
                    toastr.error(errorMessage);
                } else {
                    toastr.error(response.data.message || "Error Saving Address");
                }
            }
        } catch (error) {
            console.error("Axios Error : ", error.response?.data || error.message);
            toastr.error("Error Saving Address. Check console for details.");
        } finally {
            // 5. Reset Save Button UI
            if (saveBtn) {
                saveBtn.innerText = originalBtnText;
                saveBtn.disabled = false;
            }
        }
    });
});