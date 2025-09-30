// DOM Elements
const loginPage = document.getElementById('login-page');
const signupPage = document.getElementById('signup-page');
const dashboard = document.getElementById('dashboard');
const showSignupBtn = document.getElementById('show-signup');
const showLoginBtn = document.getElementById('show-login');
const loginBtn = document.getElementById('login-btn');
const signupBtn = document.getElementById('signup-btn');
const logoutBtn = document.getElementById('logout-btn');
const addTaskBtn = document.getElementById('add-task-btn');
const displayUsername = document.getElementById('display-username');
const flashMessages = document.querySelectorAll('.flash-message');

// Show/Hide Pages
showSignupBtn.addEventListener('click', () => {
    loginPage.style.display = 'none';
    signupPage.style.display = 'flex';
});

showLoginBtn.addEventListener('click', () => {
    signupPage.style.display = 'none';
    loginPage.style.display = 'flex';
});

// Login Functionality
loginBtn.addEventListener('click', () => {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    if (username && password) {
        // Simulate successful login
        loginPage.style.display = 'none';
        dashboard.style.display = 'block';
        displayUsername.textContent = username;
        
        // Show success message
        document.querySelector('.flash-success').style.display = 'flex';
    } else {
        // Show error message
        document.querySelector('.flash-danger').style.display = 'flex';
    }
});

// Signup Functionality
signupBtn.addEventListener('click', () => {
    const username = document.getElementById('signup-username').value;
    const password = document.getElementById('signup-password').value;
    const confirmPassword = document.getElementById('confirm-password').value;
    
    if (password !== confirmPassword) {
        alert("Passwords don't match!");
        return;
    }
    
    if (username && password) {
        // Simulate successful signup
        signupPage.style.display = 'none';
        loginPage.style.display = 'flex';
        
        // Clear form
        document.getElementById('signup-username').value = '';
        document.getElementById('signup-password').value = '';
        document.getElementById('confirm-password').value = '';
        document.getElementById('email').value = '';
    }
});

// Logout Functionality
logoutBtn.addEventListener('click', () => {
    dashboard.style.display = 'none';
    loginPage.style.display = 'flex';
});

// Add Task Functionality
addTaskBtn.addEventListener('click', () => {
    const taskName = document.getElementById('task-name').value;
    const taskDay = document.getElementById('task-day').value;
    
    if (taskName) {
        const todoColumn = document.getElementById('todo-column');
        
        const taskCard = document.createElement('div');
        taskCard.className = 'task-card';
        taskCard.draggable = true;
        taskCard.innerHTML = `
            <div class="task-header">
                <div class="task-title">${taskName}</div>
                <div class="task-actions">
                    <button><i class="fas fa-edit"></i></button>
                    <button><i class="fas fa-trash"></i></button>
                </div>
            </div>
            <div class="task-meta">
                <div class="task-day">${taskDay}</div>
                <div class="task-user">
                    <i class="fas fa-user"></i>
                    <span>${displayUsername.textContent}</span>
                </div>
            </div>
        `;
        
        todoColumn.appendChild(taskCard);
        
        // Clear form
        document.getElementById('task-name').value = '';
        
        // Update task count
        const taskCount = todoColumn.parentElement.querySelector('.task-count');
        taskCount.textContent = parseInt(taskCount.textContent) + 1;
        
        // Add event listeners to new buttons
        addTaskEventListeners(taskCard);
    }
});

// Close flash messages
flashMessages.forEach(flash => {
    const closeBtn = flash.querySelector('.flash-close');
    closeBtn.addEventListener('click', () => {
        flash.style.display = 'none';
    });
});

// Set current date
const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
const today = new Date();
document.getElementById('today-date').textContent = today.toLocaleDateString('en-US', options);

// Drag and Drop functionality
const taskCards = document.querySelectorAll('.task-card');
const columns = document.querySelectorAll('.task-list');

taskCards.forEach(card => {
    card.addEventListener('dragstart', () => {
        card.classList.add('dragging');
    });
    
    card.addEventListener('dragend', () => {
        card.classList.remove('dragging');
    });
});

columns.forEach(column => {
    column.addEventListener('dragover', e => {
        e.preventDefault();
        const afterElement = getDragAfterElement(column, e.clientY);
        const draggable = document.querySelector('.dragging');
        if (afterElement == null) {
            column.appendChild(draggable);
        } else {
            column.insertBefore(draggable, afterElement);
        }
    });
});

function getDragAfterElement(column, y) {
    const draggableElements = [...column.querySelectorAll('.task-card:not(.dragging)')];
    
    return draggableElements.reduce((closest, child) => {
        const box = child.getBoundingClientRect();
        const offset = y - box.top - box.height / 2;
        if (offset < 0 && offset > closest.offset) {
            return { offset: offset, element: child };
        } else {
            return closest;
        }
    }, { offset: Number.NEGATIVE_INFINITY }).element;
}

// Add event listeners to task actions
function addTaskEventListeners(taskCard) {
    const editBtn = taskCard.querySelector('.fa-edit').parentElement;
    const deleteBtn = taskCard.querySelector('.fa-trash').parentElement;
    
    editBtn.addEventListener('click', () => {
        const taskTitle = taskCard.querySelector('.task-title');
        const newTitle = prompt('Edit task name:', taskTitle.textContent);
        if (newTitle !== null && newTitle.trim() !== '') {
            taskTitle.textContent = newTitle;
        }
    });
    
    deleteBtn.addEventListener('click', () => {
        if (confirm('Are you sure you want to delete this task?')) {
            const column = taskCard.parentElement;
            taskCard.remove();
            
            // Update task count
            const taskCount = column.parentElement.querySelector('.task-count');
            taskCount.textContent = parseInt(taskCount.textContent) - 1;
        }
    });
}

// Initialize event listeners for existing tasks
document.querySelectorAll('.task-card').forEach(addTaskEventListeners);
