// ========================================
// DINING MACRO PLANNER - MAIN SCRIPT
// ========================================

// API Configuration
const API_BASE = 'http://localhost:8000';

// Global State
const state = {
    userId: '',
    diningHall: 'J2',
    mealType: 'Lunch',
    targets: {
        protein: 40,
        carbs: 150,
        fats: 50
    },
    availableFoods: [],
    selectedFoods: [],
    currentTotals: {
        protein: 0,
        carbs: 0,
        fats: 0,
        calories: 0
    },
    conversationActive: false  // Track if we're in an active conversation
};

// ========================================
// INITIALIZATION
// ========================================

document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
    attachEventListeners();
    updateMacroDisplays();
});

function initializeApp() {
    // Load saved user ID from localStorage
    const savedUserId = localStorage.getItem('userId');
    if (savedUserId) {
        state.userId = savedUserId;
        document.getElementById('user-id-header').value = savedUserId;
    }

    // Initialize dining hall and meal type
    syncHeaderSelectors();
}

function syncHeaderSelectors() {
    document.getElementById('dining-hall-header').value = state.diningHall;
    document.getElementById('meal-type-header').value = state.mealType;
}

// ========================================
// EVENT LISTENERS
// ========================================

function attachEventListeners() {
    // Header inputs
    document.getElementById('user-id-header').addEventListener('change', (e) => {
        state.userId = e.target.value.trim();
        localStorage.setItem('userId', state.userId);
    });

    document.getElementById('dining-hall-header').addEventListener('change', (e) => {
        state.diningHall = e.target.value;
        handleContextChange();  // Reset conversation when dining hall changes
        if (state.availableFoods.length > 0) {
            loadAvailableFoods();
        }
    });

    document.getElementById('meal-type-header').addEventListener('change', (e) => {
        state.mealType = e.target.value;
        handleContextChange();  // Reset conversation when meal type changes
        if (state.availableFoods.length > 0) {
            loadAvailableFoods();
        }
    });

    // Macro targets
    ['protein-target', 'carbs-target', 'fats-target'].forEach(id => {
        document.getElementById(id).addEventListener('change', (e) => {
            const macro = id.split('-')[0];
            state.targets[macro] = parseInt(e.target.value) || 0;
            updateMacroDisplays();
        });
    });

    // Calculator buttons
    document.getElementById('auto-match-btn').addEventListener('click', autoMatchFoods);
    document.getElementById('load-foods-btn').addEventListener('click', loadAvailableFoods);

    // Selection management
    document.getElementById('clear-selection-btn').addEventListener('click', clearSelection);
    document.getElementById('save-meal-btn').addEventListener('click', () => {
        document.getElementById('save-modal').classList.remove('hidden');
    });

    // Food table controls
    document.getElementById('food-search').addEventListener('input', filterAndSortFoods);
    document.getElementById('sort-by').addEventListener('change', filterAndSortFoods);

    // Chat
    document.getElementById('send-chat-btn').addEventListener('click', sendChatMessage);
    document.getElementById('chat-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendChatMessage();
        }
    });

    // Auto-resize chat textarea
    document.getElementById('chat-input').addEventListener('input', (e) => {
        e.target.style.height = 'auto';
        e.target.style.height = e.target.scrollHeight + 'px';
    });

    // Quick action buttons
    document.querySelectorAll('.quick-action-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const prompt = btn.dataset.prompt;
            document.getElementById('chat-input').value = prompt;
            sendChatMessage();
        });
    });

    // Modal
    document.querySelector('.modal-close').addEventListener('click', () => {
        document.getElementById('save-modal').classList.add('hidden');
    });

    document.querySelector('.modal-cancel').addEventListener('click', () => {
        document.getElementById('save-modal').classList.add('hidden');
    });

    document.getElementById('confirm-save-meal').addEventListener('click', saveMeal);

    // Rating stars
    document.querySelectorAll('.rating-stars i').forEach(star => {
        star.addEventListener('click', (e) => {
            const rating = parseInt(e.target.dataset.rating);
            document.querySelectorAll('.rating-stars i').forEach((s, idx) => {
                if (idx < rating) {
                    s.classList.remove('far');
                    s.classList.add('fas');
                } else {
                    s.classList.remove('fas');
                    s.classList.add('far');
                }
            });
        });
    });
}

// ========================================
// API FUNCTIONS
// ========================================

async function apiRequest(endpoint, method = 'GET', body = null) {
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json',
        },
    };

    if (body) {
        options.body = JSON.stringify(body);
    }

    try {
        const response = await fetch(`${API_BASE}${endpoint}`, options);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Request failed');
        }

        return data;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// ========================================
// LOAD AVAILABLE FOODS
// ========================================

async function loadAvailableFoods() {
    try {
        showToast('Loading available foods...', 'info');

        const data = await apiRequest(`/foods/${state.diningHall}/${state.mealType}`);
        state.availableFoods = data.foods;

        displayFoodsTable(state.availableFoods);
        showToast(`Loaded ${data.foods.length} foods from ${state.diningHall} ${state.mealType}`, 'success');

    } catch (error) {
        showToast(`Error loading foods: ${error.message}`, 'error');
    }
}

function displayFoodsTable(foods) {
    const tbody = document.getElementById('foods-table-body');
    tbody.innerHTML = '';

    if (foods.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="empty-state">
                    <i class="fas fa-inbox"></i>
                    <p>No foods found. Try loading from a different dining hall.</p>
                </td>
            </tr>
        `;
        return;
    }

    foods.forEach(food => {
        const row = createFoodRow(food);
        tbody.appendChild(row);
    });
}

function createFoodRow(food) {
    const tr = document.createElement('tr');
    tr.dataset.foodId = food.id;

    const confidenceClass = getConfidenceClass(food.confidence_score);
    const confidenceText = getConfidenceText(food.confidence_score);

    const isSelected = state.selectedFoods.some(f => f.id === food.id);

    tr.innerHTML = `
        <td class="food-name">${food.name}</td>
        <td>${food.protein || 0}g</td>
        <td>${food.carbs || 0}g</td>
        <td>${food.fats || 0}g</td>
        <td>${food.calories || 0}</td>
        <td><span class="confidence-badge ${confidenceClass}">${confidenceText}</span></td>
        <td>
            <button class="add-food-btn" onclick="addFoodToSelection(${food.id})" ${isSelected ? 'disabled' : ''}>
                ${isSelected ? 'Added' : 'Add'}
            </button>
        </td>
    `;

    return tr;
}

function getConfidenceClass(score) {
    if (score >= 0.8) return 'confidence-high';
    if (score >= 0.5) return 'confidence-medium';
    return 'confidence-low';
}

function getConfidenceText(score) {
    if (score >= 0.8) return 'High';
    if (score >= 0.5) return 'Medium';
    return 'Low';
}

// ========================================
// FOOD SELECTION
// ========================================

window.addFoodToSelection = function(foodId) {
    const food = state.availableFoods.find(f => f.id === foodId);
    if (!food) return;

    // Check if already selected
    if (state.selectedFoods.some(f => f.id === foodId)) {
        return;
    }

    state.selectedFoods.push(food);
    updateSelection();
    updateMacroDisplays();

    // Update table button
    const row = document.querySelector(`tr[data-food-id="${foodId}"] .add-food-btn`);
    if (row) {
        row.disabled = true;
        row.textContent = 'Added';
    }

    showToast(`Added ${food.name}`, 'success');
};

function removeFoodFromSelection(foodId) {
    state.selectedFoods = state.selectedFoods.filter(f => f.id !== foodId);
    updateSelection();
    updateMacroDisplays();

    // Update table button
    const row = document.querySelector(`tr[data-food-id="${foodId}"] .add-food-btn`);
    if (row) {
        row.disabled = false;
        row.textContent = 'Add';
    }
}

function clearSelection() {
    state.selectedFoods = [];
    updateSelection();
    updateMacroDisplays();

    // Reset all buttons
    document.querySelectorAll('.add-food-btn').forEach(btn => {
        btn.disabled = false;
        btn.textContent = 'Add';
    });

    showToast('Selection cleared', 'info');
}

function updateSelection() {
    // Calculate totals
    state.currentTotals = {
        protein: state.selectedFoods.reduce((sum, f) => sum + (f.protein || 0), 0),
        carbs: state.selectedFoods.reduce((sum, f) => sum + (f.carbs || 0), 0),
        fats: state.selectedFoods.reduce((sum, f) => sum + (f.fats || 0), 0),
        calories: state.selectedFoods.reduce((sum, f) => sum + (f.calories || 0), 0)
    };

    // Update selected foods list
    const container = document.getElementById('selected-foods-list');
    container.innerHTML = '';

    if (state.selectedFoods.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: var(--text-secondary); padding: 1rem;">No foods selected yet</p>';
        return;
    }

    state.selectedFoods.forEach(food => {
        const item = document.createElement('div');
        item.className = 'selected-food-item';
        item.innerHTML = `
            <div class="selected-food-info">
                <div class="selected-food-name">${food.name}</div>
                <div class="selected-food-macros">
                    P: ${food.protein || 0}g | C: ${food.carbs || 0}g | F: ${food.fats || 0}g
                </div>
            </div>
            <button class="remove-food-btn" onclick="removeFoodFromSelection(${food.id})">
                <i class="fas fa-times"></i>
            </button>
        `;
        container.appendChild(item);
    });
}

window.removeFoodFromSelection = removeFoodFromSelection;

function updateMacroDisplays() {
    // Update current vs target labels
    document.getElementById('protein-current').textContent =
        `${Math.round(state.currentTotals.protein)}g / ${state.targets.protein}g`;
    document.getElementById('carbs-current').textContent =
        `${Math.round(state.currentTotals.carbs)}g / ${state.targets.carbs}g`;
    document.getElementById('fats-current').textContent =
        `${Math.round(state.currentTotals.fats)}g / ${state.targets.fats}g`;
    document.getElementById('total-calories').textContent = Math.round(state.currentTotals.calories);

    // Update progress bars
    updateProgressBar('protein', state.currentTotals.protein, state.targets.protein);
    updateProgressBar('carbs', state.currentTotals.carbs, state.targets.carbs);
    updateProgressBar('fats', state.currentTotals.fats, state.targets.fats);
}

function updateProgressBar(macro, current, target) {
    const percentage = Math.min((current / target) * 100, 100);
    const progressBar = document.getElementById(`${macro}-progress`);
    progressBar.style.width = `${percentage}%`;
}

// ========================================
// AUTO-MATCH ALGORITHM
// ========================================

async function autoMatchFoods() {
    if (!state.userId) {
        showToast('Please enter your name first', 'error');
        return;
    }

    if (state.availableFoods.length === 0) {
        await loadAvailableFoods();
    }

    if (state.availableFoods.length === 0) {
        showToast('No foods available to match', 'error');
        return;
    }

    showToast('Finding optimal food combination...', 'info');

    // Use greedy algorithm to match macros
    const result = findOptimalCombination(
        state.availableFoods,
        state.targets.protein,
        state.targets.carbs,
        state.targets.fats
    );

    if (result.foods.length === 0) {
        showToast('Could not find a good match. Try adjusting your targets.', 'warning');
        return;
    }

    // Clear current selection
    clearSelection();

    // Add matched foods
    result.foods.forEach(food => {
        state.selectedFoods.push(food);
    });

    updateSelection();
    updateMacroDisplays();

    // Update table buttons
    result.foods.forEach(food => {
        const row = document.querySelector(`tr[data-food-id="${food.id}"] .add-food-btn`);
        if (row) {
            row.disabled = true;
            row.textContent = 'Added';
        }
    });

    showToast(`Found ${result.foods.length} foods matching your targets!`, 'success');
}

function findOptimalCombination(foods, targetProtein, targetCarbs, targetFats) {
    // Greedy algorithm to find foods that match macro targets
    const selected = [];
    let currentProtein = 0;
    let currentCarbs = 0;
    let currentFats = 0;

    // Sort foods by protein density (protein per calorie) for efficient matching
    const sortedFoods = [...foods].sort((a, b) => {
        const aScore = calculateMatchScore(a, targetProtein, targetCarbs, targetFats);
        const bScore = calculateMatchScore(b, targetProtein, targetCarbs, targetFats);
        return bScore - aScore;
    });

    // Try to match each macro target
    const tolerance = 10; // ±10g tolerance

    for (const food of sortedFoods) {
        if (selected.length >= 8) break; // Max 8 foods

        const newProtein = currentProtein + (food.protein || 0);
        const newCarbs = currentCarbs + (food.carbs || 0);
        const newFats = currentFats + (food.fats || 0);

        // Check if adding this food improves the match
        const currentDistance = Math.abs(targetProtein - currentProtein) +
                               Math.abs(targetCarbs - currentCarbs) +
                               Math.abs(targetFats - currentFats);

        const newDistance = Math.abs(targetProtein - newProtein) +
                           Math.abs(targetCarbs - newCarbs) +
                           Math.abs(targetFats - newFats);

        // Add food if it improves match and doesn't overshoot too much
        if (newDistance <= currentDistance ||
            (newProtein <= targetProtein + tolerance &&
             newCarbs <= targetCarbs + tolerance &&
             newFats <= targetFats + tolerance)) {
            selected.push(food);
            currentProtein = newProtein;
            currentCarbs = newCarbs;
            currentFats = newFats;

            // Check if we're close enough
            if (Math.abs(targetProtein - currentProtein) <= tolerance &&
                Math.abs(targetCarbs - currentCarbs) <= tolerance &&
                Math.abs(targetFats - currentFats) <= tolerance) {
                break;
            }
        }
    }

    return {
        foods: selected,
        totals: {
            protein: currentProtein,
            carbs: currentCarbs,
            fats: currentFats
        }
    };
}

function calculateMatchScore(food, targetProtein, targetCarbs, targetFats) {
    // Score based on how well this food contributes to targets
    const proteinScore = (food.protein || 0) / targetProtein;
    const carbsScore = (food.carbs || 0) / targetCarbs;
    const fatsScore = (food.fats || 0) / targetFats;

    // Weight protein higher
    return (proteinScore * 2) + carbsScore + fatsScore;
}

// ========================================
// TABLE FILTERING AND SORTING
// ========================================

function filterAndSortFoods() {
    const searchTerm = document.getElementById('food-search').value.toLowerCase();
    const sortBy = document.getElementById('sort-by').value;

    let filtered = state.availableFoods;

    // Filter by search term
    if (searchTerm) {
        filtered = filtered.filter(food =>
            food.name.toLowerCase().includes(searchTerm)
        );
    }

    // Sort
    filtered.sort((a, b) => {
        if (sortBy === 'name') {
            return a.name.localeCompare(b.name);
        } else if (sortBy === 'confidence') {
            return (b.confidence_score || 0) - (a.confidence_score || 0);
        } else {
            return (b[sortBy] || 0) - (a[sortBy] || 0);
        }
    });

    displayFoodsTable(filtered);
}

// ========================================
// AI CHAT
// ========================================

async function sendChatMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();

    if (!message) return;

    if (!state.userId) {
        showToast('Please enter your name in the header first', 'error');
        return;
    }

    // Add user message to chat
    addMessageToChat('user', message);

    // Clear input
    input.value = '';
    input.style.height = 'auto';

    // Show typing indicator
    document.getElementById('typing-indicator').classList.remove('hidden');

    try {
        let response;

        // Use /refine for follow-up messages, /recommendations for first message
        if (state.conversationActive) {
            // Follow-up conversation
            response = await apiRequest('/refine', 'POST', {
                user_id: state.userId,
                dining_hall: state.diningHall,
                meal_type: state.mealType,
                message: message
            });

            // Hide typing indicator
            document.getElementById('typing-indicator').classList.add('hidden');

            // Add AI response to chat
            addMessageToChat('assistant', response.refined_recommendations);

            // Update suggestions panel
            updateSuggestionsPanel(response.refined_recommendations);
        } else {
            // Initial recommendation request
            response = await apiRequest('/recommendations', 'POST', {
                user_id: state.userId,
                dining_hall: state.diningHall,
                meal_type: state.mealType,
                protein_target: state.targets.protein,
                carbs_target: state.targets.carbs,
                fats_target: state.targets.fats
            });

            // Hide typing indicator
            document.getElementById('typing-indicator').classList.add('hidden');

            // Add AI response to chat
            addMessageToChat('assistant', response.recommendations);

            // Update suggestions panel
            updateSuggestionsPanel(response.recommendations);

            // Mark conversation as active
            state.conversationActive = true;
        }

    } catch (error) {
        document.getElementById('typing-indicator').classList.add('hidden');
        addMessageToChat('assistant', `Sorry, I encountered an error: ${error.message}`);
    }
}

function addMessageToChat(role, content) {
    const messagesContainer = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    messageDiv.innerHTML = `
        <div class="message-avatar">
            <i class="fas fa-${role === 'user' ? 'user' : 'robot'}"></i>
        </div>
        <div class="message-content">
            <div class="message-header">
                <strong>${role === 'user' ? state.userId || 'You' : 'AI Assistant'}</strong>
                <span class="message-time">${time}</span>
            </div>
            ${formatMessageContent(content)}
        </div>
    `;

    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function formatMessageContent(content) {
    // Convert markdown-style formatting to HTML
    let formatted = content
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        .replace(/\n/g, '<br>');

    return `<p>${formatted}</p>`;
}

function updateSuggestionsPanel(content) {
    const panel = document.getElementById('ai-suggestions-content');
    panel.innerHTML = `<div style="white-space: pre-wrap; line-height: 1.8;">${content}</div>`;
}

function resetConversation() {
    state.conversationActive = false;
    showToast('Conversation reset. Starting fresh!', 'info');
}

// Automatically reset conversation when context changes significantly
function handleContextChange() {
    if (state.conversationActive) {
        resetConversation();
    }
}

// ========================================
// SAVE MEAL
// ========================================

async function saveMeal() {
    if (state.selectedFoods.length === 0) {
        showToast('Please select some foods first', 'error');
        return;
    }

    if (!state.userId) {
        showToast('Please enter your name first', 'error');
        return;
    }

    const rating = document.querySelectorAll('.rating-stars i.fas').length;
    const notes = document.getElementById('meal-notes').value;

    try {
        // Save meal selection
        const foodIds = state.selectedFoods.map(f => f.id);

        await apiRequest('/select', 'POST', {
            user_id: state.userId,
            food_ids: foodIds,
            total_protein: state.currentTotals.protein,
            total_carbs: state.currentTotals.carbs,
            total_fats: state.currentTotals.fats,
            total_calories: state.currentTotals.calories
        });

        // If rated, save rating
        if (rating > 0) {
            // This would need the meal ID from the previous response
            // For now, just show success
        }

        showToast('Meal saved successfully!', 'success');
        document.getElementById('save-modal').classList.add('hidden');

        // Reset rating
        document.querySelectorAll('.rating-stars i').forEach(star => {
            star.classList.remove('fas');
            star.classList.add('far');
        });
        document.getElementById('meal-notes').value = '';

    } catch (error) {
        showToast(`Error saving meal: ${error.message}`, 'error');
    }
}

// ========================================
// UTILITIES
// ========================================

function showToast(message, type = 'info') {
    // Simple toast notification
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : type === 'warning' ? '#f59e0b' : '#6366f1'};
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 0.5rem;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        z-index: 10000;
        animation: slideInRight 0.3s ease;
    `;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideOutRight 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Add animations to document
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

console.log('Dining Macro Planner initialized');
console.log('API:', API_BASE);
