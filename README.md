# AI Collaboration Optimizer

An intelligent tool that analyzes task dependencies, identifies bottlenecks, and provides AI-powered suggestions to optimize team collaboration and project workflow.

## Features

- 📊 Interactive task dependency visualization using vis-network
- 🔍 Automatic bottleneck and critical path detection
- 🤖 AI-powered optimization suggestions using OpenAI's GPT-3.5
- ⚡ Real-time analysis and recommendations
- 📱 Responsive web interface
- 🔄 Dynamic task dependency graph visualization

## Prerequisites

- Python 3.8+
- OpenAI API key (for AI suggestions)
- Modern web browser (Chrome, Firefox, Safari, or Edge)

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
   - Create a `.env` file in the project root
   - Add your OpenAI API key to the file:
     ```
     OPENAI_API_KEY=your-api-key-here
     ```
   - Or set it as an environment variable before running the app:
     ```bash
     export OPENAI_API_KEY='your-api-key-here'
     ```

## Running the Application

1. Start the Flask development server:
   ```bash
   python app.py
   ```

2. Open your web browser and navigate to:
   ```
   http://localhost:5001
   ```

3. Upload a CSV file with your project tasks or use the example data below.

## CSV Format

Your CSV should include these columns:
- `task_id`: Unique identifier for each task (integer)
- `name`: Task name/description (string)
- `assigned_to`: Team member responsible (string)
- `estimated_time`: Time estimate in hours (number)
- `dependencies`: Semicolon-separated list of task_ids this task depends on (e.g., "1;3")

### Example CSV:
```csv
task_id,name,assigned_to,estimated_time,dependencies
1,Design UI,Alice,5,
2,Build Backend,Bob,8,1
3,API Integration,Charlie,4,2
4,Testing,Dave,3,2;3
5,Documentation,Eve,2,3
```

## How to Use

1. **Upload your project tasks** in CSV format using the upload button
2. **View the interactive task graph** showing dependencies between tasks
3. **Hover over nodes** to see task details
4. **Click on any task** to get AI-powered optimization suggestions
5. **Use the sidebar** to navigate between different views and analyses

## Troubleshooting

- If the AI suggestions aren't working, ensure your OpenAI API key is correctly set in the `.env` file
- Make sure your CSV file follows the required format
- Check the terminal for any error messages if the application doesn't start

## Project Structure

```
ai-collab-optimizer/
├── app.py                # Main Flask application
├── requirements.txt      # Python dependencies
├── .env                  # Environment variables (create this file)
├── .gitignore           
├── uploads/              # Temporary directory for uploaded files
├── static/              
│   ├── css/
│   │   └── style.css    # Custom styles
│   └── js/
│       └── app.js       # Frontend JavaScript
└── templates/
    └── index.html       # Main HTML template
```

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgements

- Built with Flask, NetworkX, and vis-network
- AI-powered by OpenAI GPT-3.5
- Icons by Font Awesome
