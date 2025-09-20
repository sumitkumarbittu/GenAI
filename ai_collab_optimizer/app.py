from flask import Flask, render_template, request, jsonify
import pandas as pd
import networkx as nx
import json
import os
from datetime import datetime
from dotenv import load_dotenv

app = Flask(__name__)

# Load environment variables from .env file
load_dotenv()

# Ensure the uploads directory exists
os.makedirs('uploads', exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
            
        if file:
            # Save the file temporarily
            filename = f"uploads/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
            file.save(filename)
            
            # Read and parse the CSV
            df = pd.read_csv(filename)
            
            # Clean up the file
            os.remove(filename)
            
            # Validate required columns
            required_columns = ['task_id', 'name', 'assigned_to', 'estimated_time', 'dependencies']
            if not all(col in df.columns for col in required_columns):
                return jsonify({
                    'error': f'Missing required columns. Required: {required_columns}'
                }), 400
            
            # Process the data
            tasks = []
            for _, row in df.iterrows():
                task = {
                    'id': int(row['task_id']),
                    'name': str(row['name']),
                    'assigned_to': str(row['assigned_to']),
                    'estimated_time': float(row['estimated_time']) if pd.notna(row['estimated_time']) else 0,
                    'dependencies': []
                }
                
                if pd.notna(row['dependencies']) and str(row['dependencies']).strip():
                    task['dependencies'] = [int(dep.strip()) for dep in str(row['dependencies']).split(';') if dep.strip()]
                
                tasks.append(task)
            
            # Analyze the workflow
            analysis = analyze_workflow(tasks)
            
            return jsonify({
                'status': 'success',
                'tasks': tasks,
                'analysis': analysis
            })
            
    except Exception as e:
        return jsonify({
            'error': str(e),
            'type': type(e).__name__
        }), 500

def analyze_workflow(tasks):
    """Analyze the workflow and identify bottlenecks."""
    # Create a directed graph
    G = nx.DiGraph()
    
    # Add nodes and edges
    task_map = {task['id']: task for task in tasks}
    for task in tasks:
        G.add_node(task['id'], 
                  name=task['name'],
                  assigned_to=task['assigned_to'],
                  estimated_time=task['estimated_time'])
        
        for dep_id in task['dependencies']:
            if dep_id in task_map:
                G.add_edge(dep_id, task['id'])
    
    # Find critical path
    try:
        critical_path = nx.dag_longest_path(G, weight='estimated_time')
        critical_path_str = ' → '.join([str(node) for node in critical_path])
    except nx.NetworkXUnfeasible:
        critical_path = []
        critical_path_str = 'Could not determine (possible cycle in dependencies)'
    
    # Calculate total time for critical path
    total_time = sum(G.nodes[node].get('estimated_time', 0) for node in critical_path)
    
    # Find bottlenecks (nodes with multiple dependencies or high workload)
    bottlenecks = [n for n in G.nodes if G.in_degree(n) > 1]
    
    # Calculate workload for each task
    workload = {}
    for node in G.nodes():
        workload[node] = G.nodes[node].get('estimated_time', 0)
        for desc in nx.descendants(G, node):
            workload[node] += G.nodes[desc].get('estimated_time', 0)
    
    # Sort bottlenecks by workload
    bottlenecks = sorted(bottlenecks, key=lambda x: workload.get(x, 0), reverse=True)
    
    # Prepare bottleneck data
    bottleneck_data = []
    for node in bottlenecks:
        task = G.nodes[node]
        bottleneck_data.append({
            'task_id': node,
            'name': task.get('name', ''),
            'assigned_to': task.get('assigned_to', ''),
            'estimated_time': task.get('estimated_time', 0),
            'dependent_tasks': G.in_degree(node),
            'total_impact': workload.get(node, 0)
        })
    
    return {
        'critical_path': critical_path,
        'critical_path_str': critical_path_str,
        'total_time': total_time,
        'bottlenecks': bottleneck_data,
        'has_cycle': nx.is_directed_acyclic_graph(G) is False
    }

@app.route('/api/ai/suggest', methods=['POST'])
def get_ai_suggestion():
    try:
        data = request.get_json()
        task_name = data.get('task_name', '')
        assigned_to = data.get('assigned_to', '')
        estimated_time = data.get('estimated_time', 0)
        dependencies = data.get('dependencies', [])
        
        # Get API key from environment variable
        openai.api_key = os.getenv("OPENAI_API_KEY")
        if not openai.api_key:
            return jsonify({
                'status': 'error',
                'message': 'OpenAI API key not configured. Please set the OPENAI_API_KEY environment variable.'
            }), 500

        # Create a detailed prompt for better suggestions
        prompt = f"""
        As an experienced project manager, please provide specific, actionable suggestions to optimize this task:
        
        Task: {task_name}
        Assigned To: {assigned_to}
        Estimated Duration: {estimated_time} hours
        Dependencies: {', '.join(map(str, dependencies)) if dependencies else 'None'}
        
        Please provide 2-3 specific, actionable suggestions to:
        1. Optimize the task workflow
        2. Manage dependencies effectively
        3. Ensure balanced workload for {assigned_to}
        4. Identify potential risks or bottlenecks
        
        Format the response with clear bullet points and keep it concise.
        """

        try:
            # Call OpenAI API
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",  # Using 3.5 as it's more widely available
                messages=[
                    {"role": "system", "content": "You are a helpful project management assistant that provides concise, actionable advice."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=300
            )
            
            suggestion = response['choices'][0]['message']['content'].strip()
            
            return jsonify({
                'status': 'success',
                'suggestion': suggestion
            })
            
        except Exception as api_error:
            return jsonify({
                'status': 'error',
                'message': f'Error calling OpenAI API: {str(api_error)}',
                'type': type(api_error).__name__
            }), 500
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'type': type(e).__name__
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
