import streamlit as st
import pandas as pd
import networkx as nx
from pyvis.network import Network
import openai
import tempfile
import os

# ----------------------------
# 1. OpenAI API Configuration
# ----------------------------
# Make OpenAI API key optional
openai_api_key = None
try:
    openai_api_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if openai_api_key and openai_api_key != "YOUR_OPENAI_API_KEY":
        openai.api_key = openai_api_key
        AI_ENABLED = True
    else:
        AI_ENABLED = False
except Exception:
    AI_ENABLED = False

def suggest_solution(task_name, assigned_to):
    """
    Use GPT to suggest ways to reduce workload or reassign tasks.
    """
    if not AI_ENABLED:
        return "AI suggestions are disabled. Please set up your OpenAI API key to enable this feature."
        
    prompt = f"""
    Task '{task_name}' assigned to {assigned_to} is a potential bottleneck in a project.
    Suggest 2-3 actionable ways to reduce workload, split the task, or reassign it.
    Keep the response concise and focused on practical solutions.
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Using 3.5 as it's more widely available
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"Error generating suggestion: {str(e)}. Please check your OpenAI API key and internet connection."

# ----------------------------
# 2. Streamlit App
# ----------------------------
st.set_page_config(page_title="AI Collaboration Optimizer", layout="wide")
st.title("AI Collaboration Optimizer 🚀")
st.markdown("""
Upload your project task CSV with columns:
`task_id, name, assigned_to, estimated_time, dependencies` 
- `dependencies` should be semicolon-separated task_ids (e.g., "1;3")
- `estimated_time` should be in hours
""")

# Add example data
example_data = {
    'task_id': [1, 2, 3, 4, 5],
    'name': ['Design UI', 'Build Backend', 'API Integration', 'Testing', 'Documentation'],
    'assigned_to': ['Alice', 'Bob', 'Charlie', 'Dave', 'Eve'],
    'estimated_time': [5, 8, 4, 3, 2],
    'dependencies': ['', '1', '2', '2;3', '3']
}

# Create example download
@st.cache_data
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

csv = convert_df_to_csv(pd.DataFrame(example_data))

download_col, _ = st.columns(2)
with download_col:
    st.download_button(
        label="📥 Download Example CSV",
        data=csv,
        file_name='example_tasks.csv',
        mime='text/csv',
    )

uploaded_file = st.file_uploader("Or upload your own CSV file", type=["csv"])

# Use example data if no file uploaded
if uploaded_file is None:
    st.warning("👆 Please upload a CSV file or use the example data.")
    st.stop()

df = pd.read_csv(uploaded_file)

# Validate required columns
required_columns = ['task_id', 'name', 'assigned_to', 'estimated_time', 'dependencies']
if not all(col in df.columns for col in required_columns):
    st.error(f"❌ Error: CSV must contain these columns: {', '.join(required_columns)}")
    st.stop()

st.subheader("📋 Task Data Overview")
st.dataframe(df, use_container_width=True)

# ----------------------------
# 3. Build Task Graph
# ----------------------------
G = nx.DiGraph()
for _, row in df.iterrows():
    G.add_node(
        row['task_id'], 
        name=row['name'], 
        assigned_to=row['assigned_to'], 
        time=row['estimated_time']
    )
    if pd.notna(row['dependencies']) and str(row['dependencies']).strip():
        deps = [d.strip() for d in str(row['dependencies']).split(';') if d.strip()]
        for dep in deps:
            try:
                G.add_edge(int(dep), row['task_id'])
            except ValueError:
                st.warning(f"Skipping invalid dependency: {dep} for task {row['task_id']}")

# ----------------------------
# 4. Detect Bottlenecks
# ----------------------------
st.subheader("🔍 Bottleneck Analysis")

# Calculate critical path
try:
    critical_path = nx.dag_longest_path(G, weight='time')
    critical_path_str = ' → '.join([str(node) for node in critical_path])
    st.info(f"**Critical Path:** {critical_path_str}")
    
    # Calculate total time for critical path
    total_time = sum(G.nodes[node].get('time', 0) for node in critical_path)
    st.info(f"**Estimated Total Time:** {total_time} hours")
    
except nx.NetworkXUnfeasible:
    st.warning("⚠️ Warning: The task graph contains cycles. Please check your dependencies.")

# Find bottlenecks (nodes with multiple dependencies or high workload)
bottlenecks = [n for n in G.nodes if G.in_degree(n) > 1]
workload = {}
for node in G.nodes():
    # Calculate workload as sum of task time and all dependent tasks
    workload[node] = G.nodes[node].get('time', 0)
    for desc in nx.descendants(G, node):
        workload[node] += G.nodes[desc].get('time', 0)

# Sort by workload
bottlenecks = sorted(bottlenecks, key=lambda x: workload.get(x, 0), reverse=True)

if bottlenecks:
    st.warning(f"🚨 Found {len(bottlenecks)} potential bottlenecks in the workflow")
    bottleneck_data = []
    for node in bottlenecks:
        task = G.nodes[node]
        bottleneck_data.append({
            'Task ID': node,
            'Task Name': task.get('name', ''),
            'Assigned To': task.get('assigned_to', ''),
            'Estimated Time (hours)': task.get('time', 0),
            'Dependent Tasks': G.in_degree(node),
            'Total Impact (hours)': workload.get(node, 0)
        })
    st.dataframe(pd.DataFrame(bottleneck_data), use_container_width=True)
else:
    st.success("✅ No major bottlenecks detected in the workflow")

# ----------------------------
# 5. Generate AI Suggestions
# ----------------------------
if st.button("🤖 Get AI Suggestions"):
    st.subheader("💡 AI-Powered Recommendations")
    
    if not bottlenecks:
        st.info("No major bottlenecks found to analyze.")
    else:
        with st.spinner("Analyzing workflow and generating suggestions..."):
            for node in bottlenecks[:3]:  # Limit to top 3 to save tokens
                task = G.nodes[node]
                with st.expander(f"🔧 Task {node}: {task.get('name', '')} (Assigned to {task.get('assigned_to', '?')})"):
                    suggestion = suggest_solution(task.get('name', ''), task.get('assigned_to', ''))
                    st.markdown(suggestion)
                    
                    # Add action buttons
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"Reassign Task {node}", key=f"reassign_{node}"):
                            st.session_state[f'reassign_{node}'] = True
                    with col2:
                        if st.button(f"Split Task {node}", key=f"split_{node}"):
                            st.session_state[f'split_{node}'] = True
                    
                    # Handle button actions
                    if st.session_state.get(f'reassign_{node}', False):
                        new_assignee = st.selectbox(
                            f"Select new assignee for Task {node}:",
                            options=[m for m in df['assigned_to'].unique() if m != task.get('assigned_to', '')],
                            key=f"new_assignee_{node}"
                        )
                        if st.button(f"Confirm Reassignment to {new_assignee}", key=f"confirm_reassign_{node}"):
                            # Update the graph and dataframe
                            G.nodes[node]['assigned_to'] = new_assignee
                            df.loc[df['task_id'] == node, 'assigned_to'] = new_assignee
                            st.success(f"Task {node} reassigned to {new_assignee}")
                            st.rerun()
                    
                    if st.session_state.get(f'split_{node}', False):
                        st.info("Coming soon: Task splitting functionality")

# ----------------------------
# 6. Visualize Task Graph
# ----------------------------
st.subheader("📊 Interactive Task Graph")

# Create Pyvis network
net = Network(
    height='600px', 
    width='100%', 
    notebook=False, 
    directed=True,
    bgcolor='#ffffff',
    font_color='#2d3436'
)

# Add nodes with styling
for n, attr in G.nodes(data=True):
    is_bottleneck = n in bottlenecks
    is_critical = n in critical_path if 'critical_path' in locals() else False
    
    # Determine node color
    if is_critical and is_bottleneck:
        color = '#e74c3c'  # Red for critical bottlenecks
    elif is_critical:
        color = '#e67e22'  # Orange for critical path
    elif is_bottleneck:
        color = '#f1c40f'  # Yellow for bottlenecks
    else:
        color = '#2ecc71'  # Green for normal nodes
    
    title = f"""
    <b>Task {n}: {attr.get('name', '')}</b><br>
    <b>Assigned to:</b> {attr.get('assigned_to', '')}<br>
    <b>Time:</b> {attr.get('time', 0)} hours<br>
    <b>Dependencies:</b> {', '.join(str(p) for p in G.predecessors(n)) or 'None'}
    """
    
    net.add_node(
        n, 
        label=f"{n}: {attr.get('name', '')}", 
        color=color,
        title=title,
        borderWidth=2,
        shape='box',
        font={'size': 12, 'face': 'Arial'}
    )

# Add edges with arrows
for u, v in G.edges():
    net.add_edge(u, v, arrows='to', width=1, color='#95a5a6')

# Improve layout
net.repulsion(
    node_distance=150,
    central_gravity=0.2,
    spring_length=200,
    spring_strength=0.05,
    damping=0.09
)

# Generate and display the graph
with st.spinner("Generating interactive graph..."):
    tmp_dir = tempfile.gettempdir()
    path = os.path.join(tmp_dir, "task_graph.html")
    net.save_graph(path)
    
    # Add custom CSS for better display
    st.components.v1.html("""
    <style>
    .vis-network:focus, .vis-network:active {
        outline: none !important;
    }
    .vis-tooltip {
        max-width: 300px;
        padding: 10px;
        border-radius: 5px;
        background-color: #2c3e50;
        color: white;
        font-family: Arial, sans-serif;
        font-size: 12px;
        line-height: 1.4;
    }
    </style>
    """ + open(path, 'r', encoding='utf-8').read(), 
    height=600, 
    scrolling=False)

# Add legend
legend = """
### Legend
- 🟢 Normal Task
- 🟡 Potential Bottleneck
- 🟠 On Critical Path
- 🔴 Critical Bottleneck
"""
st.markdown(legend)

# Add some helpful tips
tips = st.expander("💡 Tips for Better Results")
with tips:
    st.markdown("""
    1. **Break down large tasks** into smaller, more manageable pieces
    2. **Balance workloads** across team members
    3. **Identify parallel paths** to reduce total project time
    4. **Update task estimates** as work progresses for better accuracy
    5. **Review dependencies** to ensure they reflect the actual workflow
    """)

# Add footer
st.markdown("---")
st.caption("AI Collaboration Optimizer v1.0 | Built with Streamlit, NetworkX, and OpenAI")
