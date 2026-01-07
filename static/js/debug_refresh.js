/**
 * Debug Refresh Monitor - Helps detect unwanted auto-refresh behavior
 */

console.log('🐛 Debug Refresh Monitor loaded');

let refreshCount = 0;
let lastRefreshTime = Date.now();
let timerIds = [];
let intervalIds = [];

// Monitor page refreshes
window.addEventListener('beforeunload', function () {
    refreshCount++;
    console.log(`🔄 Page refresh detected: #${refreshCount} at ${new Date().toISOString()}`);

    // Store refresh info
    sessionStorage.setItem('debugRefreshCount', refreshCount);
    sessionStorage.setItem('lastRefreshTime', Date.now());
});

// Check for rapid refreshes on load
document.addEventListener('DOMContentLoaded', function () {
    const savedRefreshCount = parseInt(sessionStorage.getItem('debugRefreshCount')) || 0;
    const savedRefreshTime = parseInt(sessionStorage.getItem('lastRefreshTime')) || 0;
    const timeSinceLastRefresh = Date.now() - savedRefreshTime;

    if (savedRefreshCount > 0 && timeSinceLastRefresh < 10000) { // Less than 10 seconds
        console.warn(`⚠️ Rapid refresh detected! Count: ${savedRefreshCount}, Time since last: ${timeSinceLastRefresh}ms`);

        if (savedRefreshCount > 5) {
            console.error('🚨 EXCESSIVE REFRESH LOOP DETECTED! Disabling all auto-refresh mechanisms.');

            // Emergency disable all auto-refresh
            disableAllAutoRefresh();
        }
    }

    // Monitor for timers and intervals
    monitorTimersAndIntervals();

    // Create debug console
    createDebugConsole();
});

function disableAllAutoRefresh() {
    // Clear all existing timers and intervals
    timerIds.forEach(id => clearTimeout(id));
    intervalIds.forEach(id => clearInterval(id));

    // Override timer functions to prevent new ones
    const originalSetTimeout = window.setTimeout;
    const originalSetInterval = window.setInterval;

    window.setTimeout = function (fn, delay, ...args) {
        console.log('🚫 setTimeout blocked to prevent refresh loop');
        return null;
    };

    window.setInterval = function (fn, delay, ...args) {
        console.log('🚫 setInterval blocked to prevent refresh loop');
        return null;
    };

    // Disable form auto-submission
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function (e) {
            console.log('🚫 Form submission blocked - manual submission required');
            e.preventDefault();
            e.stopPropagation();
            return false;
        });
    });

    // Show emergency message
    showEmergencyMessage();
}

function monitorTimersAndIntervals() {
    // Override timer functions to track them
    const originalSetTimeout = window.setTimeout;
    const originalSetInterval = window.setInterval;

    window.setTimeout = function (fn, delay, ...args) {
        console.log(`⏱️ setTimeout created: ${delay}ms delay`);
        const id = originalSetTimeout.call(this, fn, delay, ...args);
        timerIds.push(id);
        return id;
    };

    window.setInterval = function (fn, delay, ...args) {
        console.log(`⏱️ setInterval created: ${delay}ms interval`);
        const id = originalSetInterval.call(this, fn, delay, ...args);
        intervalIds.push(id);
        return id;
    };
}

function createDebugConsole() {
    // Only create in development/debug mode
    if (!window.location.hostname.includes('localhost') && !window.location.hostname.includes('127.0.0.1')) {
        return;
    }

    const debugConsole = document.createElement('div');
    debugConsole.id = 'debug-refresh-console';
    debugConsole.innerHTML = `
        <div style="
            position: fixed;
            bottom: 10px;
            right: 10px;
            background: rgba(0, 0, 0, 0.9);
            color: #fff;
            padding: 10px;
            border-radius: 5px;
            border: 1px solid #333;
            z-index: 9999;
            font-family: monospace;
            font-size: 12px;
            max-width: 300px;
            display: none;
        ">
            <div style="font-weight: bold; color: #F05545; margin-bottom: 5px;">🐛 Debug Monitor</div>
            <div>Timers: <span id="timer-count">0</span></div>
            <div>Intervals: <span id="interval-count">0</span></div>
            <div>Refreshes: <span id="refresh-count">0</span></div>
            <div style="margin-top: 5px;">
                <button onclick="toggleDebugConsole()" style="font-size: 10px; background: #F05545; color: white; border: none; padding: 2px 5px; border-radius: 3px;">Hide</button>
                <button onclick="clearAllTimers()" style="font-size: 10px; background: #333; color: white; border: none; padding: 2px 5px; border-radius: 3px; margin-left: 3px;">Clear Timers</button>
            </div>
        </div>
    `;

    document.body.appendChild(debugConsole);

    // Show console if there are any timers
    updateDebugConsole();

    // Update every second
    setInterval(updateDebugConsole, 1000);

    // Keyboard shortcut to toggle
    document.addEventListener('keydown', function (e) {
        if (e.ctrlKey && e.shiftKey && e.key === 'D') {
            toggleDebugConsole();
        }
    });
}

function updateDebugConsole() {
    const console = document.getElementById('debug-refresh-console');
    if (!console) return;

    const timerCount = document.getElementById('timer-count');
    const intervalCount = document.getElementById('interval-count');
    const refreshCountEl = document.getElementById('refresh-count');

    if (timerCount) timerCount.textContent = timerIds.length;
    if (intervalCount) intervalCount.textContent = intervalIds.length;
    if (refreshCountEl) refreshCountEl.textContent = refreshCount;

    // Show console if there are active timers/intervals
    if (timerIds.length > 0 || intervalIds.length > 0) {
        console.querySelector('div').style.display = 'block';
    }
}

function toggleDebugConsole() {
    const console = document.getElementById('debug-refresh-console');
    if (console) {
        const display = console.querySelector('div').style.display;
        console.querySelector('div').style.display = display === 'none' ? 'block' : 'none';
    }
}

function clearAllTimers() {
    timerIds.forEach(id => clearTimeout(id));
    intervalIds.forEach(id => clearInterval(id));
    timerIds = [];
    intervalIds = [];
    console.log('🧹 All timers and intervals cleared');
}

function showEmergencyMessage() {
    const message = document.createElement('div');
    message.innerHTML = `
        <div style="
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(220, 53, 69, 0.95);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            z-index: 10000;
            font-family: 'Rajdhani', sans-serif;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
        ">
            <h3>🚨 Auto-Refresh Loop Detected</h3>
            <p>The system has disabled all auto-refresh mechanisms to prevent an infinite loop.</p>
            <p>Please refresh the page manually if needed.</p>
            <button onclick="this.parentElement.parentElement.remove()" style="
                background: white;
                color: #dc3545;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
                font-weight: bold;
                cursor: pointer;
            ">Close</button>
        </div>
    `;

    document.body.appendChild(message);
}

// Make functions globally available
window.toggleDebugConsole = toggleDebugConsole;
window.clearAllTimers = clearAllTimers;

console.log('✅ Debug Refresh Monitor ready - Press Ctrl+Shift+D to toggle debug console'); 