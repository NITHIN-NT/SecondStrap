/* ================================
   STATE
================================ */
const selectedProducts = new Map();
const selectedCategories = new Map();

/* ================================
   SEARCH SETUP (AXIOS)
================================ */
function setupSearch(inputId, resultId, selectedId, searchUrl, store) {
    const input = document.getElementById(inputId);
    const results = document.getElementById(resultId);
    const selected = document.getElementById(selectedId);

    let cancelSource = null;

    input.addEventListener("input", async () => {
        const query = input.value.trim();

        if (query.length < 2) { 
            results.innerHTML = "";
            return;
        }

        if (cancelSource) {
            cancelSource.cancel();
        }
        cancelSource = axios.CancelToken.source();

        try {
            const response = await axios.get(searchUrl, {
                params: { search: query },
                cancelToken: cancelSource.token
            });

            results.innerHTML = "";

            response.data.forEach(item => {
                const li = document.createElement("li");
                li.innerHTML = `
                    <img src="${item.image}" width="32" height="32" style="border-radius:6px;margin-right:8px;">
                    <span>${item.name}</span>
                `;
                li.style.display = "flex";
                li.style.alignItems = "center";

                li.onclick = () => {
                    if (!store.has(item.id)) {
                        store.set(item.id, {
                            name: item.name,
                            image: item.image
                        });
                        renderSelected();
                    }
                    input.value = "";
                    results.innerHTML = "";
                };

                results.appendChild(li);
            });

        } catch (error) {
            if (!axios.isCancel(error)) {
                console.error("Search error:", error);
            }
        }
    });

    function renderSelected() {
        selected.innerHTML = "";
        store.forEach((item, id) => {
            const li = document.createElement("li");
            li.className = "selected-item";
            li.innerHTML = `
                <img src="${item.image}" width="36" height="36" style="border-radius:8px;">
                <span>${item.name}</span>
                <button type="button">❌</button>
            `;

            li.querySelector("button").onclick = () => {
                store.delete(id);
                renderSelected();
            };

            selected.appendChild(li);
        });
    }
}

/* ================================
   INIT SEARCHES
================================ */
setupSearch(
    "productSearch",
    "productResults",
    "selectedProducts",
    window.PRODUCT_SEARCH_URL,
    selectedProducts
);

setupSearch(
    "categorySearch",
    "categoryResults",
    "selectedCategories",
    window.CATEGORY_SEARCH_URL,
    selectedCategories
);

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
    if (offerType.value === "category") categorySection.style.display = "block";
    if (offerType.value === "amount_threshold") amountSection.style.display = "block";
}

offerType.addEventListener("change", toggleOfferSections);
toggleOfferSections();

/* ================================
   FORM SUBMIT HANDLER
================================ */
function attachSelected() {
    document.getElementById("productsInput").value =
        Array.from(selectedProducts.keys()).join(",");

    document.getElementById("categoriesInput").value =
        Array.from(selectedCategories.keys()).join(",");
}
