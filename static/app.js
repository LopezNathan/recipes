const API_URL = '';
let currentPage = 1;
let currentSearch = '';
let currentIngredientFilter = '';
let editingRecipeId = null;
let isPrivate = false;
const LIMIT = 5;

document.addEventListener('DOMContentLoaded', async () => {
    initThemeToggle();
    setupEventListeners();
    await detectAppMode();
    loadRecipes();
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
        <input type="text" placeholder="Ingredient name" class="ingredient-name">
        <input type="text" placeholder="Quantity (e.g., 400g)" class="ingredient-quantity">
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
        <input type="text" placeholder="Ingredient name" class="ingredient-name">
        <input type="text" placeholder="Quantity (e.g., 400g)" class="ingredient-quantity">
        <button type="button" class="btn-danger btn-remove-ingredient">Remove</button>
    `;
    container.appendChild(div);
    div.querySelector('.btn-remove-ingredient').addEventListener('click', function() {
        this.closest('.ingredient-item').remove();
    });
}

function getIngredientsFromForm(prefix = '') {
    const container = prefix ? document.getElementById(`${prefix}IngredientsContainer`) : document.getElementById('ingredientsContainer');
    const items = container.querySelectorAll('.ingredient-item');
    return Array.from(items).map(item => {
        const name = item.querySelector('.ingredient-name').value;
        const quantity = item.querySelector('.ingredient-quantity').value;
        if (!name) return null;
        return quantity ? { name, quantity } : name;
    }).filter(Boolean);
}

async function handleCreateRecipe(e) {
    e.preventDefault();

    const recipe = {
        title: document.getElementById('title').value,
        description: document.getElementById('description').value || undefined,
        ingredients: getIngredientsFromForm(),
        instructions: document.getElementById('instructions').value,
        prep_time: parseInt(document.getElementById('prepTime').value) || undefined,
        cook_time: parseInt(document.getElementById('cookTime').value) || undefined,
        image_url: document.getElementById('imageUrl').value || undefined
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
            statusDiv.innerHTML = `✅ Imported: "${recipe.title}"`;
            statusDiv.style.color = 'var(--success)';
            document.getElementById('importUrl').value = '';
            loadRecipes();
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
            statusDiv.innerHTML = `✅ Added: "${recipe.title}"`;
            statusDiv.style.color = 'var(--success)';
            document.getElementById('pasteContent').value = '';
            loadRecipes();
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
JSON Format Example:
{
  "title": "Recipe Name",
  "description": "Brief description",
  "ingredients": [
    {"name": "flour", "quantity": "2 cups"},
    {"name": "sugar", "quantity": "1 cup"}
  ],
  "instructions": "Step 1.\\nStep 2.\\nStep 3.",
  "prep_time": 15,
  "cook_time": 30,
  "category": "Dessert",
  "image_url": "https://..."
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

    const updates = {
        title: document.getElementById('editTitle').value,
        description: document.getElementById('editDescription').value || undefined,
        image_url: document.getElementById('editImageUrl').value || undefined,
        source_url: document.getElementById('editSourceUrl').value || undefined,
        ingredients: getIngredientsFromForm('edit'),
        instructions: document.getElementById('editInstructions').value,
        prep_time: parseInt(document.getElementById('editPrepTime').value) || undefined,
        cook_time: parseInt(document.getElementById('editCookTime').value) || undefined
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

async function loadRecipes() {
    try {
        let url = `${API_URL}/recipes?skip=${(currentPage - 1) * LIMIT}&limit=${LIMIT}`;
        if (currentSearch) url += `&search=${encodeURIComponent(currentSearch)}`;
        if (currentIngredientFilter) url += `&ingredient=${encodeURIComponent(currentIngredientFilter)}`;

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
        const img = recipe.image_url
            ? `<img class="recipe-card-img" src="${recipe.image_url}" alt="${recipe.title}">`
            : `<div class="recipe-card-img-placeholder">🍽️</div>`;

        const metaParts = [];
        if (recipe.prep_time) metaParts.push(`⏱️ ${recipe.prep_time}m prep`);
        if (recipe.cook_time) metaParts.push(`🔥 ${recipe.cook_time}m cook`);

        return `
        <div class="recipe-card" onclick="openCookingMode(${recipe.id})">
            ${img}
            <div class="recipe-card-body">
                <div class="recipe-card-title">${recipe.title}</div>
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

        document.getElementById('editTitle').value = recipe.title;
        document.getElementById('editDescription').value = recipe.description || '';
        document.getElementById('editImageUrl').value = recipe.image_url || '';
        document.getElementById('editSourceUrl').value = recipe.source_url || '';
        document.getElementById('editInstructions').value = recipe.instructions;
        document.getElementById('editPrepTime').value = recipe.prep_time || '';
        document.getElementById('editCookTime').value = recipe.cook_time || '';

        const container = document.getElementById('editIngredientsContainer');
        container.innerHTML = '';
        recipe.ingredients.forEach(ing => {
            const div = document.createElement('div');
            div.className = 'ingredient-item';
            const name = typeof ing === 'string' ? ing : ing.name;
            const quantity = typeof ing === 'string' ? '' : (ing.quantity || '');
            div.innerHTML = `
                <input type="text" placeholder="Ingredient name" class="ingredient-name" value="${name}">
                <input type="text" placeholder="Quantity" class="ingredient-quantity" value="${quantity}">
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
            <input type="text" placeholder="Ingredient name" class="ingredient-name" required>
            <input type="text" placeholder="Quantity (e.g., 400g)" class="ingredient-quantity">
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

// Cooking Mode Functions
async function openCookingMode(recipeId) {
    try {
        const response = await fetch(`${API_URL}/recipes/${recipeId}`);
        const recipe = await response.json();

        // Set title and image
        document.getElementById('cookingTitle').textContent = recipe.title;
        if (recipe.image_url) {
            document.getElementById('cookingImage').src = recipe.image_url;
            document.getElementById('cookingImage').style.display = 'block';
        } else {
            document.getElementById('cookingImage').style.display = 'none';
        }

        // Set times
        document.getElementById('cookingPrepTime').textContent = recipe.prep_time ? `${recipe.prep_time}m` : '—';
        document.getElementById('cookingCookTime').textContent = recipe.cook_time ? `${recipe.cook_time}m` : '—';

        // Build ingredients list with checkboxes
        const ingredientsList = document.getElementById('cookingIngredientsList');
        ingredientsList.innerHTML = recipe.ingredients.map((ing, idx) => {
            const name = typeof ing === 'string' ? ing : ing.name;
            const qty = typeof ing === 'string' ? '' : (ing.quantity ? ` • ${ing.quantity}` : '');
            return `
                <div class="cooking-ingredient-item" data-ingredient-id="${idx}">
                    <input type="checkbox" id="ing-${idx}" class="ingredient-checkbox">
                    <label for="ing-${idx}">
                        <span>${name}${qty}</span>
                    </label>
                </div>
            `;
        }).join('');

        // Add event listeners to ingredients
        document.querySelectorAll('.cooking-ingredient-item input').forEach(checkbox => {
            checkbox.addEventListener('change', function() {
                this.closest('.cooking-ingredient-item').classList.toggle('checked');
            });
        });

        // Build instructions list
        const instructionsList = document.getElementById('cookingInstructionsList');
        instructionsList.innerHTML = recipe.instructions
            .split('\n')
            .filter(line => line.trim())
            .map((instruction, idx) => {
                // Extract time in minutes from instruction (e.g., "5 minutes", "30-45 minutes", "2-3 hours")
                const timeRegex = /(\d+)(?:\s*[-–]\s*(\d+))?\s*(?:minute|min|hour|hr|second|sec)/i;
                const timeMatch = instruction.match(timeRegex);
                let timerMinutes = null;

                if (timeMatch) {
                    let timeValue = parseInt(timeMatch[1]);
                    // If it's in hours, convert to minutes
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

        // Add event listeners to instructions
        document.querySelectorAll('.cooking-instruction-step').forEach(step => {
            step.addEventListener('click', function(e) {
                // Don't toggle completed if clicking on timer button
                if (!e.target.closest('.timer-button')) {
                    this.classList.toggle('completed');
                }
            });
        });

        // Add event listeners to timer buttons
        document.querySelectorAll('.timer-button').forEach(button => {
            button.addEventListener('click', function(e) {
                e.stopPropagation();
                const seconds = parseInt(this.getAttribute('data-seconds'));
                if (seconds) {
                    startTimer(seconds);
                }
            });
        });

        // Show cooking mode
        document.getElementById('cookingMode').classList.add('active');
        document.body.style.overflow = 'auto';
    } catch (error) {
        showAlert('Error loading recipe: ' + error.message, 'error');
    }
}

function closeCookingMode() {
    document.getElementById('cookingMode').classList.remove('active');
    document.body.style.overflow = 'auto';
    stopAllTimers(); // Stop all timers if running
    timerCounter = 0; // Reset timer counter
}

// Timer Functions
let timers = new Map(); // Map of timerId -> {interval, display, seconds}
let timerCounter = 0;

function startTimer(seconds) {
    const timerId = timerCounter++;
    let remainingSeconds = seconds;

    // Create timer display element
    const timerDisplay = document.createElement('div');
    timerDisplay.className = 'timer-display';

    // Use bottom positioning on mobile (< 768px), top positioning on desktop
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
        <div id="timerText-${timerId}" class="timer-display-text">${formatTime(remainingSeconds)}</div>
    `;
    document.body.appendChild(timerDisplay);

    // Start interval
    const timerInterval = setInterval(() => {
        remainingSeconds--;

        const timerText = document.getElementById(`timerText-${timerId}`);
        if (timerText) {
            timerText.textContent = formatTime(remainingSeconds);
        }

        // Timer complete
        if (remainingSeconds <= 0) {
            clearInterval(timerInterval);
            timers.delete(timerId);

            if (timerDisplay) {
                timerDisplay.classList.add('completed');
                // Play sound notification
                playTimerSound();
                // Show alert
                showAlert(`Timer ${timerId + 1} finished! ⏱️`, 'success');

                // Auto-remove after 5 seconds
                setTimeout(() => {
                    timerDisplay.remove();
                }, 5000);
            }
        }
    }, 1000);

    // Store timer info
    timers.set(timerId, {
        interval: timerInterval,
        display: timerDisplay,
        seconds: seconds
    });
}

function stopTimer(timerId) {
    const timer = timers.get(timerId);
    if (timer) {
        clearInterval(timer.interval);
        timer.display.remove();
        timers.delete(timerId);
    }
}

function stopAllTimers() {
    for (const [timerId, timer] of timers) {
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
    // Create a simple beep sound using Web Audio API
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

    // Get saved theme or default to dark
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
    // Hide all pages
    document.querySelectorAll('.page').forEach(page => {
        page.classList.remove('active');
    });

    // Remove active from all tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });

    // Show selected page
    const pageElement = document.getElementById(pageName + 'Page');
    if (pageElement) {
        pageElement.classList.add('active');
    }

    // Mark selected tab as active
    event.target.classList.add('active');

    // Load recipes when showing home page
    if (pageName === 'home') {
        loadRecipes();
    }

    // Scroll to top
    window.scrollTo(0, 0);
}
