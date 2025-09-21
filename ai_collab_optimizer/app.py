"""
AI-Powered Project Management and Optimization Tool

This is a consolidated version of the application that includes all functionality
from the ai_utils modules in a single file.
"""

# Standard library imports
import os
import json
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Tuple, Set, Optional, Any, Union
from collections import defaultdict

# Third-party imports
from flask import Flask, render_template, request, jsonify, send_from_directory
import pandas as pd
import networkx as nx
import numpy as np
import plotly
import plotly.graph_objects as go
import google.generativeai as genai
from dotenv import load_dotenv

# =============================================================================
# Critical Path Analyzer
# =============================================================================

class CriticalPathAnalyzer:
    """A class to analyze project workflows and identify critical paths and bottlenecks."""
    
    def __init__(self, tasks: List[Dict]):
        """
        Initialize the analyzer with a list of tasks.
        
        Args:
            tasks: List of task dictionaries with at least 'id', 'duration', and 'dependencies' keys.
        """
        self.tasks = tasks
        self.graph = self._build_dependency_graph()
        self.forward_pass()
        self.backward_pass()
        
    def _build_dependency_graph(self) -> nx.DiGraph:
        """Build a directed graph from the task dependencies."""
        G = nx.DiGraph()
        
        if not self.tasks:
            return G
            
        # Add nodes with task data
        for task in self.tasks:
            # Support both old and new column names
            task_id = str(task.get('Task ID', task.get('task_id', ''))).strip()
            if not task_id:
                continue
                
            # Get task name with fallback to task_id
            task_name = task.get('Task Name', task.get('task_name', f'Task {task_id}'))
            
            # Get duration (convert from days to hours if needed)
            duration_days = float(task.get('Duration (days)', task.get('duration', task.get('estimated_time', 0))))
            
            # If duration is in days (likely from new format), convert to hours (assuming 8-hour workdays)
            if 'Duration (days)' in task or 'duration' in task:
                duration = int(duration_days * 8)  # Convert days to hours
            else:
                duration = int(duration_days)  # Already in hours
                
            G.add_node(task_id, 
                      name=task_name,
                      duration=max(1, duration),  # Ensure minimum duration of 1 hour
                      resource=task.get('Resource', task.get('assigned_to', 'Unassigned')),
                      early_start=0,
                      early_finish=0,
                      late_start=float('inf'),
                      late_finish=float('inf'),
                      slack=0,
                      is_critical=False)
        
        # Add edges for dependencies
        for task in self.tasks:
            task_id = str(task.get('Task ID', task.get('task_id', ''))).strip()
            if not task_id or task_id not in G.nodes:
                continue
                
            # Get dependencies (support both comma and semicolon separated)
            deps = task.get('Dependencies', task.get('dependencies', ''))
            if isinstance(deps, str):
                deps = [d.strip() for d in deps.replace(';', ',').split(',') if d.strip()]
            
            # Add edges for each dependency
            for dep_id in deps:
                dep_id = str(dep_id).strip()
                if dep_id in G.nodes and task_id in G.nodes and dep_id != task_id:
                    G.add_edge(dep_id, task_id)
        
        return G
    
    def forward_pass(self) -> None:
        """Perform forward pass to calculate early start and early finish times."""
        # Perform topological sort to process nodes in dependency order
        try:
            topo_order = list(nx.topological_sort(self.graph))
        except nx.NetworkXUnfeasible:
            # Handle cycles in the graph
            print("Warning: Cycle detected in task dependencies")
            return
        
        # Forward pass
        for node in topo_order:
            predecessors = list(self.graph.predecessors(node))
            
            if not predecessors:
                # No dependencies, can start at time 0
                self.graph.nodes[node]['early_start'] = 0
            else:
                # Early start is max of all predecessors' early finish times
                max_ef = max(self.graph.nodes[pred]['early_finish'] for pred in predecessors)
                self.graph.nodes[node]['early_start'] = max_ef
            
            # Early finish is early start + duration
            duration = self.graph.nodes[node]['duration']
            self.graph.nodes[node]['early_finish'] = self.graph.nodes[node]['early_start'] + duration
    
    def backward_pass(self) -> None:
        """Perform backward pass to calculate late start and late finish times."""
        if not self.graph.nodes:
            return
            
        # Get nodes in reverse topological order
        try:
            reverse_topo = list(reversed(list(nx.topological_sort(self.graph))))
        except nx.NetworkXUnfeasible:
            print("Warning: Cycle detected in task dependencies")
            return
        
        # Initialize project end time (max of all early finish times)
        project_end = max(self.graph.nodes[node]['early_finish'] for node in self.graph.nodes)
        
        # Initialize all nodes with default values
        for node in self.graph.nodes:
            self.graph.nodes[node]['late_finish'] = float('inf')
            self.graph.nodes[node]['late_start'] = float('inf')
        
        # Backward pass
        for node in reverse_topo:
            successors = list(self.graph.successors(node))
            duration = self.graph.nodes[node]['duration']
            
            if not successors:
                # No successors, set late finish to project end time
                self.graph.nodes[node]['late_finish'] = project_end
                self.graph.nodes[node]['late_start'] = project_end - duration
            else:
                # Late finish is min of all successors' late start times
                if successors:  # Check again in case there are no successors
                    min_ls = min(self.graph.nodes[succ]['late_start'] for succ in successors)
                    self.graph.nodes[node]['late_finish'] = min_ls
                    self.graph.nodes[node]['late_start'] = min_ls - duration
            
            # Calculate slack (total float)
            self.graph.nodes[node]['slack'] = self.graph.nodes[node]['late_start'] - self.graph.nodes[node]['early_start']
            
            # Identify critical tasks (zero slack or very small slack due to floating point)
            self.graph.nodes[node]['is_critical'] = abs(self.graph.nodes[node]['slack']) < 1e-6
    
    def get_critical_path(self) -> List[Dict]:
        """
        Get the critical path as a list of task dictionaries.
        
        Returns:
            List of task dictionaries in the critical path.
        """
        critical_nodes = [node for node in self.graph.nodes if self.graph.nodes[node]['is_critical']]
        
        # Sort by early start time
        critical_nodes_sorted = sorted(critical_nodes, 
                                     key=lambda x: self.graph.nodes[x]['early_start'])
        
        # Get task details for the critical path
        critical_path = []
        for node in critical_nodes_sorted:
            node_data = self.graph.nodes[node]
            critical_path.append({
                'id': node,
                'name': node_data.get('name', f'Task {node}'),
                'duration': node_data.get('duration', 0),
                'early_start': node_data.get('early_start', 0),
                'early_finish': node_data.get('early_finish', 0),
                'late_start': node_data.get('late_start', 0),
                'late_finish': node_data.get('late_finish', 0),
                'slack': node_data.get('slack', 0),
                'is_critical': node_data.get('is_critical', False),
                'resource': node_data.get('resource', 'Unassigned')
            })
        
        return critical_path
        
    def get_minimum_viable_paths(self, max_paths: int = 5) -> List[List[Dict]]:
        """
        Find the top N minimum viable paths in the project.
        
        Args:
            max_paths: Maximum number of paths to return
            
        Returns:
            List of paths, where each path is a list of task dictionaries
        """
        # Find all start nodes (nodes with no incoming edges)
        start_nodes = [node for node in self.graph.nodes if self.graph.in_degree(node) == 0]
        # Find all end nodes (nodes with no outgoing edges)
        end_nodes = [node for node in self.graph.nodes if self.graph.out_degree(node) == 0]
        
        all_paths = []
        
        # Find all paths from start to end nodes
        for start in start_nodes:
            for end in end_nodes:
                try:
                    # Find all simple paths from start to end
                    paths = list(nx.all_simple_paths(self.graph, start, end))
                    for path in paths:
                        # Calculate total duration of the path
                        path_duration = sum(self.graph.nodes[node]['duration'] for node in path)
                        # Create path with task details
                        path_tasks = []
                        for node in path:
                            node_data = self.graph.nodes[node]
                            path_tasks.append({
                                'id': node,
                                'name': node_data.get('name', f'Task {node}'),
                                'duration': node_data.get('duration', 0),
                                'resource': node_data.get('resource', 'Unassigned')
                            })
                        all_paths.append({
                            'path': path_tasks,
                            'duration': path_duration,
                            'is_critical': all(self.graph.nodes[node]['is_critical'] for node in path)
                        })
                except nx.NetworkXNoPath:
                    continue
        
        # Sort paths by duration and take top N
        all_paths.sort(key=lambda x: x['duration'])
        return [path_info['path'] for path_info in all_paths[:max_paths]]
    
    def identify_bottlenecks(self, threshold: float = 0.2) -> List[Dict]:
        """
        Identify bottleneck tasks in the project.
        
        Args:
            threshold: Slack threshold as a percentage of project duration to consider a task a bottleneck.
                      Tasks with slack less than this threshold are considered bottlenecks.
                      
        Returns:
            List of dictionaries containing bottleneck task information.
        """
        if not self.graph.nodes:
            return []
        
        project_duration = max((self.graph.nodes[node]['early_finish'] for node in self.graph.nodes), default=0)
        slack_threshold = project_duration * threshold
        
        bottlenecks = []
        for node in self.graph.nodes:
            node_data = self.graph.nodes[node]
            
            # Skip nodes with no duration
            if node_data.get('duration', 0) <= 0:
                continue
                
            # Calculate impact (number of dependent tasks)
            impact = len(nx.descendants(self.graph, node))
            
            # Check if this is a bottleneck
            slack = node_data.get('slack', float('inf'))
            if slack <= slack_threshold and impact > 1:  # Only consider nodes that impact multiple tasks
                # Add bottleneck data to node
                self.graph.nodes[node]['is_bottleneck'] = True
                self.graph.nodes[node]['impact'] = impact
                
                bottlenecks.append({
                    'id': node,
                    'name': node_data.get('name', f'Task {node}'),
                    'duration': node_data.get('duration', 0),
                    'resource': node_data.get('resource', 'Unassigned'),
                    'impact': impact,
                    'slack': slack,
                    'early_start': node_data.get('early_start', 0),
                    'late_start': node_data.get('late_start', 0)
                })
        
        # Sort by impact (highest first)
        return sorted(bottlenecks, key=lambda x: x['impact'], reverse=True)
        bottlenecks.sort(key=lambda x: (-x['impact'], x['slack']))
        
        return bottlenecks
    
    def get_project_duration(self) -> float:
        """
        Get the total project duration.
        
        Returns:
            Total project duration in the same units as task durations.
        """
        if not self.graph.nodes:
            return 0
        return max(self.graph.nodes[node]['early_finish'] for node in self.graph.nodes)

# =============================================================================
# Graph Editor
# =============================================================================

class GraphEditor:
    """A class for interactive manipulation of project graphs."""
    
    def __init__(self):
        """Initialize an empty graph."""
        self.graph = nx.DiGraph()
    
    def add_node(self, node_id: str, label: str = "", duration: int = 0, 
                resource: str = "Unassigned", dependencies: str = "") -> None:
        """
        Add a node to the graph.
        
        Args:
            node_id: Unique identifier for the node
            label: Display name for the node
            duration: Duration of the task
            resource: Assigned resource
            dependencies: Comma-separated string of dependency node IDs
        """
        self.graph.add_node(node_id, 
                          label=label or f"Task {node_id}",
                          duration=duration,
                          resource=resource,
                          dependencies=dependencies)
    
    def remove_node(self, node_id: str) -> bool:
        """
        Remove a node from the graph.
        
        Args:
            node_id: ID of the node to remove
            
        Returns:
            True if node was removed, False if not found
        """
        if node_id in self.graph:
            self.graph.remove_node(node_id)
            return True
        return False
    
    def add_edge(self, source: str, target: str) -> bool:
        """
        Add a directed edge from source to target.
        
        Args:
            source: Source node ID
            target: Target node ID
            
        Returns:
            True if edge was added, False if nodes don't exist
        """
        if source in self.graph and target in self.graph:
            self.graph.add_edge(source, target)
            return True
        return False
    
    def remove_edge(self, source: str, target: str) -> bool:
        """
        Remove an edge from the graph.
        
        Args:
            source: Source node ID
            target: Target node ID
            
        Returns:
            True if edge was removed, False if not found
        """
        if self.graph.has_edge(source, target):
            self.graph.remove_edge(source, target)
            return True
        return False
    
    def update_node(self, node_id: str, **kwargs) -> bool:
        """
        Update node attributes.
        
        Args:
            node_id: ID of the node to update
            **kwargs: Attributes to update
            
        Returns:
            True if node was updated, False if not found
        """
        if node_id in self.graph:
            for key, value in kwargs.items():
                if value is not None:  # Only update if value is not None
                    self.graph.nodes[node_id][key] = value
            return True
        return False
    
    def get_graph(self) -> nx.DiGraph:
        """
        Get the current graph.
        
        Returns:
            The networkx DiGraph object
        """
        return self.graph
    
    def clear_graph(self) -> None:
        """Clear all nodes and edges from the graph."""
        self.graph.clear()
    
    def export_graph(self, format: str = 'json') -> Union[Dict, str]:
        """
        Export the graph in the specified format.
        
        Args:
            format: Export format ('json' or 'gml')
            
        Returns:
            The exported graph data
        """
        if format.lower() == 'gml':
            return nx.generate_gml(self.graph)
        else:  # Default to JSON
            return nx.node_link_data(self.graph)
    
    def import_graph(self, data: Union[Dict, str], format: str = 'json') -> bool:
        """
        Import a graph from the specified format.
        
        Args:
            data: Graph data to import
            format: Import format ('json' or 'gml')
            
        Returns:
            True if import was successful, False otherwise
        """
        try:
            if format.lower() == 'gml':
                self.graph = nx.parse_gml(data)
            else:  # Default to JSON
                self.graph = nx.node_link_graph(data)
            return True
        except Exception as e:
            print(f"Error importing graph: {e}")
            return False
    
    def export_tasks(self) -> List[Dict]:
        """
        Export tasks in a format suitable for the CriticalPathAnalyzer.
        
        Returns:
            List of task dictionaries
        """
        tasks = []
        for node_id, node_data in self.graph.nodes(data=True):
            task = {
                'Task ID': node_id,
                'Task Name': node_data.get('label', f'Task {node_id}'),
                'Duration': node_data.get('duration', 0),
                'Resource': node_data.get('resource', 'Unassigned'),
                'Dependencies': list(self.graph.predecessors(node_id))
            }
            tasks.append(task)
        return tasks
    
    def validate_graph(self) -> Dict[str, Any]:
        """
        Validate the graph structure.
        
        Returns:
            Dictionary with validation results
        """
        result = {
            'is_dag': nx.is_directed_acyclic_graph(self.graph),
            'has_cycles': not nx.is_directed_acyclic_graph(self.graph),
            'nodes': len(self.graph.nodes()),
            'edges': len(self.graph.edges()),
            'connected_components': nx.number_weakly_connected_components(self.graph)
        }
        
        # Find cycles if they exist
        if result['has_cycles']:
            try:
                result['cycles'] = list(nx.simple_cycles(self.graph))
            except Exception as e:
                result['cycle_error'] = str(e)
        
        return result

# =============================================================================
# Gantt Chart Generator
# =============================================================================

class GanttChart:
    """A class for generating Gantt charts from task data."""
    
    def __init__(self):
        """Initialize the Gantt chart generator."""
        self.colors = [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
            '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'
        ]
    
    def generate_gantt_data(self, tasks: List[Dict]) -> Dict:
        """
        Generate data for a Gantt chart.
        
        Args:
            tasks: List of task dictionaries
            
        Returns:
            Dictionary with Gantt chart data
        """
        if not tasks:
            return {}
            
        # Process tasks
        processed_tasks = []
        resource_colors = {}
        
        for i, task in enumerate(tasks):
            task_id = task.get('Task ID', task.get('task_id', f'task_{i}'))
            name = task.get('Task Name', task.get('task_name', f'Task {task_id}'))
            start = task.get('early_start', 0)
            duration = int(float(task.get('Duration', task.get('duration', 0))))
            resource = task.get('Resource', task.get('resource', 'Unassigned'))
            
            # Assign color based on resource
            if resource not in resource_colors:
                resource_colors[resource] = self.colors[len(resource_colors) % len(self.colors)]
            
            processed_tasks.append({
                'Task': name,
                'Start': start,
                'Finish': start + duration,
                'Resource': resource,
                'Duration': duration,
                'Task_ID': task_id,
                'Color': resource_colors[resource]
            })
        
        # Sort tasks by start time
        processed_tasks.sort(key=lambda x: x['Start'])
        
        return {
            'tasks': processed_tasks,
            'resources': list(resource_colors.keys()),
            'resource_colors': resource_colors,
            'project_duration': max((task['Finish'] for task in processed_tasks), default=0)
        }
    
    def generate_gantt_chart(self, tasks: List[Dict], output_format: str = 'plotly') -> Any:
        """
        Generate a Gantt chart.
        
        Args:
            tasks: List of task dictionaries
            output_format: Output format ('plotly' or 'html')
            
        Returns:
            Plotly figure or HTML string, depending on format
        """
        data = self.generate_gantt_data(tasks)
        if not data or 'tasks' not in data or not data['tasks']:
            return None
        
        # Create figure
        fig = go.Figure()
        
        # Add bars for each task
        for task in data['tasks']:
            fig.add_trace(go.Bar(
                name=task['Task'],
                x=[task['Duration']],
                y=[task['Task']],
                base=task['Start'],
                orientation='h',
                marker_color=task['Color'],
                text=f"{task['Task']}<br>Duration: {task['Duration']} days<br>Resource: {task['Resource']}",
                hoverinfo='text',
                textposition='inside',
                texttemplate='%{text}',
                textfont=dict(size=10)
            ))
        
        # Update layout
        fig.update_layout(
            title='Project Gantt Chart',
            xaxis_title='Timeline',
            yaxis_title='Tasks',
            showlegend=False,
            height=max(400, len(data['tasks']) * 25 + 100),
            margin=dict(l=200, r=50, t=80, b=50),
            xaxis=dict(
                tickformat=",d",
                rangeslider_visible=True,
                side='top'
            ),
            yaxis=dict(
                autorange="reversed",
                tickfont=dict(size=10)
            )
        )
        
        if output_format.lower() == 'html':
            return fig.to_html(full_html=False, include_plotlyjs='cdn')
        
        return fig
    
    def export_gantt_chart(self, tasks: List[Dict], filename: str, format: str = 'png') -> bool:
        """
        Export Gantt chart to a file.
        
        Args:
            tasks: List of task dictionaries
            filename: Output filename
            format: Export format ('png', 'jpeg', 'webp', 'svg', 'pdf')
            
        Returns:
            True if export was successful, False otherwise
        """
        try:
            fig = self.generate_gantt_chart(tasks, output_format='plotly')
            if not fig:
                return False
                
            if format.lower() == 'html':
                with open(filename, 'w') as f:
                    f.write(fig.to_html(full_html=True, include_plotlyjs='cdn'))
            else:
                fig.write_image(filename, format=format.lower())
                
            return True
        except Exception as e:
            print(f"Error exporting Gantt chart: {e}")
            return False

# =============================================================================
# AI Optimizer
# =============================================================================

class AIOptimizer:
    """A class for AI-powered task optimization and suggestions."""
    
    def __init__(self, api_key: str = None):
        """
        Initialize the AI Optimizer.
        
        Args:
            api_key: Optional Google Gemini API key. If not provided, will try to get from environment.
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash')
        else:
            self.model = None
    
    def get_optimization_suggestions(self, tasks: List[Dict], question: str = None) -> List[Dict]:
        """
        Generate optimization suggestions for a list of tasks.
        
        Args:
            tasks: List of task dictionaries
            question: Optional specific question to ask the AI
            
        Returns:
            List of suggestion dictionaries
        """
        if not self.model:
            return [{
                'type': 'warning',
                'title': 'AI Service Not Configured',
                'description': 'Please set the GEMINI_API_KEY environment variable to enable AI suggestions.',
                'priority': 'high'
            }]
            
        # If no question is provided, use a default one
        if not question or not question.strip():
            question = "What are the key optimization opportunities for these tasks?"
            
        try:
            # Prepare task data for the prompt
            task_list = []
            for i, task in enumerate(tasks, 1):
                task_id = task.get('Task ID', task.get('task_id', f'Task {i}'))
                task_name = task.get('Task Name', task.get('task_name', f'Task {i}'))
                duration = task.get('Duration', task.get('duration', 0))
                resource = task.get('Resource', task.get('resource', 'Unassigned'))
                deps = task.get('Dependencies', task.get('dependencies', []))
                if isinstance(deps, str):
                    deps = [d.strip() for d in deps.split(',') if d.strip()]
                
                task_list.append(f"{i}. {task_name} "
                              f"(ID: {task_id}, "
                              f"Duration: {duration}h, "
                              f"Resource: {resource}, "
                              f"Dependencies: {', '.join(deps) or 'None'})")
            
            # Create a detailed prompt with clear instructions
            prompt = f"""You are an expert project manager analyzing a project plan. Here are the project tasks:
            
            {chr(10).join(task_list)}
            
            Please analyze these tasks and provide specific, actionable recommendations to optimize this project. 
            
            Your analysis should include:
            1. **Project Overview**: Brief summary of key observations about the project
            2. **Top Recommendations** (3-5 items):
               - For each recommendation:
                 * Task(s) affected
                 * Specific action to take
                 * Expected benefit
                 * Any risks or considerations
            3. **Additional Insights**: Any other observations that could help improve the project
            
            Focus on practical, implementable suggestions that will have the most impact on project success.
            
            If you need any clarification about the tasks, please make reasonable assumptions and state them clearly."""
            
            response = self.model.generate_content(prompt)
            
            # Process the response into structured suggestions
            suggestions = []
            if response.text:
                # Split the response into individual suggestions
                suggestion_texts = [s.strip() for s in response.text.split('\n') if s.strip()]
                
                for i, text in enumerate(suggestion_texts, 1):
                    if text and len(text) > 10:  # Simple validation for non-empty suggestions
                        suggestions.append({
                            'type': 'suggestion',
                            'title': f'Optimization Suggestion {i}',
                            'description': text,
                            'priority': 'high' if i == 1 else 'medium',
                            'task_id': None,  # Can be linked to specific tasks if needed
                            'impact': 'high',
                            'effort': 'medium'
                        })
            
            return suggestions if suggestions else [{
                'type': 'info',
                'title': 'No Specific Suggestions',
                'description': 'No specific optimization suggestions were generated. The current plan appears to be well-optimized.',
                'priority': 'low'
            }]
            
        except Exception as e:
            print(f"Error generating AI suggestions: {e}")
            return [{
                'type': 'error',
                'title': 'Error Generating Suggestions',
                'description': f'An error occurred while generating AI suggestions: {str(e)}',
                'priority': 'high'
            }]
    
    def get_ai_suggestion(self, prompt: str, context: Dict = None) -> str:
        """
        Get a response from the AI model based on the given prompt and context.
        
        Args:
            prompt: User's question or prompt
            context: Optional context dictionary
            
        Returns:
            AI-generated response as a string
        """
        if not self.model:
            return "AI service is not configured. Please set the GEMINI_API_KEY environment variable."
        
        try:
            full_prompt = f"""You are a helpful project management assistant. Please provide a concise and helpful response to the following question.
            
            Context: {json.dumps(context, indent=2) if context else 'No additional context provided.'}
            
            Question: {prompt}
            
            Response:"""
            
            response = self.model.generate_content(full_prompt)
            return response.text if response.text else "I couldn't generate a response. Please try again."
            
        except Exception as e:
            return f"Error generating response: {str(e)}"

# =============================================================================
# Flask Application
# =============================================================================

# Initialize Flask app
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['EXPORT_FOLDER'] = 'exports'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['EXPORT_FOLDER'], exist_ok=True)

# Initialize the GraphEditor and AIOptimizer
graph_editor = GraphEditor()
ai_optimizer = AIOptimizer()

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# =============================================================================
# Helper Functions
# =============================================================================

def analyze_workflow(tasks: List[Dict]) -> Dict:
    """
    Analyze a workflow using the CriticalPathAnalyzer.
    
    Args:
        tasks: List of task dictionaries
        
    Returns:
        Dictionary with analysis results
    """
    try:
        print("=== Starting workflow analysis ===")
        print(f"Received {len(tasks)} tasks for analysis")
        
        # Convert tasks to the format expected by GraphEditor
        graph_editor.clear_graph()
        
        # First pass: add all nodes
        for task in tasks:
            # Handle both string and numeric task IDs
            task_id = str(task.get('Task ID', task.get('task_id', ''))).strip()
            if not task_id:
                print(f"Skipping task with empty ID: {task}")
                continue
                
            # Get duration with fallback to estimated_time
            duration = 0
            try:
                duration = int(float(task.get('Duration', task.get('duration', task.get('estimated_time', 0)))))
                if duration <= 0:
                    print(f"Warning: Task {task_id} has invalid duration {duration}, defaulting to 1")
                    duration = 1
            except (ValueError, TypeError) as e:
                print(f"Error parsing duration for task {task_id}: {e}, using default 1")
                duration = 1
            
            # Add the node
            try:
                graph_editor.add_node(
                    node_id=task_id,
                    label=task.get('Task Name', task.get('task_name', f'Task {task_id}')),
                    duration=duration,
                    resource=task.get('Resource', task.get('resource', 'Unassigned')),
                    dependencies=task.get('Dependencies', task.get('dependencies', ''))
                )
                print(f"Added task {task_id} with duration {duration}")
            except Exception as e:
                print(f"Error adding task {task_id}: {e}")
                continue
        
        # Get the graph for analysis
        graph = graph_editor.get_graph()
        if not graph.nodes:
            raise ValueError("No valid tasks found in the graph")
            
        print(f"Graph has {len(graph.nodes)} nodes and {len(graph.edges)} edges")
        
        # Initialize CriticalPathAnalyzer with the graph
        tasks_for_analysis = graph_editor.export_tasks()
        print(f"Exported {len(tasks_for_analysis)} tasks for analysis")
        
        cpa = CriticalPathAnalyzer(tasks_for_analysis)
        
        # Get the critical path with detailed information
        critical_path = []
        try:
            critical_nodes = cpa.get_critical_path()
            print(f"Found {len(critical_nodes)} tasks in critical path")
            
            for node in critical_nodes:
                if node not in cpa.graph.nodes:
                    print(f"Warning: Critical node {node} not found in graph")
                    continue
                    
                node_data = cpa.graph.nodes[node]
                task_info = {
                    'id': node,
                    'name': node_data.get('name', f'Task {node}'),
                    'duration': node_data.get('duration', 0),
                    'resource': node_data.get('resource', 'Unassigned'),
                    'early_start': node_data.get('early_start', 0),
                    'early_finish': node_data.get('early_finish', 0),
                    'late_start': node_data.get('late_start', 0),
                    'late_finish': node_data.get('late_finish', 0),
                    'slack': node_data.get('slack', 0),
                    'is_critical': True,
                    'dependencies': node_data.get('dependencies', [])
                }
                critical_path.append(task_info)
                print(f"Critical task: {task_info['name']} (ID: {node}), "
                      f"Duration: {task_info['duration']}, "
                      f"ES: {task_info['early_start']}, "
                      f"EF: {task_info['early_finish']}, "
                      f"Slack: {task_info['slack']}")
        except Exception as e:
            print(f"Error getting critical path: {e}")
            traceback.print_exc()
            raise
        
        # Get bottlenecks
        bottlenecks = cpa.identify_bottlenecks()
        
        # Get AI suggestions
        ai_optimizer = AIOptimizer()
        ai_suggestions = ai_optimizer.get_optimization_suggestions(tasks_for_analysis)
        
        # Generate Gantt chart data
        gantt = GanttChart()
        gantt_data = gantt.generate_gantt_data(tasks_for_analysis)
        
        # Get graph data with critical path and bottleneck information
        graph_data = graph_editor.export_graph('json')
        
        return {
            'critical_path': critical_path,
            'bottlenecks': bottlenecks,
            'ai_suggestions': ai_suggestions,
            'gantt_data': gantt_data,
            'graph_data': graph_data,
            'project_duration': cpa.get_project_duration(),
            'task_count': len(tasks),
            'success': True
        }
        
    except Exception as e:
        print(f"Error in analyze_workflow: {str(e)}")
        traceback.print_exc()
        return {
            'error': str(e),
            'critical_path': [],
            'bottlenecks': [],
            'ai_suggestions': [],
            'gantt_data': None,
            'graph_data': None,
            'success': False
        }

# =============================================================================
# API Routes
# =============================================================================

@app.route('/')
def index():
    """Render the main application page."""
    return render_template('index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze():
    """Analyze a workflow from an uploaded CSV file."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded', 'success': False}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file', 'success': False}), 400
            
        if file:
            # Save the file temporarily
            filename = os.path.join(app.config['UPLOAD_FOLDER'], 
                                  f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
            file.save(filename)
            
            try:
                # Read and parse the CSV
                df = pd.read_csv(filename)
                tasks = df.to_dict('records')
                
                # Analyze the workflow
                result = analyze_workflow(tasks)
                
                return jsonify(result)
                
            finally:
                # Clean up the temporary file
                try:
                    os.remove(filename)
                except:
                    pass
                    
    except Exception as e:
        return jsonify({
            'error': str(e),
            'trace': traceback.format_exc(),
            'success': False
        }), 500

@app.route('/api/graph/update', methods=['POST'])
def update_graph():
    """Update the graph with node/edge additions/removals."""
    try:
        data = request.get_json()
        action = data.get('action')
        
        if action == 'add_node':
            node_id = data.get('id')
            node_data = data.get('data', {})
            graph_editor.add_node(
                node_id=node_id,
                label=node_data.get('label', ''),
                duration=node_data.get('duration', 0),
                resource=node_data.get('resource', 'Unassigned'),
                dependencies=node_data.get('dependencies', '')
            )
        elif action == 'remove_node':
            graph_editor.remove_node(data.get('id'))
        elif action == 'add_edge':
            graph_editor.add_edge(
                source=data.get('from'),
                target=data.get('to')
            )
        elif action == 'remove_edge':
            graph_editor.remove_edge(
                source=data.get('from'),
                target=data.get('to')
            )
        elif action == 'update_node':
            node_id = data.get('id')
            node_data = data.get('data', {})
            graph_editor.update_node(
                node_id=node_id,
                **node_data
            )
        
        return jsonify({
            'success': True,
            'graph': graph_editor.export_graph('json')
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/api/gantt/data', methods=['GET'])
def get_gantt_data():
    """Get Gantt chart data for the current graph."""
    try:
        tasks = graph_editor.export_tasks()
        gantt = GanttChart()
        gantt_data = gantt.generate_gantt_data(tasks)
        return jsonify(gantt_data)
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 400

@app.route('/api/gantt/export', methods=['GET'])
def export_gantt():
    """Export the Gantt chart in the specified format."""
    try:
        format_type = request.args.get('format', 'png')
        tasks = graph_editor.export_tasks()
        gantt = GanttChart()
        
        if format_type == 'html':
            html_content = gantt.generate_gantt_chart(tasks, output_format='html')
            return html_content
        else:
            filename = f"gantt_chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format_type}"
            filepath = os.path.join(app.config['EXPORT_FOLDER'], filename)
            gantt.export_gantt_chart(tasks, filepath, format=format_type)
            return send_from_directory(
                app.config['EXPORT_FOLDER'],
                filename,
                as_attachment=True
            )
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 400

@app.route('/api/ai/suggest', methods=['POST'])
def get_ai_suggestion():
    """Get an AI-generated suggestion based on the provided prompt and context."""
    try:
        data = request.get_json()
        prompt = data.get('prompt', '')
        context = data.get('context', {})
        
        # Use the AIOptimizer to get a suggestion
        suggestion = ai_optimizer.get_ai_suggestion(prompt, context)
        
        return jsonify({
            'suggestion': suggestion,
            'success': True
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'success': False
        }), 400

@app.route('/exports/<path:filename>')
def serve_export(filename):
    """Serve exported files from the exports directory."""
    return send_from_directory(app.config['EXPORT_FOLDER'], filename)

# =============================================================================
# Main Execution
# =============================================================================

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('exports', exist_ok=True)
    
    # Run the application
    app.run(debug=True, port=5001)
