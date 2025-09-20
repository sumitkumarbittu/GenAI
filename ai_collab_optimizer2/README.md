# AI Collaboration Optimizer

An intelligent tool that analyzes task dependencies, identifies bottlenecks, and provides AI-powered suggestions to optimize team collaboration and project workflow.

## Features

- 📊 Interactive task dependency visualization
- 🔍 Automatic bottleneck detection
- 🤖 AI-powered optimization suggestions
- ⚡ Real-time analysis and recommendations
- 📱 Responsive web interface

## Prerequisites

- Python 3.8+
- OpenAI API key (for AI suggestions)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/ai-collab-optimizer.git
   cd ai-collab-optimizer
   ```

2. Create and activate a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up your OpenAI API key:
   - Create a `.streamlit` folder in the project root
   - Create a `secrets.toml` file inside it with:
     ```toml
     OPENAI_API_KEY = "your-api-key-here"
     ```
   - Or set it as an environment variable:
     ```bash
     export OPENAI_API_KEY='your-api-key-here'
     ```

## Usage

1. Run the Streamlit app:
   ```bash
   streamlit run app.py
   ```

2. Upload a CSV file with your project tasks or use the example data.

3. View the interactive task graph, bottleneck analysis, and AI suggestions.

## CSV Format

Your CSV should include these columns:
- `task_id`: Unique identifier for each task (integer)
- `name`: Task name/description
- `assigned_to`: Team member responsible
- `estimated_time`: Time estimate in hours (number)
- `dependencies`: Semicolon-separated list of task_ids this task depends on (e.g., "1;3")

Example:
```csv
task_id,name,assigned_to,estimated_time,dependencies
1,Design UI,Alice,5,
2,Build Backend,Bob,8,1
3,API Integration,Charlie,4,2
4,Testing,Dave,3,2;3
5,Documentation,Eve,2,3
```

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
