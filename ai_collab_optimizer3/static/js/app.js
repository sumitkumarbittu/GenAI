// Main Application
class CollaborationOptimizer {
    constructor() {
        this.tasks = [];
        this.network = null;
        this.nodes = new vis.DataSet([]);
        this.edges = new vis.DataSet([]);
        
        this.initEventListeners();
        this.loadExampleData();
    }

    initEventListeners() {
        // File upload
        document.getElementById('fileInput').addEventListener('change', (e) => this.handleFileUpload(e));
        document.getElementById('loadExample').addEventListener('click', () => this.loadExampleData());
        
        // AI Panel Toggle
        const aiPanel = document.querySelector('.ai-panel');
        const toggleBtn = document.getElementById('toggleAIPanel');
        
        toggleBtn.addEventListener('click', (e) => {
            e.preventDefault();
            aiPanel.classList.toggle('expanded');
            // Update the icon based on panel state
            const icon = toggleBtn.querySelector('i');
            if (aiPanel.classList.contains('expanded')) {
                icon.classList.remove('bi-chevron-up');
                icon.classList.add('bi-chevron-down');
            } else {
                icon.classList.remove('bi-chevron-down');
                icon.classList.add('bi-chevron-up');
            }
        });

        // API Key
        document.getElementById('addApiKey').addEventListener('click', () => {
            const modal = new bootstrap.Modal(document.getElementById('apiKeyModal'));
            modal.show();
        });

        document.getElementById('saveApiKey').addEventListener('click', () => {
            const apiKey = document.getElementById('apiKeyInput').value;
            if (apiKey) {
                localStorage.setItem('gemini_api_key', apiKey);
                document.getElementById('apiKeyInput').value = '';
                bootstrap.Modal.getInstance(document.getElementById('apiKeyModal')).hide();
                this.showAISuggestions();
            }
        });

        // Fullscreen toggle
        document.getElementById('toggleFullscreen').addEventListener('click', () => {
            if (!document.fullscreenElement) {
                document.documentElement.requestFullscreen();
            } else {
                if (document.exitFullscreen) {
                    document.exitFullscreen();
                }
            }
        });
    }

    async handleFileUpload(event) {
        const file = event.target.files[0];
        if (!file) return;

        const text = await file.text();
        this.parseCSV(text);
    }

    parseCSV(csvText) {
        const results = Papa.parse(csvText, {
            header: true,
            skipEmptyLines: true,
            transform: (value) => value.trim()
        });

        if (results.errors.length > 0) {
            this.showError("Error parsing CSV file");
            return;
        }

        this.tasks = results.data.map(task => ({
            ...task,
            task_id: parseInt(task.task_id),
            estimated_time: parseInt(task.estimated_time) || 0,
            dependencies: task.dependencies ? task.dependencies.split(';').map(Number).filter(Boolean) : []
        }));

        this.updateUI();
    }

    loadExampleData() {
        const exampleData = `task_id,name,assigned_to,estimated_time,dependencies\n1,Design UI,Alice,5,\n2,Build Backend,Bob,8,1\n3,API Integration,Charlie,4,2\n4,Testing,Dave,3,2;3\n5,Documentation,Eve,2,3`;
        this.parseCSV(exampleData);
    }

    updateUI() {
        this.updateTaskList();
        this.updateGraph();
        this.analyzeBottlenecks();
    }

    updateTaskList() {
        const container = document.getElementById('tasksContainer');
        container.innerHTML = '';
        
        this.tasks.forEach(task => {
            const taskEl = document.createElement('div');
            taskEl.className = 'task-item';
            taskEl.innerHTML = `
                <span class="task-name">${task.name}</span>
                <span class="task-assignee">${task.assigned_to}</span>
                <span class="badge bg-secondary">${task.estimated_time}h</span>
            `;
            container.appendChild(taskEl);
        });

        document.getElementById('taskCount').textContent = this.tasks.length;
    }

    updateGraph() {
        const container = document.getElementById('graph-container');
        container.classList.add('visible');
        document.getElementById('noData').style.display = 'none';

        // Clear previous network
        if (this.network) {
            this.network.destroy();
        }

        // Create nodes and edges
        const nodes = this.tasks.map(task => ({
            id: task.task_id,
            label: `${task.task_id}: ${task.name}`,
            title: `Task: ${task.name}\nAssigned to: ${task.assigned_to}\nDuration: ${task.estimated_time}h`,
            color: this.getNodeColor(task),
            shape: 'box',
            margin: 10,
            font: { size: 12 }
        }));

        const edges = [];
        this.tasks.forEach(task => {
            task.dependencies.forEach(depId => {
                edges.push({
                    from: depId,
                    to: task.task_id,
                    arrows: 'to'
                });
            });
        });

        // Initialize network
        const data = {
            nodes: new vis.DataSet(nodes),
            edges: new vis.DataSet(edges)
        };

        const options = {
            layout: {
                hierarchical: {
                    direction: 'LR',
                    sortMethod: 'directed',
                    nodeSpacing: 150,
                    levelSeparation: 100
                }
            },
            physics: {
                hierarchicalRepulsion: {
                    nodeDistance: 120
                }
            },
            nodes: {
                shape: 'box',
                margin: 10,
                font: {
                    size: 12,
                    face: 'Arial'
                }
            },
            edges: {
                smooth: true,
                arrows: {
                    to: {
                        enabled: true,
                        scaleFactor: 0.5
                    }
                }
            }
        };

        this.network = new vis.Network(container, data, options);
    }

    analyzeBottlenecks() {
        // Simple bottleneck detection: tasks with multiple dependencies or long duration
        const bottlenecks = this.tasks.filter(task => 
            task.dependencies.length > 1 || task.estimated_time > 5
        );

        const container = document.getElementById('bottlenecksContainer');
        container.innerHTML = '';

        bottlenecks.forEach(task => {
            const bottleneckEl = document.createElement('div');
            bottleneckEl.className = 'bottleneck-item fade-in';
            bottleneckEl.innerHTML = `
                <strong>${task.name}</strong>
                <div class="small">${task.assigned_to} • ${task.estimated_time}h</div>
                <div class="small text-muted">Depends on: ${task.dependencies.join(', ') || 'None'}</div>
            `;
            container.appendChild(bottleneckEl);
        });

        document.getElementById('bottleneckCount').textContent = bottlenecks.length;
        
        // Always try to show AI suggestions (handling is done in the backend)
        this.showAISuggestions();
    }

    async showAISuggestions() {
        const container = document.getElementById('aiSuggestions');
        container.innerHTML = `
            <div class="text-center p-4">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2">Analyzing workflow with AI...</p>
            </div>`;
        
        // Ensure the panel is expanded when showing suggestions
        const aiPanel = document.querySelector('.ai-panel');
        aiPanel.classList.add('expanded');

        try {
            const bottlenecks = this.tasks.filter(task => task.dependencies.length > 1 || task.estimated_time > 5);
            
            if (bottlenecks.length === 0) {
                container.innerHTML = `
                    <div class="alert alert-info">
                        <i class="bi bi-info-circle"></i> 
                        No potential bottlenecks detected in the current workflow.
                    </div>
                `;
                return;
            }
            
            let suggestions = '<div class="suggestions-list">';
            suggestions += '<h6 class="mb-3">AI-Powered Optimization Suggestions</h6>';
            
            for (const task of bottlenecks.slice(0, 3)) { // Limit to top 3
                try {
                    const suggestion = await this.getAISuggestion(task);
                    suggestions += `
                        <div class="suggestion-item mb-3 p-2 border rounded">
                            <h6 class="mb-1">${task.name} (${task.assigned_to})</h6>
                            <div class="small text-muted mb-2">${task.estimated_time}h • Depends on: ${task.dependencies.length} tasks</div>
                            <div class="suggestion-text">${suggestion}</div>
                        </div>
                    `;
                } catch (error) {
                    console.error(`Error getting suggestion for task ${task.name}:`, error);
                    suggestions += `
                        <div class="alert alert-warning p-2 mb-2">
                            <i class="bi bi-exclamation-triangle"></i> 
                            Could not generate suggestion for ${task.name}
                        </div>
                    `;
                }
            }
            
            suggestions += '</div>';
            container.innerHTML = suggestions;
            
        } catch (error) {
            console.error('Error in showAISuggestions:', error);
            container.innerHTML = `
                <div class="alert alert-warning">
                    <i class="bi bi-exclamation-triangle"></i> 
                    Could not load AI suggestions. Please try again later.
                </div>
            `;
        }
    }

    async getAISuggestion(task) {
        try {
            // Show loading state
            const suggestionElement = document.getElementById(`suggestion-${task.id}`);
            if (suggestionElement) {
                suggestionElement.innerHTML = `
                    <div class="d-flex align-items-center text-muted">
                        <div class="spinner-border spinner-border-sm me-2" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        Analyzing task...
                    </div>`;
            }

            const response = await fetch('/api/ai/suggest', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    task_name: task.name,
                    assigned_to: task.assigned_to,
                    estimated_time: task.estimated_time,
                    dependencies: task.dependencies
                })
            });

            const data = await response.json();

            if (!response.ok) {
                console.error('API Error:', data);
                
                // Handle specific error cases
                if (data.message?.includes('quota') || data.message?.includes('billing')) {
                    return `⚠️ API quota exceeded. Please check your Google AI Studio billing.`;
                } else if (data.message?.includes('API key')) {
                    return `🔑 API key not configured. Please set GEMINI_API_KEY in .env file.`;
                } else {
                    return `❌ Error: ${data.message || 'Failed to get suggestion'}`;
                }
            }

            return data.suggestion || 'No suggestion available';
            
        } catch (error) {
            console.error('Error getting AI suggestion:', error);
            return '⚠️ Error connecting to the server. Please try again later.';
        }
    }

    getNodeColor(task) {
        if (task.dependencies.length > 1) {
            return { background: '#f8d7da', border: '#f5c6cb' }; // Red for bottlenecks
        } else if (task.estimated_time > 5) {
            return { background: '#fff3cd', border: '#ffeeba' }; // Yellow for long tasks
        } else {
            return { background: '#d4edda', border: '#c3e6cb' }; // Green for normal tasks
        }
    }

    showError(message) {
        // Show error message in UI
        const alert = document.createElement('div');
        alert.className = 'alert alert-danger alert-dismissible fade show';
        alert.role = 'alert';
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        const container = document.querySelector('.main-content');
        container.prepend(alert);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            alert.remove();
        }, 5000);
    }
}

// Initialize the application when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new CollaborationOptimizer();
});
