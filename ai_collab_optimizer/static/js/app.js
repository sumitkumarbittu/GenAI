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
        
        // Layout controls
        const hierarchicalToggle = document.getElementById('hierarchicalToggle');
        const layoutDirection = document.getElementById('layoutDirection');
        const layoutSpacing = document.getElementById('layoutSpacing');
        const spacingValue = document.getElementById('spacingValue');
        
        // Update spacing value display
        if (layoutSpacing && spacingValue) {
            layoutSpacing.addEventListener('input', () => {
                spacingValue.textContent = `${layoutSpacing.value}px`;
                this.updateLayout();
            });
        }
        
        // Toggle hierarchical layout
        if (hierarchicalToggle) {
            hierarchicalToggle.addEventListener('change', () => {
                this.updateLayout();
            });
        }
        
        // Change layout direction
        if (layoutDirection) {
            layoutDirection.addEventListener('change', () => {
                this.updateLayout();
            });
        }
        
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
        // Reset tasks
        this.tasks = [];
        
        try {
            console.log('=== STARTING CSV PARSING ===');
            
            // First, do a quick validation of the CSV content
            if (!csvText || typeof csvText !== 'string') {
                throw new Error('Invalid CSV content');
            }
            
            // Parse CSV with PapaParse
            const results = Papa.parse(csvText, {
                header: true,
                skipEmptyLines: true
            });
            
            // Log parsing results
            console.log('CSV parse results:', {
                meta: results.meta,
                errors: results.errors,
                rowCount: results.data ? results.data.length : 0
            });
            
            // Handle parsing errors
            if (results.errors && results.errors.length > 0) {
                throw new Error(`CSV parsing error: ${results.errors[0].message}`);
            }
            
            if (!results.data || !Array.isArray(results.data)) {
                throw new Error('Invalid CSV format: No data found');
            }
            
            // Process each row
            results.data.forEach((row, index) => {
                try {
                    // Skip empty rows
                    if (!row || Object.keys(row).length === 0) return;
                    
                    // Extract task ID
                    const taskId = parseInt(row['Task ID'] || row.task_id || (index + 1));
                    if (isNaN(taskId)) {
                        console.warn(`Skipping row ${index + 1}: Invalid task ID`);
                        return;
                    }
                    
                    // Extract duration (convert days to hours)
                    let duration = 0;
                    const durationStr = row['Duration (days)'] || row.estimated_time || row.duration || '0';
                    try {
                        duration = Math.max(1, Math.floor(parseFloat(durationStr) * 8));
                    } catch (e) {
                        console.warn(`Invalid duration for task ${taskId}, using default`);
                        duration = 8; // Default to 1 day if parsing fails
                    }
                    
                    // Create task object
                    const task = {
                        task_id: taskId,
                        name: row['Task Name'] || row.name || `Task ${taskId}`,
                        assigned_to: row.Resource || row.assigned_to || 'Unassigned',
                        estimated_time: duration,
                        dependencies: []
                    };
                    
                    // Parse dependencies
                    const deps = row.Dependencies || row.dependencies || '';
                    if (deps && typeof deps === 'string') {
                        task.dependencies = deps.split(/[,;]/)
                            .map(d => parseInt(d.trim()))
                            .filter(id => !isNaN(id) && id > 0);
                    }
                    
                    console.log('Parsed task:', task);
                    this.tasks.push(task);
                    
                } catch (e) {
                    console.error(`Error processing row ${index + 1}:`, e, row);
                }
            });
            
            // Final validation
            if (this.tasks.length === 0) {
                throw new Error('No valid tasks found in the CSV file');
            }
            
            console.log(`Successfully parsed ${this.tasks.length} tasks`);
            
        } catch (error) {
            console.error('Failed to parse CSV:', error);
            this.showError(`Error: ${error.message || 'Failed to process CSV file'}`);
            this.tasks = [];
        } finally {
            // Always update UI, even if there was an error
            this.updateUI();
        }
    }

    loadExampleData() {
        const exampleData = `Task ID,Task Name,Duration (days),Dependencies,Resource\n1,Project Start,0,,Project Manager\n2,Design Phase,5,1,Design Team\n3,Frontend Development,8,2,Frontend Team\n4,Backend Development,10,2,Backend Team\n5,API Integration,5,"3,4",Full Stack Team\n6,Testing,4,5,QA Team\n7,Documentation,3,5,Technical Writer\n8,Deployment,2,"6,7",DevOps`;
        this.parseCSV(exampleData);
    }

    updateUI() {
        try {
            console.log('Updating UI...');
            this.updateTaskList();
            this.updateGraph();
            this.analyzeBottlenecks();
            
            // Update the task count
            const taskCount = this.tasks.length;
            document.getElementById('taskCount').textContent = taskCount;
            console.log('UI update complete');
        } catch (error) {
            console.error('Error updating UI:', error);
            this.showError(`UI update failed: ${error.message}`);
        }
    }
    
    // Highlight a task in the UI
    highlightTask(taskId, highlight = true) {
        // Highlight in task list
        const taskElements = document.querySelectorAll('.task-item');
        taskElements.forEach(el => {
            if (parseInt(el.dataset.taskId) === taskId) {
                el.classList.toggle('highlighted', highlight);
            } else if (highlight) {
                el.classList.remove('highlighted');
            }
        });
        
        // Highlight in graph
        if (this.network) {
            const nodeId = this.tasks.findIndex(t => t.task_id === taskId) + 1;
            if (nodeId > 0) {
                const options = {
                    nodes: {
                        borderWidth: highlight ? 3 : 1,
                        borderWidthSelected: highlight ? 5 : 2,
                        color: {
                            border: highlight ? '#0d6efd' : '#2B7CE9',
                            background: highlight ? '#D2E5FF' : '#97C2FC',
                            highlight: {
                                border: highlight ? '#0d6efd' : '#2B7CE9',
                                background: highlight ? '#D2E5FF' : '#97C2FC'
                            }
                        }
                    }
                };
                this.network.selectNodes([nodeId]);
                this.network.setOptions(options);
                
                // Scroll to the node if possible
                this.network.focus(nodeId, {
                    scale: 0.8,
                    animation: {
                        duration: 1000,
                        easingFunction: 'easeInOutQuad'
                    }
                });
            }
        }
    }
    
    // Update the critical tasks count in the UI
    updateCriticalTasksCount(count) {
        const criticalCountElement = document.getElementById('criticalTasksCount');
        if (criticalCountElement) {
            criticalCountElement.textContent = count;
            
            // Update the label style based on count
            const label = criticalCountElement.closest('.badge');
            if (label) {
                if (count === 0) {
                    label.classList.remove('bg-danger');
                    label.classList.add('bg-secondary');
                } else {
                    label.classList.remove('bg-secondary');
                    label.classList.add('bg-danger');
                }
            }
        }
    }
    
    updateCriticalPathDisplay(criticalPath) {
        const container = document.getElementById('criticalPathContainer');
        if (!container) {
            console.error('Critical path container not found');
            return;
        }
        
        if (!criticalPath || criticalPath.length === 0) {
            container.innerHTML = `
                <div class="alert alert-warning">
                    <i class="bi bi-exclamation-triangle-fill me-2"></i>
                    No critical path found. Check task dependencies and durations.
                </div>`;
            return;
        }
        
        // Store critical path for later reference
        this.criticalPath = criticalPath;
        
        // Calculate total duration
        const totalDuration = criticalPath.reduce((sum, task) => sum + (parseFloat(task.estimated_time) || 0), 0);
        
        // Create the critical path HTML
        let html = `
        <div class="card border-0 shadow-sm mb-4">
            <div class="card-header bg-white d-flex justify-content-between align-items-center">
                <h5 class="mb-0">
                    <i class="bi bi-lightning-charge-fill text-warning me-2"></i>
                    Critical Path
                    <small class="text-muted ms-2">(click tasks to highlight)</small>
                </h5>
                <span class="badge bg-danger">
                    <i class="bi bi-clock-history me-1"></i>
                    ${Math.ceil(totalDuration/8)} days (${totalDuration} hours)
                </span>
            </div>
            <div class="card-body p-0">
                <div class="path-timeline p-3">`;
        
        // Add each task in the critical path
        criticalPath.forEach((task, index) => {
            const taskDuration = parseFloat(task.estimated_time) || 0;
            const days = taskDuration / 8; // Convert hours to days (assuming 8h/day)
            
            html += `
                    <div class="path-task" 
                         data-task-id="${task.task_id}" 
                         data-bs-toggle="tooltip" 
                         title="Click to highlight in graph">
                        <div class="task-header">
                            <span class="task-name">
                                <i class="bi bi-${task.is_milestone ? 'flag-fill text-primary' : 'card-checklist'}"></i>
                                ${task.name}
                            </span>
                            <span class="badge bg-light text-dark">#${task.task_id}</span>
                        </div>
                        <div class="task-details">
                            <span class="task-meta">
                                <i class="bi bi-clock"></i>
                                ${days.toFixed(1)} days (${taskDuration}h)
                            </span>
                            <span class="task-meta">
                                <i class="bi bi-people"></i>
                                ${task.assigned_to || 'Unassigned'}
                            </span>
                            ${task.status === 'Completed' ? `
                            <span class="badge bg-success">
                                <i class="bi bi-check-circle-fill me-1"></i> Completed
                            </span>` : ''}
                        </div>
                    </div>`;
        });
        
        html += `
                </div>
            </div>
        </div>`;
        
        container.innerHTML = html;
        
        // Initialize tooltips
        const tooltipTriggerList = [].slice.call(container.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
        
        // Add event listeners to critical path items
        container.querySelectorAll('.path-task').forEach(item => {
            // Click to highlight task in graph
            item.addEventListener('click', (e) => {
                const taskId = item.getAttribute('data-task-id');
                this.highlightTaskInGraph(taskId, true);
                
                // Toggle highlight class on the clicked item
                container.querySelectorAll('.path-task').forEach(i => i.classList.remove('highlighted'));
                item.classList.add('highlighted');
                
                // Clear timeout if user hovers over the item
                item.addEventListener('mouseenter', () => clearTimeout(timeout), { once: true });
            });
            
            // Highlight on hover
            item.addEventListener('mouseenter', () => {
                this.highlightTask(taskId, true);
            });
            
            // Remove highlight when mouse leaves
            item.addEventListener('mouseleave', () => {
                this.highlightTask(taskId, false);
            });
        });
        
        // Clicking anywhere else removes highlights
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.path-item')) {
                this.highlightTask(null, false);
            }
        });
    }

    updateTaskList() {
        const container = document.getElementById('tasksContainer');
        container.innerHTML = '';
        
        this.tasks.forEach(task => {
            const taskEl = document.createElement('div');
            taskEl.className = 'task-item';
            taskEl.dataset.taskId = task.task_id;
            taskEl.innerHTML = `
                <span class="task-name">${task.name}</span>
                <span class="task-assignee">${task.assigned_to}</span>
                <span class="badge bg-secondary">${task.estimated_time}h</span>
            `;
            container.appendChild(taskEl);
        });

        document.getElementById('taskCount').textContent = this.tasks.length;
    }

    // Enhanced critical path finder
    findCriticalPath() {
        console.log('=== FINDING CRITICAL PATH ===');
        
        if (!this.tasks || this.tasks.length === 0) {
            console.warn('No tasks available for critical path analysis');
            return [];
        }
        
        // Create a map of task IDs to tasks for easier lookup
        const taskMap = new Map(this.tasks.map(task => [task.task_id, task]));
        
        // Find all end nodes (tasks that no other task depends on)
        const endTasks = this.tasks.filter(task => {
            return !this.tasks.some(t => t.dependencies.includes(task.task_id));
        });
        
        console.log(`Found ${endTasks.length} end tasks:`, endTasks.map(t => t.task_id));
        
        // If no end tasks found, use all tasks as potential end points
        const targetTasks = endTasks.length > 0 ? endTasks : this.tasks;
        
        let longestPath = [];
        let maxDuration = 0;
        
        // Find the longest path to each end task
        for (const endTask of targetTasks) {
            const path = this.findLongestPathToTask(endTask, taskMap);
            const pathDuration = path.reduce((sum, task) => sum + task.estimated_time, 0);
            
            if (pathDuration > maxDuration) {
                maxDuration = pathDuration;
                longestPath = path;
            }
        }
        
        console.log(`Longest path found with duration: ${maxDuration/8} days (${maxDuration} hours)`);
        console.log('Critical path tasks:', longestPath.map(t => t.task_id));
        
        return longestPath;
    }
    
    // Helper method to find the longest path to a specific task
    findLongestPathToTask(task, taskMap, visited = new Set(), path = []) {
        const taskId = task.task_id;
        
        // Check for cycles
        if (visited.has(taskId)) {
            console.warn(`Cycle detected at task ${taskId}, path so far:`, path.map(t => t.task_id));
            return [...path];
        }
        
        visited.add(taskId);
        path.push(task);
        
        let longestPath = [...path];
        let maxDuration = longestPath.reduce((sum, t) => sum + t.estimated_time, 0);
        
        // Get all dependencies of this task
        const dependencies = (task.dependencies || [])
            .map(id => taskMap.get(id))
            .filter(Boolean);
        
        // If no dependencies, this is a start node
        if (dependencies.length === 0) {
            visited.delete(taskId);
            return path;
        }
        
        // Find the longest path from all dependencies
        for (const dep of dependencies) {
            const currentPath = this.findLongestPathToTask(dep, taskMap, new Set(visited), [...path]);
            const currentDuration = currentPath.reduce((sum, t) => sum + t.estimated_time, 0);
            
            if (currentDuration > maxDuration) {
                maxDuration = currentDuration;
                longestPath = currentPath;
            }
        }
        
        visited.delete(taskId);
        return longestPath;
    }
    
    updateGraph() {
        const container = document.getElementById('graph-container');
        if (!container) {
            console.error('Graph container not found');
            return;
        }
        
        container.classList.add('visible');
        const noDataElement = document.getElementById('noData');
        if (noDataElement) {
            noDataElement.style.display = 'none';
        }

        // Clear previous network
        if (this.network) {
            this.network.destroy();
            this.network = null;
        }
        
        // Clear existing nodes and edges
        this.nodes.clear();
        this.edges.clear();
        
        // Add nodes
        const nodeData = this.tasks.map(task => ({
            id: task.task_id,
            label: task.name,
            title: `${task.name}\nAssigned to: ${task.assigned_to}\nDuration: ${task.estimated_time}h`,
            color: this.getNodeColor(task),
            margin: 10,
            shape: 'box',
            font: { size: 12 }
        }));
        
        if (nodeData.length > 0) {
            this.nodes.update(nodeData);
            
            // Add edges
            const edgeData = [];
            this.tasks.forEach(task => {
                if (task.dependencies && task.dependencies.length > 0) {
                    task.dependencies.forEach(depId => {
                        edgeData.push({
                            from: depId,
                            to: task.task_id,
                            arrows: 'to',
                            smooth: {
                                type: 'cubicBezier',
                                forceDirection: 'horizontal',
                                roundness: 0.4
                            }
                        });
                    });
                }
            });
            
            if (edgeData.length > 0) {
                this.edges.update(edgeData);
            }
            
            // Initialize network
            this.initNetwork();
        } else {
            if (noDataElement) {
                noDataElement.style.display = 'block';
            }
        }
    }

    updateLayout() {
        if (!this.network) return;
        
        const hierarchicalToggle = document.getElementById('hierarchicalToggle');
        const layoutDirection = document.getElementById('layoutDirection');
        const layoutSpacing = document.getElementById('layoutSpacing');
        
        const isHierarchical = hierarchicalToggle ? hierarchicalToggle.checked : false;
        const direction = layoutDirection ? layoutDirection.value : 'LR';
        const spacing = layoutSpacing ? parseInt(layoutSpacing.value) : 150;
        
        const options = {
            layout: {
                hierarchical: {
                    enabled: isHierarchical,
                    direction: direction,
                    nodeSpacing: spacing,
                    levelSeparation: spacing,
                    sortMethod: 'directed',
                    shakeTowards: 'roots',
                    parentCentralization: true
                }
            },
            physics: {
                enabled: true,
                hierarchical: {
                    enabled: isHierarchical,
                    direction: direction,
                    nodeSpacing: spacing,
                    levelSeparation: spacing,
                    sortMethod: 'directed',
                    shakeTowards: 'roots',
                    parentCentralization: true
                },
                solver: isHierarchical ? 'hierarchicalRepulsion' : 'forceAtlas2Based',
                forceAtlas2Based: {
                    gravitationalConstant: -50,
                    centralGravity: 0.01,
                    springLength: 100,
                    springConstant: 0.08,
                    nodeDistance: spacing,
                    damping: 0.4
                },
                minVelocity: 0.75,
                maxVelocity: 50,
                stabilization: {
                    enabled: true,
                    iterations: 1000,
                    updateInterval: 25,
                    onlyDynamicEdges: false,
                    fit: true
                },
                timestep: 0.5
            }
        };
        
        this.network.setOptions(options);
        
        // If switching to hierarchical, stabilize the layout
        if (isHierarchical) {
            this.network.stabilize();
        }
    }
    
    initNetwork() {
        const container = document.getElementById('graph-container');
        if (!container) {
            console.error('Graph container not found');
            return;
        }
        
        const data = {
            nodes: this.nodes,
            edges: this.edges
        };
        
        // Get initial layout settings
        const hierarchicalToggle = document.getElementById('hierarchicalToggle');
        const layoutDirection = document.getElementById('layoutDirection');
        const layoutSpacing = document.getElementById('layoutSpacing');
        
        const isHierarchical = hierarchicalToggle ? hierarchicalToggle.checked : false;
        const direction = layoutDirection ? layoutDirection.value : 'LR';
        const spacing = layoutSpacing ? parseInt(layoutSpacing.value) : 150;
        
        const options = {
            nodes: {
                shape: 'box',
                margin: 10,
                widthConstraint: {
                    minimum: 100,
                    maximum: 200
                },
                font: {
                    size: 12,
                    face: 'Roboto, sans-serif',
                    color: '#2B2B2B'
                },
                heightConstraint: {
                    minimum: 50,
                    valign: 'middle'
                },
                font: {
                    size: 12
                },
                borderWidth: 1,
                shadow: true,
                color: {
                    border: '#2B7CE9',
                    background: '#D2E5FF',
                    highlight: {
                        border: '#2B7CE9',
                        background: '#D2E5FF'
                    },
                    hover: {
                        border: '#2B7CE9',
                        background: '#D2E5FF'
                    }
                }
            },
            edges: {
                arrows: 'to',
                smooth: {
                    type: 'cubicBezier',
                    forceDirection: 'horizontal',
                    roundness: 0.4
                },
                color: {
                    color: '#848484',
                    highlight: '#ff7800',
                    hover: '#ff7800',
                    inherit: 'from',
                    opacity: 0.8
                },
                width: 2,
                selectionWidth: 3
            },
            physics: {
                enabled: true,
                hierarchical: {
                    enabled: isHierarchical,
                    direction: direction,
                    sortMethod: 'directed',
                    nodeSpacing: spacing,
                    levelSeparation: spacing,
                    shakeTowards: 'roots',
                    parentCentralization: true
                },
                solver: 'forceAtlas2Based',
                forceAtlas2Based: {
                    gravitationalConstant: -50,
                    centralGravity: 0.01,
                    springLength: 100,
                    springConstant: 0.08,
                    nodeDistance: 120,
                    damping: 0.4
                },
                minVelocity: 0.75,
                maxVelocity: 50,
                stabilization: {
                    enabled: true,
                    iterations: 1000,
                    updateInterval: 25,
                    onlyDynamicEdges: false,
                    fit: true
                },
                timestep: 0.5
            },
            layout: {
                hierarchical: {
                    enabled: isHierarchical,
                    direction: direction,
                    nodeSpacing: spacing,
                    levelSeparation: spacing,
                    sortMethod: 'directed',
                    shakeTowards: 'roots',
                    parentCentralization: true
                }
            },
            interaction: {
                dragNodes: true,
                dragView: true,
                zoomView: true,
                tooltipDelay: 200,
                hideEdgesOnDrag: false,
                hideEdgesOnZoom: false,
                multiselect: false,
                selectable: true,
                selectConnectedEdges: true
            },
            manipulation: {
                enabled: false // We'll handle interactions manually
            }
        };

        this.network = new vis.Network(container, data, options);
        
        // Show/hide no data message based on node count
        this.network.on('stabilizationIterationsDone', () => {
            const noDataElement = document.getElementById('noData');
            if (noDataElement) {
                noDataElement.style.display = 'none';
            }
        });

        // Add click handler for nodes
        this.network.on('click', (params) => this.handleNodeClick(params));

        // Add double click handler for nodes to center view
        this.network.on('doubleClick', (params) => {
            if (params.nodes.length > 0) {
                this.network.focus(params.nodes[0], {
                    scale: 1.2,
                    animation: {
                        duration: 1000,
                        easingFunction: 'easeInOutQuad'
                    }
                });
            }
        });
    }

    analyzeBottlenecks() {
        console.log('=== ANALYZING BOTTLENECKS ===');
        console.log('Total tasks:', this.tasks.length);
        
        // First, identify critical path
        try {
            console.log('Finding critical path...');
            const criticalPath = this.findCriticalPath();
            console.log('Critical Path:', criticalPath);
            
            if (criticalPath.length === 0) {
                console.warn('No critical path found. Possible issues:');
                console.log('- No tasks with dependencies');
                console.log('- Tasks might not be properly connected');
                console.log('- Check if any task has a valid duration > 0');
                
                // Log task details for debugging
                console.log('Task details:');
                this.tasks.forEach(task => {
                    console.log(`- Task ${task.task_id}: '${task.name}', ` +
                                `Duration: ${task.estimated_time}h, ` +
                                `Dependencies: [${task.dependencies ? task.dependencies.join(', ') : 'none'}]`);
                });
                
                // If no critical path found but we have tasks, use the longest task as critical
                if (this.tasks.length > 0) {
                    console.log('Using longest task as critical path');
                    const longestTask = this.tasks.reduce((longest, task) => 
                        (!longest || task.estimated_time > longest.estimated_time) ? task : longest, null);
                    
                    if (longestTask) {
                        longestTask.is_critical = true;
                        this.updateCriticalPathDisplay([longestTask]);
                        this.updateCriticalTasksCount(1);
                        return;
                    }
                }
                
                // If we still don't have a critical path, show a message
                this.updateCriticalPathDisplay([]);
                this.updateCriticalTasksCount(0);
                return;
            }
            
            // Mark critical tasks
            this.tasks.forEach(task => {
                task.is_critical = criticalPath.some(t => t.task_id === task.task_id);
                if (task.is_critical) {
                    console.log(`Task ${task.task_id} is on the critical path`);
                }
            });
            
            // Update the critical path display and count
            this.updateCriticalPathDisplay(criticalPath);
            this.updateCriticalTasksCount(criticalPath.length);
            
        } catch (error) {
            console.error('Error in critical path analysis:', error);
            this.showError(`Critical path error: ${error.message}`);
            this.updateCriticalTasksCount(0);
        }
        
        // Simple bottleneck detection: tasks with multiple dependencies or long duration
        const bottlenecks = this.tasks.filter(task => {
            const isBottleneck = task.dependencies.length > 1 || task.estimated_time > 5 * 8; // > 5 days in hours
            if (isBottleneck) {
                console.log(`Bottleneck found: ${task.name} (ID: ${task.task_id})`);
                console.log(`  Dependencies: ${task.dependencies.length}, Duration: ${task.estimated_time/8} days`);
            }
            return isBottleneck;
        });

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

    async getAISuggestion(task) {
        try {
            const response = await fetch('/api/ai/suggest', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    prompt: `Provide optimization suggestions for task: ${task.name} (${task.assigned_to})`,
                    context: {
                        task: task,
                        taskList: this.tasks
                    }
                })
            });

            if (!response.ok) {
                throw new Error('Failed to get AI suggestion');
            }

            const data = await response.json();
            return data.suggestion || 'No specific suggestions available for this task.';
            
        } catch (error) {
            console.error('Error getting AI suggestion:', error);
            throw error;
        }
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
            };

            container.innerHTML = suggestions + '</div>';
        } catch (error) {
            console.error('Error in showAISuggestions:', error);
            container.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle"></i>
                    Failed to load AI suggestions. Please try again later.
                </div>`;
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
        if (container) {
            container.prepend(alert);
            
            // Auto-remove after 5 seconds
            setTimeout(() => {
                if (alert && alert.parentNode) {
                    alert.remove();
                }
            }, 5000);
        }
    }

    // Handle node click events
    handleNodeClick(params) {
        if (!params || !params.nodes || !params.nodes.length) return;
        
        const nodeId = params.nodes[0];
        const node = this.nodes.get(nodeId);
        if (!node) return;
        
        // Find the task in our tasks array
        const task = this.tasks.find(t => t.task_id == nodeId);
        if (task) {
            this.showEditModal(task);
        }
    }
    
    // Show the edit modal with task data
    showEditModal(task) {
        if (!task) return;
        
        const elements = {
            taskName: document.getElementById('taskName'),
            assignedTo: document.getElementById('assignedTo'),
            estimatedTime: document.getElementById('estimatedTime'),
            taskDependencies: document.getElementById('taskDependencies'),
            modal: document.getElementById('taskModal')
        };
        
        if (elements.taskName) elements.taskName.value = task.name || '';
        if (elements.assignedTo) elements.assignedTo.value = task.assigned_to || '';
        if (elements.estimatedTime) elements.estimatedTime.value = task.estimated_time || 0;
        if (elements.taskDependencies) {
            elements.taskDependencies.value = Array.isArray(task.dependencies) ? 
                task.dependencies.join(', ') : '';
        }
        
        this.currentTaskId = task.task_id;
        
        if (elements.modal) {
            new bootstrap.Modal(elements.modal).show();
        }
    }
    
    // Save task changes
    saveTask() {
        const taskId = this.currentTaskId;
        if (!taskId) return;
        
        const elements = {
            taskName: document.getElementById('taskName'),
            assignedTo: document.getElementById('assignedTo'),
            estimatedTime: document.getElementById('estimatedTime'),
            taskDependencies: document.getElementById('taskDependencies'),
            modal: document.getElementById('taskModal')
        };
        
        const updatedTask = {
            task_id: taskId,
            name: elements.taskName?.value || '',
            assigned_to: elements.assignedTo?.value || '',
            estimated_time: parseInt(elements.estimatedTime?.value) || 0,
            dependencies: (elements.taskDependencies?.value || '')
                .split(',')
                .map(id => id.trim())
                .filter(id => id && !isNaN(id))
        };
        
        try {
            const taskIndex = this.tasks.findIndex(t => t.task_id == taskId);
            if (taskIndex === -1) return;
            
            // Update task
            this.tasks[taskIndex] = { ...this.tasks[taskIndex], ...updatedTask };
            
            // Update network node
            if (this.nodes?.update) {
                this.nodes.update({
                    id: taskId,
                    label: updatedTask.name,
                    title: `${updatedTask.name}\nAssigned to: ${updatedTask.assigned_to}\nDuration: ${updatedTask.estimated_time}h`
                });
            }
            
            // Update UI
            this.updateTaskList?.();
            this.analyzeBottlenecks?.();
            this.showToast('Task updated successfully', 'success');
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(elements.modal);
            modal?.hide();
            
        } catch (error) {
            console.error('Error updating task:', error);
            this.showToast(`Error: ${error.message || 'Failed to update task'}`, 'danger');
        }
    }
    
    // Show a toast notification
    showToast(message, type) {
        type = type || 'info';
        var toastContainer = document.getElementById('toastContainer') || document.body;
        
        var toastId = 'toast-' + Date.now();
        var toastHtml = [
            '<div id="' + toastId + '" class="toast align-items-center text-white bg-' + type + ' border-0" role="alert" aria-live="assertive" aria-atomic="true">',
            '    <div class="d-flex">',
            '        <div class="toast-body">',
            '            ' + message,
            '        </div>',
            '        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>',
            '    </div>',
            '</div>'
        ].join('\n');
        
        // Add the toast to the container
        var toastElement = document.createElement('div');
        toastElement.innerHTML = toastHtml;
        var toastNode = toastElement.firstElementChild;
        
        // Make sure toast container exists
        if (toastContainer) {
            toastContainer.appendChild(toastNode);
            
            // Initialize and show the toast
            if (window.bootstrap && window.bootstrap.Toast) {
                var toast = new bootstrap.Toast(toastNode, {
                    autohide: true,
                    delay: 3000
                });
                
                toast.show();
                
                // Remove the toast after it's hidden
                toastNode.addEventListener('hidden.bs.toast', function() {
                    if (toastNode && toastNode.parentNode) {
                        toastNode.parentNode.removeChild(toastNode);
                    }
                });
            }
        }
    }

} // End of CollaborationOptimizer class

// Initialize the application when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize the app
    window.app = new CollaborationOptimizer();
    
    // Add event listener for the save task button
    var saveButton = document.getElementById('saveTask');
    if (saveButton) {
        saveButton.addEventListener('click', function() {
            if (window.app && typeof window.app.saveTask === 'function') {
                window.app.saveTask();
            }
        });
    }
});
