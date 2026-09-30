// Global variables
let chartInstance = null;
let healthChartInstance = null;
let currentMachine = 'M-001';

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    loadMachineList();
    loadDashboardSummary();
    loadMachine('M-001');
    
    // Auto-refresh every 5 seconds
    setInterval(() => {
        loadDashboardSummary();
        loadMachine(currentMachine);
    }, 5000);
});

function loadMachineList() {
    fetch('/api/machines')
        .then(res => res.json())
        .then(data => {
            const select = document.getElementById('machineSelect');
            select.innerHTML = '';
            data.forEach(machine => {
                const option = document.createElement('option');
                option.value = machine.id;
                option.textContent = `${machine.name} (${machine.id})`;
                select.appendChild(option);
            });
        })
        .catch(err => console.error('Error loading machine list:', err));
}

function loadDashboardSummary() {
    fetch('/api/dashboard')
        .then(res => res.json())
        .then(data => {
            document.getElementById('totalMachines').textContent = data.total;
            document.getElementById('onlineDevices').textContent = data.online;
            document.getElementById('warningMachines').textContent = data.warning;
            document.getElementById('criticalMachines').textContent = data.critical;
            document.getElementById('avgHealth').textContent = data.avg_health + '%';
        })
        .catch(err => console.error('Error loading dashboard summary:', err));
}

function loadMachine(machineId) {
    currentMachine = machineId;
    
    fetch(`/api/machine/${machineId}`)
        .then(res => res.json())
        .then(data => {
            updateMachineInfo(data);
            updateSensors(data);
            updateAlerts(data);
            updateMaintenance(data);
            updateChart(data);
            updateGauge(data.info.health);
            loadHealthTrend(machineId);
        })
        .catch(err => console.error('Error loading machine data:', err));
}

function updateMachineInfo(data) {
    const info = data.info;
    document.getElementById('machineName').textContent = info.name;
    document.getElementById('machineId').textContent = `ID: ${info.id}`;
    document.getElementById('machineFactory').textContent = info.factory || 'N/A';
    
    const badge = document.getElementById('statusBadge');
    const statusClass = `status-${info.status.toLowerCase()}`;
    const statusIcons = {
        'Normal': '🟢',
        'Attention': '🟡',
        'Warning': '🟠',
        'Critical': '🔴'
    };
    badge.innerHTML = `<span class="${statusClass}">${statusIcons[info.status] || '⚪'} ${info.status}</span>`;
    document.getElementById('healthScore').textContent = info.health + '%';
}

function updateSensors(data) {
    const latest = data.latest;
    const normal = data.normal_ranges;
    
    if (latest.temperature !== null) {
        document.getElementById('tempValue').textContent = latest.temperature + '°C';
        document.getElementById('tempNormal').textContent = `Normal: ${normal.temp_normal}°C`;
    }
    
    if (latest.vibration !== null) {
        document.getElementById('vibValue').textContent = latest.vibration + ' mm/s';
        document.getElementById('vibNormal').textContent = `Normal: ${normal.vib_normal} mm/s`;
    }
    
    if (latest.rpm !== null) {
        document.getElementById('rpmValue').textContent = latest.rpm + ' RPM';
        document.getElementById('rpmNormal').textContent = `Normal: ${normal.rpm_normal} RPM`;
    }
    
    if (latest.current !== null) {
        document.getElementById('currentValue').textContent = latest.current + ' A';
        document.getElementById('currentNormal').textContent = `Normal: ${normal.current_normal} A`;
    }
}

function updateAlerts(data) {
    const alertsList = document.getElementById('alertsList');
    const alerts = data.alerts || [];
    
    if (alerts.length === 0) {
        alertsList.innerHTML = '<div class="alert-item" style="border-color: #00ff88;"><span style="color: #00ff88;">✅ No active alerts</span></div>';
        return;
    }
    
    alertsList.innerHTML = alerts.slice(0, 5).map(alert => `
        <div class="alert-item level-${alert.level.toLowerCase()}">
            <div class="alert-issue">${alert.issue}</div>
            <div class="alert-action">🔧 ${alert.action}</div>
            <div class="alert-time">${alert.time}</div>
        </div>
    `).join('');
}

function updateMaintenance(data) {
    const maintenanceList = document.getElementById('maintenanceList');
    const maintenance = data.maintenance || [];
    
    if (maintenance.length === 0) {
        maintenanceList.innerHTML = '<div class="maintenance-item">No maintenance records</div>';
        return;
    }
    
    maintenanceList.innerHTML = maintenance.slice(0, 5).map(record => `
        <div class="maintenance-item">
            ${record.time}: ${record.issue}
        </div>
    `).join('');
}

function updateGauge(health) {
    const progress = document.getElementById('gaugeProgress');
    const circumference = 314.16;
    const offset = circumference - (health / 100) * circumference;
    progress.style.strokeDashoffset = offset;
    
    let color = '#00ff88';
    if (health < 40) color = '#ff4444';
    else if (health < 70) color = '#ffaa00';
    else if (health < 90) color = '#ff8800';
    progress.style.stroke = color;
}

function updateChart(data) {
    const history = data.history || [];
    const labels = history.map(r => r.time.substring(11, 16));
    const temps = history.map(r => r.temp);
    const vibs = history.map(r => r.vibration);
    const rpms = history.map(r => r.rpm);
    const currents = history.map(r => r.current);
    
    const ctx = document.getElementById('historyChart').getContext('2d');
    
    if (chartInstance) {
        chartInstance.destroy();
    }
    
    chartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Temperature',
                    data: temps,
                    borderColor: '#ff6b6b',
                    backgroundColor: 'rgba(255, 107, 107, 0.1)',
                    tension: 0.3,
                    pointRadius: 1,
                    borderWidth: 2
                },
                {
                    label: 'Vibration',
                    data: vibs,
                    borderColor: '#ffa94d',
                    backgroundColor: 'rgba(255, 169, 77, 0.1)',
                    tension: 0.3,
                    pointRadius: 1,
                    borderWidth: 2
                },
                {
                    label: 'RPM',
                    data: rpms,
                    borderColor: '#4dabf7',
                    backgroundColor: 'rgba(77, 171, 247, 0.1)',
                    tension: 0.3,
                    pointRadius: 1,
                    borderWidth: 2
                },
                {
                    label: 'Current',
                    data: currents,
                    borderColor: '#69db7c',
                    backgroundColor: 'rgba(105, 219, 124, 0.1)',
                    tension: 0.3,
                    pointRadius: 1,
                    borderWidth: 2
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                x: {
                    grid: {
                        color: '#1a3550',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#7a9bb5',
                        maxTicksLimit: 12
                    }
                },
                y: {
                    grid: {
                        color: '#1a3550',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#7a9bb5'
                    }
                }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            }
        }
    });
}

function loadHealthTrend(machineId) {
    fetch(`/api/machine/${machineId}/health-trend`)
        .then(res => res.json())
        .then(data => {
            const ctx = document.getElementById('healthTrendChart').getContext('2d');
            
            if (healthChartInstance) {
                healthChartInstance.destroy();
            }
            
            healthChartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.map(d => d.time.substring(11, 16)),
                    datasets: [{
                        label: 'Health Score',
                        data: data.map(d => d.health),
                        borderColor: '#00d4ff',
                        backgroundColor: 'rgba(0, 212, 255, 0.1)',
                        fill: true,
                        tension: 0.3,
                        pointRadius: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            labels: { color: '#7a9bb5' }
                        }
                    },
                    scales: {
                        x: {
                            grid: { color: '#1a3550' },
                            ticks: { color: '#7a9bb5' }
                        },
                        y: {
                            grid: { color: '#1a3550' },
                            ticks: { color: '#7a9bb5' },
                            min: 0,
                            max: 100
                        }
                    }
                }
            });
        })
        .catch(err => console.error('Error loading health trend:', err));
}

function refreshData() {
    loadDashboardSummary();
    loadMachine(currentMachine);
    const btn = document.querySelector('.refresh-btn');
    btn.style.transform = 'rotate(360deg)';
    setTimeout(() => {
        btn.style.transform = 'rotate(0deg)';
    }, 300);
}