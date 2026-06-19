const API_URL = '';
let currentPage = 1;
let wakeLock = null;

async function acquireWakeLock() {
    if (!('wakeLock' in navigator)) return;
    try {
        wakeLock = await navigator.wakeLock.request('screen');
        wakeLock.addEventListener('release', () => { wakeLock = null; });
    } catch (_) {}
}

async function releaseWakeLock() {
    if (wakeLock) {
        await wakeLock.release();
        wakeLock = null;
    }
}

// Re-acquire wake lock when the tab becomes visible again (browser auto-releases on hide)
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' &&
        document.getElementById('cookingMode')?.classList.contains('active')) {
        acquireWakeLock();
    }
});
let currentSearch = '';
let currentIngredientFilter = '';
let currentCategoryFilter = '';
let currentCuisineFilter = '';
let currentKeywordFilter = '';
let editingRecipeId = null;
let isPrivate = false;
let LIMIT = 8;

document.addEventListener('DOMContentLoaded', async () => {
    initThemeToggle();
    setupEventListeners();
    LIMIT = parseInt(document.getElementById('perPageSelect').value) || 8;
    await detectAppMode();
    await Promise.all([loadRecipes(), loadCategories(), loadCuisines(), loadKeywords()]);
    updateGroceryBadge();
    const initialRecipeId = getRecipeIdFromHash();
    if (initialRecipeId) openCookingMode(initialRecipeId);
});

async function detectAppMode() {
    try {
        const res = await fetch(`${API_URL}/app-mode`);
        const { mode } = await res.json();
        if (mode === 'private') {
            isPrivate = true;
            document.querySelectorAll('.write-only').forEach(el => el.style.display = '');
        }
    } catch (e) {
        // stay in read-only mode
    }
}

function setupEventListeners() {
    document.getElementById('recipeForm').addEventListener('submit', handleCreateRecipe);
    document.getElementById('resetBtn').addEventListener('click', resetForm);
    document.getElementById('addIngredientBtn').addEventListener('click', addIngredientField);
    document.getElementById('importBtn').addEventListener('click', handleImportRecipe);
    document.getElementById('pasteBtn').addEventListener('click', handlePasteRecipe);
    document.getElementById('pasteFormatBtn').addEventListener('click', showFormatHelp);

    document.getElementById('searchInput').addEventListener('input', debounce(() => {
        currentPage = 1;
        currentSearch = document.getElementById('searchInput').value;
        loadRecipes();
    }, 300));

    document.getElementById('ingredientFilter').addEventListener('input', debounce(() => {
        currentPage = 1;
        currentIngredientFilter = document.getElementById('ingredientFilter').value;
        loadRecipes();
    }, 300));

    document.getElementById('prevBtn').addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            loadRecipes();
        }
    });

    document.getElementById('nextBtn').addEventListener('click', () => {
        currentPage++;
        loadRecipes();
    });

    document.getElementById('perPageSelect').addEventListener('change', (e) => {
        LIMIT = parseInt(e.target.value);
        currentPage = 1;
        loadRecipes();
    });

    document.getElementById('editForm').addEventListener('submit', handleUpdateRecipe);
    document.getElementById('editAddIngredientBtn').addEventListener('click', addEditIngredientField);

    setupIngredientRemovalListeners();
}

function setupIngredientRemovalListeners() {
    document.querySelectorAll('.btn-remove-ingredient').forEach(btn => {
        btn.addEventListener('click', function() {
            this.closest('.ingredient-item').remove();
        });
    });
}

function addIngredientField() {
    const container = document.getElementById('ingredientsContainer');
    const div = document.createElement('div');
    div.className = 'ingredient-item';
    div.innerHTML = `
        <input type="text" placeholder="e.g., 2 cups flour" class="ingredient-text">
        <button type="button" class="btn-danger btn-remove-ingredient">Remove</button>
    `;
    container.appendChild(div);
    div.querySelector('.btn-remove-ingredient').addEventListener('click', function() {
        this.closest('.ingredient-item').remove();
    });
}

function addEditIngredientField() {
    const container = document.getElementById('editIngredientsContainer');
    const div = document.createElement('div');
    div.className = 'ingredient-item';
    div.innerHTML = `
        <input type="text" placeholder="e.g., 2 cups flour" class="ingredient-text">
        <button type="button" class="btn-danger btn-remove-ingredient">Remove</button>
    `;
    container.appendChild(div);
    div.querySelector('.btn-remove-ingredient').addEventListener('click', function() {
        this.closest('.ingredient-item').remove();
    });
}

function getIngredientsFromForm(prefix = '') {
    const containerId = prefix ? `${prefix}IngredientsContainer` : 'ingredientsContainer';
    const container = document.getElementById(containerId);
    return Array.from(container.querySelectorAll('.ingredient-item'))
        .map(item => (item.querySelector('.ingredient-text').value || '').trim())
        .filter(Boolean);
}

function minutesToDuration(minutes) {
    if (!minutes || isNaN(minutes)) return undefined;
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    if (h && m) return `PT${h}H${m}M`;
    if (h) return `PT${h}H`;
    return `PT${m}M`;
}

function durationToMinutes(iso) {
    if (!iso) return null;
    const h = iso.match(/(\d+)H/);
    const m = iso.match(/(\d+)M/);
    return (h ? parseInt(h[1]) * 60 : 0) + (m ? parseInt(m[1]) : 0) || null;
}

async function handleCreateRecipe(e) {
    e.preventDefault();

    const prepMins = parseInt(document.getElementById('prepTime').value);
    const cookMins = parseInt(document.getElementById('cookTime').value);
    const servings = parseInt(document.getElementById('servings').value);

    const recipe = {
        name: document.getElementById('title').value,
        description: document.getElementById('description').value || undefined,
        recipeIngredient: getIngredientsFromForm(),
        recipeInstructions: document.getElementById('instructions').value,
        prepTime: minutesToDuration(prepMins),
        cookTime: minutesToDuration(cookMins),
        recipeYield: servings ? `${servings} servings` : undefined,
        recipeCategory: document.getElementById('category').value
            ? document.getElementById('category').value.split(',').map(s => s.trim()).filter(Boolean)
            : undefined,
        image: document.getElementById('imageUrl').value || undefined
    };

    try {
        const response = await fetch(`${API_URL}/recipes`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(recipe)
        });

        if (response.ok) {
            showAlert('Recipe created successfully!', 'success');
            resetForm();
            currentPage = 1;
            loadRecipes();
            loadCategories();
        } else {
            showAlert('Error creating recipe', 'error');
        }
    } catch (error) {
        showAlert('Error: ' + error.message, 'error');
    }
}

async function handleImportRecipe() {
    const url = document.getElementById('importUrl').value.trim();
    const statusDiv = document.getElementById('importStatus');

    if (!url) {
        statusDiv.innerHTML = '⚠️ Please enter a recipe URL';
        statusDiv.style.color = 'var(--warning)';
        return;
    }

    statusDiv.innerHTML = '⏳ Importing recipe...';
    statusDiv.style.color = 'var(--primary)';

    try {
        const response = await fetch(`${API_URL}/import`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: url })
        });

        if (response.ok) {
            const recipe = await response.json();
            statusDiv.innerHTML = `✅ Imported: "${recipe.name}"`;
            statusDiv.style.color = 'var(--success)';
            document.getElementById('importUrl').value = '';
            loadRecipes();
            loadCategories();
        } else {
            const error = await response.json();
            statusDiv.innerHTML = `❌ ${error.detail || 'Failed to import recipe'}`;
            statusDiv.style.color = 'var(--danger)';
        }
    } catch (error) {
        statusDiv.innerHTML = `❌ Error: ${error.message}`;
        statusDiv.style.color = 'var(--danger)';
    }
}

async function handlePasteRecipe() {
    const content = document.getElementById('pasteContent').value.trim();
    const statusDiv = document.getElementById('pasteStatus');

    if (!content) {
        statusDiv.innerHTML = '⚠️ Please paste a recipe';
        statusDiv.style.color = 'var(--warning)';
        return;
    }

    statusDiv.innerHTML = '⏳ Parsing recipe...';
    statusDiv.style.color = 'var(--primary)';

    try {
        const response = await fetch(`${API_URL}/paste`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: content })
        });

        if (response.ok) {
            const recipe = await response.json();
            statusDiv.innerHTML = `✅ Added: "${recipe.name}"`;
            statusDiv.style.color = 'var(--success)';
            document.getElementById('pasteContent').value = '';
            loadRecipes();
            loadCategories();
        } else {
            const error = await response.json();
            statusDiv.innerHTML = `❌ ${error.detail || 'Failed to parse recipe'}`;
            statusDiv.style.color = 'var(--danger)';
        }
    } catch (error) {
        statusDiv.innerHTML = `❌ Error: ${error.message}`;
        statusDiv.style.color = 'var(--danger)';
    }
}

function showFormatHelp() {
    const help = `
JSON Format Example (schema.org):
{
  "name": "Recipe Name",
  "description": "Brief description",
  "recipeIngredient": [
    "2 cups flour",
    "1 cup sugar",
    "2 eggs"
  ],
  "recipeInstructions": "Step 1.\\nStep 2.\\nStep 3.",
  "prepTime": "PT15M",
  "cookTime": "PT30M",
  "recipeCategory": ["Dessert"],
  "image": "https://..."
}

Markdown Format Example:
# Recipe Name
Recipe description

## Ingredients
- 2 cups flour
- 1 cup sugar

## Instructions
1. First step
2. Second step

## Metadata
Prep Time: 15
Cook Time: 30
Category: Dessert
Image URL: https://...
    `.trim();

    alert(help);
}

async function handleUpdateRecipe(e) {
    e.preventDefault();

    const prepMins = parseInt(document.getElementById('editPrepTime').value);
    const cookMins = parseInt(document.getElementById('editCookTime').value);
    const servings = parseInt(document.getElementById('editServings').value);

    const parseTagInput = id => {
        const val = document.getElementById(id).value.trim();
        return val ? val.split(',').map(t => t.trim()).filter(Boolean) : undefined;
    };

    const updates = {
        name: document.getElementById('editTitle').value,
        description: document.getElementById('editDescription').value || undefined,
        image: document.getElementById('editImageUrl').value || undefined,
        url: document.getElementById('editSourceUrl').value || undefined,
        recipeIngredient: getIngredientsFromForm('edit'),
        recipeInstructions: document.getElementById('editInstructions').value,
        prepTime: minutesToDuration(prepMins),
        cookTime: minutesToDuration(cookMins),
        recipeYield: servings ? `${servings} servings` : undefined,
        recipeCategory: parseTagInput('editCategory'),
        recipeCuisine: parseTagInput('editCuisine'),
        keywords: parseTagInput('editKeywords'),
    };

    try {
        const response = await fetch(`${API_URL}/recipes/${editingRecipeId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updates)
        });

        if (response.ok) {
            showAlert('Recipe updated successfully!', 'success');
            closeEditModal();
            loadRecipes();
        } else {
            showAlert('Error updating recipe', 'error');
        }
    } catch (error) {
        showAlert('Error: ' + error.message, 'error');
    }
}

async function loadCategories() {
    try {
        const response = await fetch(`${API_URL}/categories`);
        const categories = await response.json();
        renderCategoryChips(categories);
    } catch (_) {}
}

function _updateFilterSection() {
    const anyVisible = ['categoryRow', 'cuisineRow', 'keywordRow']
        .some(id => document.getElementById(id).style.display !== 'none');
    document.getElementById('filterSection').style.display = anyVisible ? '' : 'none';
}

function renderCategoryChips(categories) {
    const container = document.getElementById('categoryChips');
    const row = document.getElementById('categoryRow');
    if (!categories.length) {
        container.innerHTML = '';
        row.style.display = 'none';
        _updateFilterSection();
        return;
    }
    row.style.display = '';
    container.innerHTML = categories.map(cat => {
        const active = cat === currentCategoryFilter ? ' active' : '';
        return `<button class="category-chip${active}" onclick="selectCategory('${cat.replace(/'/g, "\\'")}')">${cat}</button>`;
    }).join('');
    _updateFilterSection();
}

function selectCategory(cat) {
    currentCategoryFilter = currentCategoryFilter === cat ? '' : cat;
    currentPage = 1;
    document.querySelectorAll('.category-chip').forEach(el => {
        el.classList.toggle('active', el.textContent === currentCategoryFilter);
    });
    loadRecipes();
}

async function loadCuisines() {
    try {
        const response = await fetch(`${API_URL}/cuisines`);
        const cuisines = await response.json();
        renderCuisineChips(cuisines);
    } catch (_) {}
}

function renderCuisineChips(cuisines) {
    const container = document.getElementById('cuisineChips');
    const row = document.getElementById('cuisineRow');
    if (!cuisines.length) {
        container.innerHTML = '';
        row.style.display = 'none';
        _updateFilterSection();
        return;
    }
    row.style.display = '';
    container.innerHTML = cuisines.map(c => {
        const active = c === currentCuisineFilter ? ' active' : '';
        return `<button class="category-chip${active}" onclick="selectCuisine('${c.replace(/'/g, "\\'")}')">${c}</button>`;
    }).join('');
    _updateFilterSection();
}

function selectCuisine(cuisine) {
    currentCuisineFilter = currentCuisineFilter === cuisine ? '' : cuisine;
    currentPage = 1;
    document.querySelectorAll('#cuisineChips .category-chip').forEach(el => {
        el.classList.toggle('active', el.textContent === currentCuisineFilter);
    });
    loadRecipes();
}

async function loadKeywords() {
    try {
        const response = await fetch(`${API_URL}/keywords`);
        const keywords = await response.json();
        renderKeywordChips(keywords);
    } catch (_) {}
}

function renderKeywordChips(keywords) {
    const container = document.getElementById('keywordChips');
    const row = document.getElementById('keywordRow');
    if (!keywords.length) {
        container.innerHTML = '';
        row.style.display = 'none';
        _updateFilterSection();
        return;
    }
    row.style.display = '';
    container.innerHTML = keywords.map(k => {
        const active = k === currentKeywordFilter ? ' active' : '';
        return `<button class="category-chip${active}" onclick="selectKeyword('${k.replace(/'/g, "\\'")}')">${k}</button>`;
    }).join('');
    _updateFilterSection();
}

function selectKeyword(keyword) {
    currentKeywordFilter = currentKeywordFilter === keyword ? '' : keyword;
    currentPage = 1;
    document.querySelectorAll('#keywordChips .category-chip').forEach(el => {
        el.classList.toggle('active', el.textContent === currentKeywordFilter);
    });
    loadRecipes();
}

async function loadRecipes() {
    try {
        let url = `${API_URL}/recipes?skip=${(currentPage - 1) * LIMIT}&limit=${LIMIT}`;
        if (currentSearch) url += `&search=${encodeURIComponent(currentSearch)}`;
        if (currentIngredientFilter) url += `&ingredient=${encodeURIComponent(currentIngredientFilter)}`;
        if (currentCategoryFilter) url += `&category=${encodeURIComponent(currentCategoryFilter)}`;
        if (currentCuisineFilter) url += `&cuisine=${encodeURIComponent(currentCuisineFilter)}`;
        if (currentKeywordFilter) url += `&keyword=${encodeURIComponent(currentKeywordFilter)}`;

        const response = await fetch(url);
        const data = await response.json();

        renderRecipes(data.recipes);
        updatePagination(data.total);
    } catch (error) {
        showAlert('Error loading recipes: ' + error.message, 'error');
    }
}

function renderRecipes(recipes) {
    const container = document.getElementById('recipesContainer');

    if (recipes.length === 0) {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🔍</div><p>No recipes found. Try different search criteria!</p></div>';
        return;
    }

    container.innerHTML = recipes.map(recipe => {
        const img = recipe.image
            ? `<img class="recipe-card-img" src="${recipe.image}" alt="${recipe.name}">`
            : `<div class="recipe-card-img-placeholder">🍽️</div>`;

        const metaParts = [];
        if (recipe.prepTime) metaParts.push(`⏱️ ${formatDuration(recipe.prepTime)} prep`);
        if (recipe.cookTime) metaParts.push(`🔥 ${formatDuration(recipe.cookTime)} cook`);
        if (recipe.recipeYield) metaParts.push(`🍽️ ${recipe.recipeYield}`);

        return `
        <div class="recipe-card" onclick="openCookingMode(${recipe.id})">
            ${img}
            <div class="recipe-card-body">
                <div class="recipe-card-title">${recipe.name}</div>
                ${metaParts.length ? `<div class="recipe-card-meta">${metaParts.join(' · ')}</div>` : ''}
                ${isPrivate ? `<div class="recipe-card-actions" onclick="event.stopPropagation()">
                    <button class="btn-secondary" onclick="openEditModal(${recipe.id})">Edit</button>
                    <button class="btn-danger" onclick="deleteRecipe(${recipe.id})">Delete</button>
                </div>` : ''}
            </div>
        </div>`;
    }).join('');
}

function updatePagination(total) {
    const totalPages = Math.ceil(total / LIMIT);
    const pagination = document.getElementById('pagination');

    if (total <= LIMIT) {
        pagination.style.display = 'none';
        return;
    }

    pagination.style.display = 'flex';
    document.getElementById('currentPage').textContent = currentPage;
    document.getElementById('totalPages').textContent = totalPages;
    document.getElementById('prevBtn').disabled = currentPage === 1;
    document.getElementById('nextBtn').disabled = currentPage === totalPages;
}

async function openEditModal(recipeId) {
    try {
        const response = await fetch(`${API_URL}/recipes/${recipeId}`);
        const recipe = await response.json();

        editingRecipeId = recipe.id;

        document.getElementById('editTitle').value = recipe.name;
        document.getElementById('editDescription').value = recipe.description || '';
        document.getElementById('editImageUrl').value = recipe.image || '';
        document.getElementById('editSourceUrl').value = recipe.url || '';
        document.getElementById('editInstructions').value = recipe.recipeInstructions;
        document.getElementById('editPrepTime').value = durationToMinutes(recipe.prepTime) || '';
        document.getElementById('editCookTime').value = durationToMinutes(recipe.cookTime) || '';
        document.getElementById('editServings').value = recipe.recipeYield ? parseInt(recipe.recipeYield) : '';
        document.getElementById('editCategory').value = (recipe.recipeCategory || []).join(', ');
        document.getElementById('editCuisine').value = (recipe.recipeCuisine || []).join(', ');
        document.getElementById('editKeywords').value = (recipe.keywords || []).join(', ');

        const container = document.getElementById('editIngredientsContainer');
        container.innerHTML = '';
        (recipe.recipeIngredient || []).forEach(ing => {
            const div = document.createElement('div');
            div.className = 'ingredient-item';
            div.innerHTML = `
                <input type="text" placeholder="e.g., 2 cups flour" class="ingredient-text" value="${ing}">
                <button type="button" class="btn-danger btn-remove-ingredient">Remove</button>
            `;
            container.appendChild(div);
            div.querySelector('.btn-remove-ingredient').addEventListener('click', function() {
                this.closest('.ingredient-item').remove();
            });
        });

        document.getElementById('editModal').classList.add('active');
    } catch (error) {
        showAlert('Error loading recipe: ' + error.message, 'error');
    }
}

function closeEditModal() {
    document.getElementById('editModal').classList.remove('active');
    editingRecipeId = null;
}

async function deleteRecipe(recipeId) {
    if (!confirm('Are you sure you want to delete this recipe?')) return;

    try {
        const response = await fetch(`${API_URL}/recipes/${recipeId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            showAlert('Recipe deleted successfully!', 'success');
            loadRecipes();
            loadCategories();
        } else {
            showAlert('Error deleting recipe', 'error');
        }
    } catch (error) {
        showAlert('Error: ' + error.message, 'error');
    }
}

function resetForm() {
    document.getElementById('recipeForm').reset();
    const container = document.getElementById('ingredientsContainer');
    container.innerHTML = `
        <div class="ingredient-item">
            <input type="text" placeholder="e.g., 2 cups flour" class="ingredient-text" required>
            <button type="button" class="btn-danger btn-remove-ingredient">Remove</button>
        </div>
    `;
    setupIngredientRemovalListeners();
}

function showAlert(message, type) {
    const alert = document.getElementById('alert');
    alert.textContent = message;
    alert.className = `alert ${type}`;
    alert.style.display = 'block';
    setTimeout(() => {
        alert.style.display = 'none';
    }, 4000);
}

function debounce(func, wait) {
    let timeout;
    return function() {
        clearTimeout(timeout);
        timeout = setTimeout(func, wait);
    };
}

function formatDuration(iso) {
    if (!iso) return null;
    const h = iso.match(/(\d+)H/);
    const m = iso.match(/(\d+)M/);
    const hours = h ? parseInt(h[1]) : 0;
    const mins = m ? parseInt(m[1]) : 0;
    const total = hours * 60 + mins;
    if (total < 60) return `${total}m`;
    return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
}

function getRecipeIdFromHash() {
    const m = location.hash.match(/^#recipe\/(\d+)$/);
    return m ? parseInt(m[1]) : null;
}

window.addEventListener('popstate', () => {
    const recipeId = getRecipeIdFromHash();
    if (recipeId) {
        openCookingMode(recipeId);
    } else {
        document.getElementById('cookingMode').classList.remove('active');
        document.body.style.overflow = 'auto';
        stopAllTimers();
        timerCounter = 0;
    }
});

// Cooking Mode Functions

let _cookingRecipe = null;
let _originalServings = null;
let _currentServings = null;

function _parseLeadingNumber(str) {
    let m = str.match(/^(\d+)\s+(\d+)\/(\d+)/);
    if (m) return { value: parseInt(m[1]) + parseInt(m[2]) / parseInt(m[3]), length: m[0].length };
    m = str.match(/^(\d+)\/(\d+)/);
    if (m) return { value: parseInt(m[1]) / parseInt(m[2]), length: m[0].length };
    m = str.match(/^(\d+\.?\d*)/);
    if (m) return { value: parseFloat(m[1]), length: m[0].length };
    return null;
}

function _formatNum(n) {
    if (n <= 0) return '0';
    const whole = Math.floor(n);
    const frac = n - whole;
    const fracs = [[1,8],[1,4],[1,3],[3,8],[1,2],[5,8],[2,3],[3,4],[7,8]];
    for (const [a, b] of fracs) {
        if (Math.abs(frac - a / b) < 0.06) {
            if (frac < 0.01) return String(whole);
            return whole > 0 ? `${whole} ${a}/${b}` : `${a}/${b}`;
        }
    }
    if (frac < 0.01) return String(whole);
    return n.toFixed(1).replace(/\.0$/, '');
}

function _scaleIngredient(ingStr, factor) {
    if (!ingStr || factor === 1) return ingStr;
    // Handle "X to Y ..." ranges
    const rangeM = ingStr.match(/^([\d\s\/½⅓¼⅔¾⅛⅜⅝⅞]+)\s+to\s+([\d\s\/½⅓¼⅔¾⅛⅜⅝⅞]+)(.*)/);
    if (rangeM) {
        const n1 = _parseLeadingNumber(rangeM[1].trim());
        const n2 = _parseLeadingNumber(rangeM[2].trim());
        if (n1 && n2) return `${_formatNum(n1.value * factor)} to ${_formatNum(n2.value * factor)}${rangeM[3]}`;
    }
    const parsed = _parseLeadingNumber(ingStr);
    if (!parsed) return ingStr;
    return _formatNum(parsed.value * factor) + ingStr.slice(parsed.length);
}

function _boldQuantity(ingStr) {
    const m = ingStr.match(
        /^([\d\s\-–\/½⅓¼⅔¾⅛⅜⅝⅞]+(?:cups?|tablespoons?|teaspoons?|tbsp|tsp|ounces?|oz|grams?|g|mg|kilograms?|kg|liters?|milliliters?|ml|l|pounds?|lbs?|pints?|gallons?|pinch(?:es)?|dashes?|cloves?|cans?|jars?|slices?|bunches?|stalks?|heads?|bulbs?|large|medium|small|whole|handfuls?)?)\s+(.+)/i
    );
    if (m && /[\d½⅓¼⅔¾⅛⅜⅝⅞]/.test(m[1])) {
        return `<strong>${m[1].trim()}</strong> ${m[2]}`;
    }
    return ingStr;
}

function _renderIngredients(recipe, factor) {
    const list = document.getElementById('cookingIngredientsList');
    list.innerHTML = (recipe.recipeIngredient || []).map((ing, idx) => {
        const scaled = _scaleIngredient(ing, factor);
        return `
            <div class="cooking-ingredient-item" data-ingredient-id="${idx}">
                <input type="checkbox" id="ing-${idx}" class="ingredient-checkbox">
                <label for="ing-${idx}"><span>${_boldQuantity(scaled)}</span></label>
                <button class="ing-add-to-list-btn" data-ing="${scaled.replace(/"/g, '&quot;')}" title="Add to grocery list">+</button>
            </div>`;
    }).join('');
    list.querySelectorAll('input').forEach(cb => {
        cb.addEventListener('change', function() {
            this.closest('.cooking-ingredient-item').classList.toggle('checked');
        });
    });
    list.querySelectorAll('.ing-add-to-list-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            addIngredientToGroceryList(this.dataset.ing, _cookingRecipe ? _cookingRecipe.name : '');
            this.textContent = '✓';
            this.disabled = true;
            setTimeout(() => { this.textContent = '+'; this.disabled = false; }, 1200);
        });
    });
}

function adjustServings(delta) {
    _currentServings = Math.max(1, _currentServings + delta);
    document.getElementById('cookingServings').textContent = _currentServings;
    _renderIngredients(_cookingRecipe, _currentServings / _originalServings);
}

async function openCookingMode(recipeId) {
    try {
        const response = await fetch(`${API_URL}/recipes/${recipeId}`);
        const recipe = await response.json();

        document.getElementById('cookingTitle').textContent = recipe.name;
        if (recipe.image) {
            document.getElementById('cookingImage').src = recipe.image;
            document.getElementById('cookingImage').style.display = 'block';
        } else {
            document.getElementById('cookingImage').style.display = 'none';
        }

        const descEl = document.getElementById('cookingDescription');
        descEl.textContent = recipe.description || '';
        descEl.style.display = recipe.description ? '' : 'none';

        const tagsEl = document.getElementById('cookingTags');
        const tags = [
            ...(recipe.recipeCategory || []).map(t => `<span class="recipe-tag recipe-tag--category">${t}</span>`),
            ...(recipe.recipeCuisine || []).map(t => `<span class="recipe-tag recipe-tag--cuisine">${t}</span>`),
            ...(recipe.keywords || []).map(t => `<span class="recipe-tag">${t}</span>`),
        ];
        tagsEl.innerHTML = tags.join('');
        tagsEl.style.display = tags.length ? '' : 'none';

        _cookingRecipe = recipe;
        _originalServings = recipe.recipeYield ? parseInt(recipe.recipeYield) : null;
        _currentServings = _originalServings;

        document.getElementById('cookingPrepTime').textContent = recipe.prepTime ? formatDuration(recipe.prepTime) : '—';
        document.getElementById('cookingCookTime').textContent = recipe.cookTime ? formatDuration(recipe.cookTime) : '—';

        const servingsItem = document.getElementById('cookingServingsItem');
        const cookingMeta = document.querySelector('.cooking-meta');
        if (_originalServings) {
            document.getElementById('cookingServings').textContent = _originalServings;
            servingsItem.style.display = '';
            cookingMeta.classList.remove('two-items');
        } else {
            servingsItem.style.display = 'none';
            cookingMeta.classList.add('two-items');
        }

        _renderIngredients(recipe, 1);

        const instructionsList = document.getElementById('cookingInstructionsList');
        instructionsList.innerHTML = recipe.recipeInstructions
            .split('\n')
            .filter(line => line.trim())
            .map((instruction, idx) => {
                const timeRegex = /(\d+)(?:\s*[-–]\s*(\d+))?\s*(?:minute|min|hour|hr|second|sec)/i;
                const timeMatch = instruction.match(timeRegex);
                let timerMinutes = null;

                if (timeMatch) {
                    let timeValue = parseInt(timeMatch[1]);
                    if (timeMatch[0].toLowerCase().includes('hour') || timeMatch[0].toLowerCase().includes('hr')) {
                        timeValue = timeValue * 60;
                    }
                    timerMinutes = timeValue;
                }

                const hasTimer = timerMinutes !== null;
                const timerHTML = hasTimer ? `<div class="cooking-instruction-timer">
                            <button class="timer-button" data-seconds="${timerMinutes * 60}">⏱️ Start ${Math.floor(timerMinutes / 60) > 0 ? Math.floor(timerMinutes / 60) + 'h ' : ''}${timerMinutes % 60 || timerMinutes}m timer</button>
                        </div>` : '';

                return `
                    <div class="cooking-instruction-step" data-step-id="${idx}">
                        <div class="cooking-instruction-step-number">${idx + 1}</div>
                        <div class="cooking-instruction-text">${instruction.trim()}</div>
                        ${timerHTML}
                    </div>
                `;
            }).join('');

        document.querySelectorAll('.cooking-instruction-step').forEach(step => {
            step.addEventListener('click', function(e) {
                if (!e.target.closest('.timer-button')) {
                    this.classList.toggle('completed');
                }
            });
        });

        document.querySelectorAll('.timer-button').forEach(button => {
            button.addEventListener('click', function(e) {
                e.stopPropagation();
                const seconds = parseInt(this.getAttribute('data-seconds'));
                if (seconds) startTimer(seconds);
            });
        });

        document.getElementById('cookingMode').classList.add('active');
        document.body.style.overflow = 'auto';
        history.pushState({ recipeId: recipe.id }, '', `#recipe/${recipe.id}`);
        acquireWakeLock();
    } catch (error) {
        showAlert('Error loading recipe: ' + error.message, 'error');
    }
}

function closeCookingMode() {
    document.getElementById('cookingMode').classList.remove('active');
    document.body.style.overflow = 'auto';
    stopAllTimers();
    timerCounter = 0;
    history.replaceState(null, '', location.pathname + location.search);
    releaseWakeLock();
}

// Timer Functions
let timers = new Map();
let timerCounter = 0;

function startTimer(seconds) {
    const timerId = timerCounter++;
    const endTime = Date.now() + seconds * 1000;

    const timerDisplay = document.createElement('div');
    timerDisplay.className = 'timer-display';

    if (window.innerWidth < 768) {
        timerDisplay.style.bottom = `${20 + (timerId * 100)}px`;
        timerDisplay.style.top = 'auto';
    } else {
        timerDisplay.style.top = `${20 + (timerId * 140)}px`;
        timerDisplay.style.bottom = 'auto';
    }

    timerDisplay.innerHTML = `
        <button class="timer-display-close" onclick="stopTimer(${timerId})">✕</button>
        <div class="timer-display-label">Timer ${timerId + 1}</div>
        <div id="timerText-${timerId}" class="timer-display-text">${formatTime(seconds)}</div>
    `;
    document.body.appendChild(timerDisplay);

    const timerInterval = setInterval(() => {
        const remainingSeconds = Math.max(0, Math.round((endTime - Date.now()) / 1000));

        const timerText = document.getElementById(`timerText-${timerId}`);
        if (timerText) timerText.textContent = formatTime(remainingSeconds);

        if (remainingSeconds <= 0) {
            clearInterval(timerInterval);
            timers.delete(timerId);

            if (timerDisplay) {
                timerDisplay.classList.add('completed');
                playTimerSound();
                showAlert(`Timer ${timerId + 1} finished! ⏱️`, 'success');
                setTimeout(() => timerDisplay.remove(), 5000);
            }
        }
    }, 1000);

    timers.set(timerId, { interval: timerInterval, display: timerDisplay, endTime });
}

document.addEventListener('visibilitychange', () => {
    if (document.visibilityState !== 'visible') return;
    for (const [timerId, timer] of timers) {
        const remainingSeconds = Math.max(0, Math.round((timer.endTime - Date.now()) / 1000));
        const timerText = document.getElementById(`timerText-${timerId}`);
        if (timerText) timerText.textContent = formatTime(remainingSeconds);
        if (remainingSeconds <= 0) {
            clearInterval(timer.interval);
            timers.delete(timerId);
            timer.display.classList.add('completed');
            playTimerSound();
            showAlert(`Timer ${timerId + 1} finished! ⏱️`, 'success');
            setTimeout(() => timer.display.remove(), 5000);
        }
    }
});

function stopTimer(timerId) {
    const timer = timers.get(timerId);
    if (timer) {
        clearInterval(timer.interval);
        timer.display.remove();
        timers.delete(timerId);
    }
}

function stopAllTimers() {
    for (const [, timer] of timers) {
        clearInterval(timer.interval);
        timer.display.remove();
    }
    timers.clear();
}

function formatTime(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;

    if (hours > 0) {
        return `${hours}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    }
    return `${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

function playTimerSound() {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();

    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);

    oscillator.frequency.value = 800;
    oscillator.type = 'sine';

    gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);

    oscillator.start(audioContext.currentTime);
    oscillator.stop(audioContext.currentTime + 0.5);
}

// Dark Mode Toggle
function initThemeToggle() {
    const toggle = document.getElementById('themeToggle');
    const body = document.body;

    const savedTheme = localStorage.getItem('theme') || 'dark';
    body.className = `${savedTheme}-mode`;
    updateThemeToggle(savedTheme);

    toggle.addEventListener('click', () => {
        const currentTheme = body.className.includes('dark') ? 'dark' : 'light';
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

        body.className = `${newTheme}-mode`;
        localStorage.setItem('theme', newTheme);
        updateThemeToggle(newTheme);
    });
}

function updateThemeToggle(theme) {
    const toggle = document.getElementById('themeToggle');
    toggle.textContent = theme === 'dark' ? '☀️' : '🌙';
}

// Page Navigation
function showPage(pageName) {
    document.querySelectorAll('.page').forEach(page => page.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));

    const pageElement = document.getElementById(pageName + 'Page');
    if (pageElement) pageElement.classList.add('active');

    event.target.classList.add('active');

    if (pageName === 'home') loadRecipes();
    if (pageName === 'grocery') {
        renderGroceryList();
        _syncStoreSelect();
        const inp = document.getElementById('groceryCustomInput');
        if (inp && !inp._bound) {
            inp.addEventListener('keydown', e => { if (e.key === 'Enter') addCustomGroceryItem(); });
            inp._bound = true;
        }
    }

    window.scrollTo(0, 0);
}

// ============================================================================
// Grocery List
// ============================================================================

const GROCERY_STORES = [
    { id: 'freshdirect', name: 'FreshDirect', searchUrl: q => `https://www.freshdirect.com/search?search=${encodeURIComponent(q).replace(/%20/g, '+')}` },
    { id: 'heb',         name: 'HEB',         searchUrl: q => `https://www.heb.com/search?esc=true&q=${encodeURIComponent(q)}` },
];

function _getSelectedStore() {
    const id = localStorage.getItem('groceryStore') || GROCERY_STORES[0].id;
    return GROCERY_STORES.find(s => s.id === id) || GROCERY_STORES[0];
}

function _saveSelectedStore(id) {
    localStorage.setItem('groceryStore', id);
}

function _ingredientSearchText(text) {
    const stripped = text
        .replace(/^[\d½¼¾⅓⅔⅛⅜⅝⅞\s\/\-\.]+(?:cups?|tbsps?|tablespoons?|tsps?|teaspoons?|oz|ounces?|lbs?|pounds?|grams?|kg|ml|l|pints?|quarts?|gallons?|cloves?|bunche?s?|cans?|packages?|pkg|slices?|pieces?|heads?)?\b\s*/i, '')
        .replace(/,\s*.*$/, '')
        .trim();
    return stripped || text.trim();
}

function shopItemOnStore(itemId) {
    const item = _loadGroceryList().find(i => i.id === itemId);
    if (!item) return;
    const store = _getSelectedStore();
    window.open(store.searchUrl(_ingredientSearchText(item.text)), '_blank');
}

function selectGroceryStore(id) {
    _saveSelectedStore(id);
    _syncStoreSelect();
    const panel = document.getElementById('shopLinksPanel');
    if (panel && panel.children.length > 0) renderShopLinks();
}

function _syncStoreSelect() {
    const id = _getSelectedStore().id;
    document.querySelectorAll('.grocery-store-tab').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.store === id);
    });
}

function shopAllOnStore() {
    renderShopLinks();
}

function renderShopLinks() {
    const panel = document.getElementById('shopLinksPanel');
    if (!panel) return;
    const unchecked = _loadGroceryList().filter(i => !i.checked);
    const store = _getSelectedStore();
    if (unchecked.length === 0) {
        panel.innerHTML = '<p class="shop-links-empty">No unchecked items to shop for.</p>';
        return;
    }
    panel.innerHTML = unchecked.map(item => {
        const url = store.searchUrl(_ingredientSearchText(item.text));
        const display = _scaleIngredient(item.text, item.count || 1);
        return `<a class="shop-link-item" href="${url}" target="_blank" rel="noopener noreferrer">
            <span class="shop-link-name">${display}</span>
            <span class="shop-link-arrow">${store.name} →</span>
        </a>`;
    }).join('');
}

function _loadGroceryList() {
    try {
        return JSON.parse(localStorage.getItem('groceryList') || '[]');
    } catch {
        return [];
    }
}

function _saveGroceryList(list) {
    localStorage.setItem('groceryList', JSON.stringify(list));
    updateGroceryBadge();
}

function updateGroceryBadge() {
    const list = _loadGroceryList();
    const unchecked = list.filter(i => !i.checked).length;
    const badge = document.getElementById('groceryBadge');
    if (!badge) return;
    if (unchecked > 0) {
        badge.textContent = unchecked;
        badge.style.display = '';
    } else {
        badge.style.display = 'none';
    }
}

function addIngredientToGroceryList(text, recipeName) {
    const list = _loadGroceryList();
    list.push({ id: Date.now() + Math.random(), text, recipeName, checked: false, count: 1 });
    _saveGroceryList(list);
}

function changeGroceryItemCount(id, delta) {
    const list = _loadGroceryList();
    const item = list.find(i => i.id === id);
    if (item) item.count = Math.max(1, (item.count || 1) + delta);
    _saveGroceryList(list);
    renderGroceryList();
}

function addCustomGroceryItem() {
    const input = document.getElementById('groceryCustomInput');
    const text = input.value.trim();
    if (!text) return;
    addIngredientToGroceryList(text, 'Additional');
    input.value = '';
    renderGroceryList();
}

function toggleIngredientsCollapse() {
    const btn = document.getElementById('ingredientsCollapseBtn');
    const list = document.getElementById('cookingIngredientsList');
    const expanded = btn.getAttribute('aria-expanded') === 'true';
    btn.setAttribute('aria-expanded', String(!expanded));
    list.classList.toggle('collapsed', expanded);
}

function addAllToGroceryList() {
    if (!_cookingRecipe) return;
    const factor = (_originalServings && _currentServings) ? _currentServings / _originalServings : 1;
    const recipeName = _cookingRecipe.name;
    (_cookingRecipe.recipeIngredient || []).forEach(ing => {
        addIngredientToGroceryList(_scaleIngredient(ing, factor), recipeName);
    });
    const btn = document.getElementById('addAllToGroceryBtn');
    if (btn) {
        btn.textContent = 'Added!';
        btn.disabled = true;
        setTimeout(() => { btn.textContent = '+ Add all to list'; btn.disabled = false; }, 1500);
    }
}

function toggleGroceryItem(id) {
    const list = _loadGroceryList();
    const item = list.find(i => i.id === id);
    if (item) item.checked = !item.checked;
    _saveGroceryList(list);
    renderGroceryList();
}

function removeGroceryItem(id) {
    const list = _loadGroceryList().filter(i => i.id !== id);
    _saveGroceryList(list);
    renderGroceryList();
}

function clearCheckedGroceryItems() {
    const list = _loadGroceryList().filter(i => !i.checked);
    _saveGroceryList(list);
    renderGroceryList();
}

function clearGroceryList() {
    if (!confirm('Clear all grocery list items?')) return;
    _saveGroceryList([]);
    renderGroceryList();
}

function renderGroceryList() {
    const container = document.getElementById('groceryListContainer');
    if (!container) return;
    const list = _loadGroceryList();

    if (list.length === 0) {
        container.innerHTML = `<div class="empty-state">
            <div class="empty-state-icon">🛒</div>
            <p>No items yet. Open a recipe and add ingredients to your list.</p>
        </div>`;
        return;
    }

    // Group by recipe name
    const groups = {};
    list.forEach(item => {
        const key = item.recipeName || 'Other';
        if (!groups[key]) groups[key] = [];
        groups[key].push(item);
    });

    container.innerHTML = Object.entries(groups).map(([recipeName, items]) => `
        <div class="grocery-group">
            <div class="grocery-group-name">${recipeName}</div>
            ${items.map(item => `
                <div class="grocery-item${item.checked ? ' checked' : ''}" data-id="${item.id}">
                    <input type="checkbox" class="grocery-checkbox" ${item.checked ? 'checked' : ''}
                        onchange="toggleGroceryItem(${item.id})">
                    <span class="grocery-item-text">${_scaleIngredient(item.text, item.count || 1)}</span>
                    <div class="grocery-count-stepper">
                        <button class="grocery-count-btn" onclick="changeGroceryItemCount(${item.id}, -1)">−</button>
                        <span class="grocery-count-value">${item.count || 1}</span>
                        <button class="grocery-count-btn" onclick="changeGroceryItemCount(${item.id}, 1)">+</button>
                    </div>
                    <button class="grocery-shop-btn" onclick="shopItemOnStore(${item.id})" title="Find on store">🔍</button>
                    <button class="grocery-remove-btn" onclick="removeGroceryItem(${item.id})" title="Remove">✕</button>
                </div>
            `).join('')}
        </div>
    `).join('');
}
