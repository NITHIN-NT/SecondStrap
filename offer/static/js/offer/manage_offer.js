document.addEventListener('DOMContentLoaded', function() {
    
    /* ================================
       1. STATE MANAGEMENT
    ================================ */
    const selectedProducts = new Map();
    const selectedCategories = new Map();

    // Populate Maps if editing (Data comes from Django template)
    if (typeof initialProducts !== 'undefined' && Array.isArray(initialProducts)) {
        initialProducts.forEach(p => selectedProducts.set(p.id.toString(), { name: p.name, image: p.image }));
    }
    if (typeof initialCategories !== 'undefined' && Array.isArray(initialCategories)) {
        initialCategories.forEach(c => selectedCategories.set(c.id.toString(), { name: c.name, image: c.image }));
    }

    /* ================================
       2. RENDER FUNCTIONS
    ================================ */
    // Helper to render the selected items chips
    function renderSelected(store, listElementId) {
        const listElement = document.getElementById(listElementId);
        if (!listElement) return;

        listElement.innerHTML = "";
        
        store.forEach((item, id) => {
            const li = document.createElement("li");
            li.className = "selected-item";
            li.innerHTML = `
                ${item.image ? `<img src="${item.image}" width="30" height="30" style="border-radius:4px; object-fit:cover;">` : ''}
                <span>${item.name}</span>
                <button type="button" class="remove-chip" data-id="${id}">✕</button>
            `;

            // Remove handler
            li.querySelector(".remove-chip").addEventListener("click", function() {
                store.delete(id);
                renderSelected(store, listElementId);
            });
            
            listElement.appendChild(li);
        });
    }

    /* ================================
       3. SEARCH SETUP (AXIOS)
    ================================ */
    function setupSearch(inputId, resultId, listId, searchUrl, store) {
        const input = document.getElementById(inputId);
        const results = document.getElementById(resultId);
        
        if (!input || !results) return; // Safety check

        // Initial render
        renderSelected(store, listId);

        let cancelSource = null;

        input.addEventListener("input", async () => {
            const query = input.value.trim();
            
            if (query.length < 2) { 
                results.innerHTML = "";
                return;
            }

            // Cancel previous request if typing continues
            if (cancelSource) cancelSource.cancel();
            cancelSource = axios.CancelToken.source();

            try {
                const response = await axios.get(searchUrl, {
                    params: { search: query },
                    cancelToken: cancelSource.token
                });

                results.innerHTML = "";
                
                if (response.data.length === 0) {
                    results.innerHTML = "<li style='padding:8px; color:#666;'>No results found</li>";
                    return;
                }

                response.data.forEach(item => {
                    const li = document.createElement("li");
                    li.style.cssText = "display:flex; align-items:center; padding:8px; cursor:pointer; border-bottom:1px solid #eee;";
                    li.innerHTML = `
                        ${item.image ? `<img src="${item.image}" width="32" height="32" style="border-radius:4px; margin-right:10px; object-fit:cover;">` : ''}
                        <span>${item.name}</span>
                    `;

                    li.addEventListener("click", () => {
                        store.set(item.id.toString(), { name: item.name, image: item.image });
                        renderSelected(store, listId);
                        input.value = "";
                        results.innerHTML = "";
                    });
                    
                    // Hover effect
                    li.onmouseover = () => li.style.backgroundColor = "#f3f4f6";
                    li.onmouseout = () => li.style.backgroundColor = "transparent";

                    results.appendChild(li);
                });
            } catch (error) {
                if (!axios.isCancel(error)) console.error("Search error:", error);
            }
        });

        // Close results if clicking outside
        document.addEventListener('click', function(e) {
            if (!input.contains(e.target) && !results.contains(e.target)) {
                results.innerHTML = "";
            }
        });
    }

    // Initialize Searches
    setupSearch("productSearch", "productResults", "selectedProducts", window.PRODUCT_SEARCH_URL, selectedProducts);
    setupSearch("categorySearch", "categoryResults", "selectedCategories", window.CATEGORY_SEARCH_URL, selectedCategories);


    /* ================================
       4. OFFER TYPE TOGGLE LOGIC
    ================================ */
    const offerType = document.getElementById("offerType");
    const productSection = document.getElementById("productSection");
    const categorySection = document.getElementById("categorySection");
    // amountSection might not exist in HTML yet, so we check existence
    const amountSection = document.getElementById("amountSection"); 

    function toggleOfferSections() {
        // Safe Hiding: Check if element exists before accessing style
        if (productSection) productSection.style.display = "none";
        if (categorySection) categorySection.style.display = "none";
        if (amountSection) amountSection.style.display = "none";

        if (!offerType) return;

        const val = offerType.value;

        if (val === "product" && productSection) {
            productSection.style.display = "block";
        } else if (val === "category" && categorySection) {
            categorySection.style.display = "block";
        } else if (val === "amount" && amountSection) {
            amountSection.style.display = "block";
        }
    }

    if (offerType) {
        offerType.addEventListener("change", toggleOfferSections);
        // Run on load to set initial state
        toggleOfferSections(); 
    }

    /* ================================
       5. FORM SUBMISSION
    ================================ */
    // Attached to window so the inline onsubmit="attachSelected()" can find it
    window.attachSelected = function() {
        const prodInput = document.getElementById("productsInput");
        const catInput = document.getElementById("categoriesInput");

        if (prodInput) {
            prodInput.value = Array.from(selectedProducts.keys()).join(",");
        }
        if (catInput) {
            catInput.value = Array.from(selectedCategories.keys()).join(",");
        }
        
        return true; // Return true to allow form submission
    };

});