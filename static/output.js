// Theme toggle functionality
const themeToggleBtn = document.getElementById('theme-toggle-btn');
const htmlElement = document.documentElement;
const prefersDarkScheme = window.matchMedia("(prefers-color-scheme: dark)");

// Check for saved theme preference or use the system preference
const savedTheme = localStorage.getItem('theme');
if (savedTheme) {
    htmlElement.setAttribute('data-theme', savedTheme);
    updateToggleButton(savedTheme);
} else if (prefersDarkScheme.matches) {
    htmlElement.setAttribute('data-theme', 'dark');
    updateToggleButton('dark');
}

// Toggle theme when button is clicked
themeToggleBtn.addEventListener('click', () => {
    const currentTheme = htmlElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

    htmlElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateToggleButton(newTheme);
});

function updateToggleButton(theme) {
    if (theme === 'dark') {
        themeToggleBtn.innerHTML = '<i class="fas fa-sun"></i> <span>Light Mode</span>';
    } else {
        themeToggleBtn.innerHTML = '<i class="fas fa-moon"></i> <span>Dark Mode</span>';
    }
}