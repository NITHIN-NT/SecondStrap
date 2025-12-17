/* ================================
   STATE
================================ */
const selectedProducts = new Map();
const selectedCategories = new Map();

// Populate Maps if editing
if (typeof initialProducts !== 'undefined') {
    initialProducts.forEach(p => selectedProducts.set(p.id.toString(), { name: p.name, image: p.image }));
}
if (typeof initialCategories !== 'undefined') {
    initialCategories.forEach(c => selectedCategories.set(c.id.toString(), { name: c.name, image: c.image }));
}

/* ================================
   SEARCH SETUP (AXIOS)
================================ */
function setupSearch(inputId, resultId, selectedId, searchUrl, store) {
    const input = document.getElementById(inputId);
    const results = document.getElementById(resultId);
    const selected = document.getElementById(selectedId);

    let cancelSource = null;

    // Separate render function to call during init and after changes
    const renderSelected = () => {
        selected.innerHTML = "";
        store.forEach((item, id) => {
            const li = document.createElement("li");
            li.className = "selected-item";
            li.innerHTML = `
                ${item.image ? `<img src="${item.image}" width="36" height="36" style="border-radius:8px;">` : ''}
                <span>${item.name}</span>
                <button type="button" class="remove-chip">❌</button>
            `;

            li.querySelector("button").onclick = () => {
                store.delete(id);
                renderSelected();
            };
            selected.appendChild(li);
        });
    };

    // Initial render for Edit mode
    renderSelected();

    input.addEventListener("input", async () => {
        const query = input.value.trim();
        if (query.length < 2) { 
            results.innerHTML = "";
            return;
        }

        if (cancelSource) cancelSource.cancel();
        cancelSource = axios.CancelToken.source();

        try {
            const response = await axios.get(searchUrl, {
                params: { search: query },
                cancelToken: cancelSource.token
            });

            results.innerHTML = "";
            response.data.forEach(item => {
                const li = document.createElement("li");
                li.style.display = "flex";
                li.style.alignItems = "center";
                li.style.padding = "8px";
                li.style.cursor = "pointer";
                li.innerHTML = `
                    <img src="${item.image}" width="32" height="32" style="border-radius:6px;margin-right:8px;">
                    <span>${item.name}</span>
                `;

                li.onclick = () => {
                    store.set(item.id.toString(), { name: item.name, image: item.image });
                    renderSelected();
                    input.value = "";
                    results.innerHTML = "";
                };
                results.appendChild(li);
            });
        } catch (error) {
            if (!axios.isCancel(error)) console.error("Search error:", error);
        }
    });
}

/* ================================
   INIT SEARCHES
================================ */
setupSearch("productSearch", "productResults", "selectedProducts", window.PRODUCT_SEARCH_URL, selectedProducts);
setupSearch("categorySearch", "categoryResults", "selectedCategories", window.CATEGORY_SEARCH_URL, selectedCategories);

/* ================================
   OFFER TYPE TOGGLE
================================ */
const offerType = document.getElementById("offerType");
const productSection = document.getElementById("productSection");
const categorySection = document.getElementById("categorySection");
const amountSection = document.getElementById("amountSection");

function toggleOfferSections() {
    productSection.style.display = "none";
    categorySection.style.display = "none";
    amountSection.style.display = "none";

    if (offerType.value === "product") productSection.style.display = "block";
    else if (offerType.value === "category") categorySection.style.display = "block";
    else if (offerType.value === "amount_threshold") amountSection.style.display = "block";
}

offerType.addEventListener("change", toggleOfferSections);
toggleOfferSections(); // Call on load

/* ================================
   FORM SUBMIT HANDLER
================================ */
function attachSelected() {
    document.getElementById("productsInput").value = Array.from(selectedProducts.keys()).join(",");
    document.getElementById("categoriesInput").value = Array.from(selectedCategories.keys()).join(",");
}