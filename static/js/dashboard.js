// Global variables
let refreshInterval = null;
let currentTheme = 'light';

// Utility Functions
function formatDate(date) {
    return new Date(date).toLocaleString();
}

function formatNumber(num, decimals = 1) {
    return parseFloat(num).toFixed(decimals);
}

function showToast(message, type = 'info') {
    // Create toast container if not exists
    if (!$('#toast-container').length) {
        $('body').append('<div id="toast-container" style="position: fixed; top: 20px; right: 20px; z-index: 9999;"></div>');
    }
    
    const toastId = 'toast-' + Date.now();
    const bgColor = type === 'success' ? 'bg-success' : type === 'error' ? 'bg-danger' : 'bg-info';
    
    const toast = `
        <div id="${toastId}" class="toast show" role="alert" aria-live="assertive" aria-atomic="true" data-bs-autohide="true" data-bs-delay="3000">
            <div class="toast-header ${bgColor} text-white">
                <strong class="me-auto"><i class="fas fa-bell"></i> Notification</strong>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;
    
    $('#toast-container').append(toast);
    
    setTimeout(() => {
        $(`#${toastId}`).remove();
    }, 3000);
}

function exportToExcel(data, filename) {
    // Simple CSV export
    if (!data || data.length === 0) {
        showToast('No data to export', 'error');
        return;
    }
    
    const headers = Object.keys(data[0]);
    const csvRows = [];
    csvRows.push(headers.join(','));
    
    for (const row of data) {
        const values = headers.map(header => {
            const val = row[header];
            return `"${val}"`;
        });
        csvRows.push(values.join(','));
    }
    
    const blob = new Blob([csvRows.join('\n')], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${filename}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
    
    showToast(`Exported ${data.length} records to ${filename}.csv`, 'success');
}

// Dashboard Functions
function loadDashboardData() {
    if ($('#stats-cards').length) {
        loadStatistics();
        loadInsights();
        loadTopPerformers();
    }
}

function loadStatistics() {
    $.get('/api/statistics')
        .done(function(data) {
            $('#total-students').text(data.total_students);
            $('#avg-score').text(formatNumber(data.avg_final_score, 1));
            $('#avg-attendance').text(formatNumber(data.avg_attendance, 1) + '%');
            $('#avg-study-hours').text(formatNumber(data.avg_study_hours, 1));
        })
        .fail(function() {
            console.error('Failed to load statistics');
        });
}

function loadInsights() {
    $.get('/api/insights')
        .done(function(data) {
            const insightsList = $('#insights-list');
            if (insightsList.length) {
                let html = '<ul class="list-group list-group-flush">';
                data.insights.forEach(insight => {
                    html += `<li class="list-group-item"><i class="fas fa-chart-line text-primary me-2"></i> ${insight}</li>`;
                });
                html += '</ul>';
                insightsList.html(html);
            }
        })
        .fail(function() {
            console.error('Failed to load insights');
        });
}

function loadTopPerformers() {
    $.get('/api/top-performers?limit=10')
        .done(function(data) {
            const tableBody = $('#top-performers-table tbody');
            if (tableBody.length && data.length) {
                let html = '';
                data.forEach((student, index) => {
                    html += `
                        <tr>
                            <td><span class="badge bg-warning">#${index + 1}</span></td>
                            <td><i class="fas fa-user-graduate me-2"></i>${student.name}</td>
                            <td><strong>${student.final_score}</strong></td>
                            <td><span class="badge bg-success">${student.grade}</span></td>
                            <td>${student.attendance_percentage}%</td>
                        </tr>
                    `;
                });
                tableBody.html(html);
            }
        })
        .fail(function() {
            console.error('Failed to load top performers');
        });
}

// Chart Functions
function createBarChart(canvasId, labels, data, title, colors = null) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;
    
    const defaultColors = ['#2E86AB', '#3AAE5C', '#5D9B9B', '#F18F01', '#C73E1D', '#A23B72'];
    
    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: title,
                data: data,
                backgroundColor: colors || defaultColors,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { position: 'top' },
                tooltip: { callbacks: { label: (ctx) => `${ctx.raw} students` } }
            }
        }
    });
}

function createPieChart(canvasId, labels, data, title) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;
    
    return new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: ['#2E86AB', '#A23B72', '#3AAE5C', '#F18F01', '#5D9B9B']
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'bottom' },
                title: { display: true, text: title }
            }
        }
    });
}

// Auto-refresh functionality
function startAutoRefresh(interval = 30000) {
    if (refreshInterval) clearInterval(refreshInterval);
    refreshInterval = setInterval(() => {
        if (document.visibilityState === 'visible') {
            refreshData();
        }
    }, interval);
}

function stopAutoRefresh() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
}

function refreshData() {
    showToast('Refreshing data...', 'info');
    location.reload();
}

// Theme Toggle
function toggleTheme() {
    currentTheme = currentTheme === 'light' ? 'dark' : 'light';
    
    if (currentTheme === 'dark') {
        $('body').css({
            'background-color': '#1a1a2e',
            'color': '#eee'
        });
        $('.card').css('background-color', '#16213e');
        $('.table').css('color', '#eee');
        showToast('Dark theme enabled', 'success');
    } else {
        $('body').css({
            'background-color': '#f5f7fa',
            'color': '#2C3E50'
        });
        $('.card').css('background-color', 'white');
        $('.table').css('color', '#2C3E50');
        showToast('Light theme enabled', 'success');
    }
    
    localStorage.setItem('theme', currentTheme);
}

// Load saved theme
function loadTheme() {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
        toggleTheme();
    }
}

// Prediction Form Helper
function updateRangeValue(slider, spanId) {
    const span = document.getElementById(spanId);
    if (span) {
        const suffix = slider.name.includes('hours') ? ' hours' : '%';
        span.innerText = slider.value + suffix;
    }
}

// Export Functions
function exportDashboardData() {
    $.get('/api/top-performers?limit=50')
        .done(function(data) {
            exportToExcel(data, 'dashboard_export');
        })
        .fail(function() {
            showToast('Failed to export data', 'error');
        });
}

// Initialize on page load
$(document).ready(function() {
    console.log('Dashboard JS loaded');
    loadTheme();
    
    // Initialize tooltips
    $('[data-bs-toggle="tooltip"]').tooltip();
    
    // Add theme toggle button to navbar if not exists
    if ($('#themeToggle').length === 0 && $('.navbar-nav').length) {
        $('.navbar-nav').append(`
            <li class="nav-item">
                <a class="nav-link" href="#" id="themeToggle" onclick="toggleTheme()">
                    <i class="fas fa-moon"></i>
                </a>
            </li>
        `);
    }
    
    // Add export button
    if ($('#exportBtn').length === 0 && $('.card-header').length) {
        $('.card-header').each(function() {
            if ($(this).text().includes('Top Performers')) {
                $(this).append(`
                    <button class="btn btn-sm btn-outline-primary float-end" onclick="exportDashboardData()">
                        <i class="fas fa-download"></i> Export
                    </button>
                `);
            }
        });
    }
    
    // Load dashboard data if on dashboard page
    if (window.location.pathname.includes('dashboard')) {
        loadDashboardData();
        startAutoRefresh(60000); // Refresh every minute
    }
    
    // Cleanup on page unload
    $(window).on('beforeunload', function() {
        stopAutoRefresh();
    });
});

// Handle AJAX errors globally
$(document).ajaxError(function(event, jqXHR, settings, error) {
    console.error('AJAX Error:', error);
    if (jqXHR.status === 401) {
        window.location.href = '/login';
    }
});

// Add loading indicator for AJAX requests
$(document).ajaxStart(function() {
    $('#loadingOverlay').show();
}).ajaxStop(function() {
    $('#loadingOverlay').hide();
});

// Create loading overlay if not exists
if (!$('#loadingOverlay').length) {
    $('body').append(`
        <div id="loadingOverlay" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 99999; text-align: center; padding-top: 20%;">
            <div class="spinner-border text-light" style="width: 4rem; height: 4rem;"></div>
            <p class="text-light mt-3">Loading...</p>
        </div>
    `);
}