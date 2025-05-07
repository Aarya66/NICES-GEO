// Theme toggle functionality
const themeToggle = document.getElementById('theme-toggle');
const body = document.body;

themeToggle.addEventListener('click', () => {
    body.classList.toggle('dark-mode');
    if (body.classList.contains('dark-mode')) {
        themeToggle.textContent = 'Light Theme';
    } else {
        themeToggle.textContent = 'Dark Theme';
    }
    
    // Save theme preference to localStorage
    localStorage.setItem('darkMode', body.classList.contains('dark-mode'));
});

// Load saved theme preference
if (localStorage.getItem('darkMode') === 'true') {
    body.classList.add('dark-mode');
    themeToggle.textContent = 'Light Theme';
}

// Sidebar toggle functionality
const sidebarToggle = document.getElementById('sidebar-toggle');
const sidebar = document.getElementById('sidebar');
const mainContent = document.querySelector('.main-content');

sidebarToggle.addEventListener('click', () => {
    sidebar.classList.toggle('sidebar-collapsed');
    mainContent.classList.toggle('main-content-expanded');
    
    // Toggle visibility of text elements
    const textElements = document.querySelectorAll('.sidebar-text');
    textElements.forEach(el => {
        if (sidebar.classList.contains('sidebar-collapsed')) {
            el.style.opacity = '0';
            setTimeout(() => { el.style.display = 'none'; }, 300);
        } else {
            el.style.display = 'block';
            setTimeout(() => { el.style.opacity = '1'; }, 10);
        }
    });
    
    // Save sidebar state to localStorage
    localStorage.setItem('sidebarCollapsed', sidebar.classList.contains('sidebar-collapsed'));
});

// Load saved sidebar state
if (localStorage.getItem('sidebarCollapsed') === 'true') {
    sidebar.classList.add('sidebar-collapsed');
    mainContent.classList.add('main-content-expanded');
    
    // Hide text elements on load if sidebar is collapsed
    const textElements = document.querySelectorAll('.sidebar-text');
    textElements.forEach(el => {
        el.style.opacity = '0';
        el.style.display = 'none';
    });
}

// Search history functionality
const searchForm = document.getElementById('search-form');
const queryInput = document.getElementById('query');
const searchHistory = document.getElementById('search-history');
const newChatBtn = document.getElementById('new-chat-btn');
const processingText = document.getElementById('processing');

// Load search history from localStorage
let searchHistoryItems = JSON.parse(localStorage.getItem('searchHistory')) || [];

// Render search history with full text
function renderSearchHistory() {
    searchHistory.innerHTML = '';
    
    // Display only the last 10 items
    const displayItems = searchHistoryItems.slice(0, 10);
    
    displayItems.forEach((item, index) => {
        const historyItem = document.createElement('div');
        historyItem.className = 'history-item';
        historyItem.dataset.index = index;
        
        // Create icon element
        const iconElement = document.createElement('i');
        iconElement.className = 'fas fa-history';
        
        // Create text span with proper class
        const textSpan = document.createElement('span');
        textSpan.className = 'sidebar-text';
        textSpan.textContent = item;
        
        // Apply initial visibility based on sidebar state
        if (sidebar.classList.contains('sidebar-collapsed')) {
            textSpan.style.opacity = '0';
            textSpan.style.display = 'none';
        }
        
        // Append elements to history item
        historyItem.appendChild(iconElement);
        historyItem.appendChild(textSpan);
        
        historyItem.addEventListener('click', () => {
            queryInput.value = item;
            // Optionally submit the form automatically
            // searchForm.submit();
        });
        
        searchHistory.appendChild(historyItem);
    });
}

// Save a new search query to history
function saveSearchQuery(query) {
    if (!query.trim()) return;
    
    // Remove the query if it already exists (to avoid duplicates)
    searchHistoryItems = searchHistoryItems.filter(item => item !== query);
    
    // Add the new query to the beginning of the array
    searchHistoryItems.unshift(query);
    
    // Keep only the last 20 items
    if (searchHistoryItems.length > 20) {
        searchHistoryItems = searchHistoryItems.slice(0, 20);
    }
    
    // Save to localStorage
    localStorage.setItem('searchHistory', JSON.stringify(searchHistoryItems));
    
    // Update the UI
    renderSearchHistory();
}

// Handle form submission
searchForm.addEventListener('submit', function(event) {
    // Show processing message
    if (processingText) {
        processingText.textContent = 'Processing query...';
        processingText.classList.remove('hidden');
    }
    
    // Save the query to history
    saveSearchQuery(queryInput.value);
});

// Handle new chat button
newChatBtn.addEventListener('click', () => {
    queryInput.value = '';
    queryInput.focus();
    
    // Hide processing message if visible
    if (processingText) {
        processingText.classList.add('hidden');
    }
});

// Handle "More" button click
document.getElementById('more-btn').addEventListener('click', () => {
    // You can implement functionality to show more history items
    alert('More functionality coming soon!');
});

// Voice input functionality
const voiceInputBtn = document.getElementById('voice-input-btn');
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

if (SpeechRecognition) {
    const recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onresult = function(event) {
        const speechResult = event.results[0][0].transcript;
        queryInput.value = speechResult;
    };

    recognition.onerror = function(event) {
        console.error('Speech recognition error', event.error);
        alert('Sorry, there was an error with voice recognition.');
    };

    recognition.onstart = function() {
        voiceInputBtn.classList.add('listening');
    };

    recognition.onend = function() {
        voiceInputBtn.classList.remove('listening');
    };

    voiceInputBtn.addEventListener('click', () => {
        recognition.start();
    });
} else {
    voiceInputBtn.disabled = true;
    voiceInputBtn.title = 'Voice input not supported in this browser';
}

// Initialize the search history on page load
renderSearchHistory();