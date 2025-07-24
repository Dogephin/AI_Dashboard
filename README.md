# PacificMeta Game Analysis Dashboard

## 📄 Table of Contents

- [PacificMeta Game Analysis Dashboard](#pacificmeta-game-analysis-dashboard)
  - [📄 Table of Contents](#-table-of-contents)
  - [🚀 Setup Instructions](#-setup-instructions)
  - [🗃️ Project Structure](#️-project-structure)
  - [🧩 Core Features](#-core-features)
    - [📊 Overall Analytics](#-overall-analytics)
    - [🎮 Minigame Analysis](#-minigame-analysis)
    - [👤 User Analysis](#-user-analysis)
    - [⚙️ Settings Panel](#️-settings-panel)
    - [🧠 AI Integration](#-ai-integration)
  - [🧹 Caching System](#-caching-system)
  - [🧠 Using DeepSeek with API](#-using-deepseek-with-api)
  - [💻 Installing Ollama for Local DeepSeek LLM](#-installing-ollama-for-local-deepseek-llm)

## 🚀 Setup Instructions

1. Clone the Repository

    ```bash
    git clone https://github.com/Dogephin/ITP-Projek.git
    ```

2. Install Dependencies

    ```bash
    pip install -r requirements.txt
    ```

3. Configure Environment Variables

    Create a `.env` file in the **root directory** with the following variables:

    ```env
    DEEPSEEK_API_KEY=your-api-key
    DB_HOST=your-database-host
    DB_PORT=3306
    DB_USER=your-db-user
    DB_PASSWORD=your-db-password
    DB_DATABASE=your-db-name
    OLLAMA_PATH=C:/Users/<your-username>/AppData/Local/Programs/Ollama/ollama.exe
    ```

    > ❗ All environment variables are required. The app will raise an error if any are missing.

4. Run the app

    ```bash
    python app.py
    ```

## 🗃️ Project Structure

```graphql
├── app.py                      # Main entrypoint
├── config.py                   # Environment configuration
├── analysis/                   # Logic for AI analysis
│   ├── minigames_analysis.py
│   ├── overall_analysis.py
│   └── user_analysis.py
├── routes/                     # Flask routes
│   ├── home.py
│   ├── minigame.py
│   ├── overall.py
│   ├── settings.py
│   └── user.py
├── utils/
│   ├── db.py                   # Database initialisation
│   ├── cache.py                # Cache management, cache key generation
│   ├── context.py              # Helper function for retrieving LLM client
│   └── llm.py                  # LLM initialisation
├── templates/                  # HTML Jinja templates
├── static/                     # CSS, JS, assets
├── requirements.txt            # Python dependencies
└── .env                        # Environment variables
```

## 🧩 Core Features

### 📊 Overall Analytics

- Average vs Max scores per minigame
- Error frequency heatmap over time
- Performance vs duration scatter plot
- AI summary of user training behavior

### 🎮 Minigame Analysis

- Summary statistics: attempts, scores, completion rates
- Top minor and severe errors
- AI-generated executive summaries per game
- Search & Sort minigames by name or average score for quick lookup
- Filtering Options (**Total Attempts**, **Completion Rate**, **Average Score**, **Failed**) for easier navigation.

### 👤 User Analysis

- Game-specific and overall assessment
- Trend analysis across attempts
- Single attempt AI analysis
- Bulk AI evaluation with strengths/weakness insights

### ⚙️ Settings Panel

- Toggle between `API` and `LOCAL` query type
- One-click cache clearing

### 🧠 AI Integration

- Switch between DeepSeek API or local LLMs via Ollama
- Caching of AI responses to avoid repeated API calls for the same query
- Regeneration of AI responses from UI
- Download AI responses to text file for future analysis

## 🧹 Caching System

- AI responses are cached to `llm_cache/`

- Caching configuration in `app.config`:

    ```python
    CACHE_TYPE = "FileSystemCache" # Cache locally
    CACHE_DIR = "llm_cache" # Directory where cache records are stored
    CACHE_DEFAULT_TIMEOUT = 3600  # Cache expiry in seconds
    CACHE_THRESHOLD = 20 # Max number of cache records
    ```

  - In the code above, cached LLM responses auto-expire after **1 hour** or when **more than 20 entries** exist.

## 🧠 Using DeepSeek with API

If using API-based LLM analysis:

- Set `DEEPSEEK_API_KEY` in `.env`
- Start app and select `API` in [settings](http://127.0.0.1:5000/settings)

## 💻 Installing Ollama for Local DeepSeek LLM

1. **Download and Install Ollama**

    - Download Ollama from: <https://ollama.com/download>

2. **Configure the Path to `ollama.exe`**

    - Add the path to the `ollama.exe` executable in your `.env` file. For example:

        ```env
        OLLAMA_PATH=C:/Users/<your-username>/AppData/Local/Programs/Ollama/ollama.exe
        ```

3. **Install a DeepSeek Model**

    - Browse and choose a DeepSeek model from the library: <https://ollama.com/library/deepseek-r1>

    - Open a terminal and run the following command to download the model:

        ```bash
        ollama pull deepseek-r1:14b
        ```

        > **Change the model name to the DeepSeek model you want**

4. **Configure the Application**

    - Launch the app and navigate to the [settings page](http://127.0.0.1:5000/settings).

    - Set the AI type to `LOCAL` and select the name of the installed model from the dropdown.

---
