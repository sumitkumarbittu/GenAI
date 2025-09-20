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
        
        // AI Panel
        document.getElementById('toggleAIPanel').addEventListener('click', () => {
            document.querySelector('.ai-panel').classList.toggle('collapsed');
        });

        // API Key
        document.getElementById('addApiKey').addEventListener('click', () => {
            const modal = new bootstrap.Modal(document.getElementById('apiKeyModal'));
            modal.show();
        });

        document.getElementById('saveApiKey').addEventListener('click', () => {
            const apiKey = document.getElementById('apiKeyInput').value;
            if (apiKey) {
                localStorage.setItem('openai_api_key', apiKey);
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
        
        // Show AI suggestions if API key is available
        if (localStorage.getItem('openai_api_key')) {
            this.showAISuggestions();
        }
    }

    async showAISuggestions() {
        const container = document.getElementById('aiSuggestions');
        container.innerHTML = '<div class="text-center p-4"><div class="spinner-border text-primary" role="status"></div><p class="mt-2">Analyzing workflow...</p></div>';

        try {
            const bottlenecks = this.tasks.filter(task => task.dependencies.length > 1 || task.estimated_time > 5);
            let suggestions = '<div class="suggestions-list">';
            
            for (const task of bottlenecks.slice(0, 3)) { // Limit to top 3
                const suggestion = await this.getAISuggestion(task);
                suggestions += `
                    <div class="suggestion-item mb-3">
                        <h6>${task.name} (${task.assigned_to})</h6>
                        <div class="suggestion-text">${suggestion}</div>
                    </div>
                `;
            }
            
            suggestions += '</div>';
            container.innerHTML = suggestions;
        } catch (error) {
            container.innerHTML = `
                <div class="alert alert-warning">
                    <i class="bi bi-exclamation-triangle"></i> 
                    Could not load AI suggestions. Please check your API key and internet connection.
                </div>
            `;
        }
    }

    async getAISuggestion(task) {
        const apiKey = localStorage.getItem('openai_api_key');
        if (!apiKey) return 'API key not found';

        const prompt = `Task '${task.name}' assigned to ${task.assigned_to} is a potential bottleneck in a project. 
        It takes ${task.estimated_time} hours and has ${task.dependencies.length} dependencies. 
        Suggest 2-3 actionable ways to optimize this.`;

        try {
            const response = await fetch('https://api.openai.com/v1/chat/completions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${apiKey}`
                },
                body: JSON.stringify({
                    model: 'gpt-3.5-turbo',
                    messages: [{ role: 'user', content: prompt }],
                    max_tokens: 150
                })
            });

            const data = await response.json();
            return data.choices?.[0]?.message?.content || 'No suggestion available';
        } catch (error) {
            console.error('Error getting AI suggestion:', error);
            return 'Error getting suggestion';
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
