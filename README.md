# PacificMeta Game Analysis Dashboard

## 📄 Table of Contents

- [PacificMeta Game Analysis Dashboard](#pacificmeta-game-analysis-dashboard)
  - [📄 Table of Contents](#-table-of-contents)
  - [🚀 Setup Instructions](#-setup-instructions)
    - [💻 Method 1: Running the App diectly via Python](#-method-1-running-the-app-diectly-via-python)
    - [🐳 Method 2: Docker Compose Setup](#-method-2-docker-compose-setup)
      - [🔄 Load Balancing Test](#-load-balancing-test)
    - [🔒 Authentication and User Roles](#-authentication-and-user-roles)
      - [🔑 Login and Security](#-login-and-security)
      - [👩‍🏫 User Roles and Data Access](#-user-roles-and-data-access)
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

> [!IMPORTANT]
> There are currently two ways to run the application. The first way is to directly run the app using Python. The second way is to run the application using Docker

### 💻 Method 1: Running the App diectly via Python

1. Clone the Repository

    ```bash
    git clone https://github.com/Dogephin/AI_Dashboard.git
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

### 🐳 Method 2: Docker Compose Setup

> [!TIP]
> This is the recommended way to run the application, as it includes the **Nginx reverse proxy** and **load balancer** and runs the Flask application in a container.

1. Install [Docker Desktop](https://www.docker.com/get-started/) on your computer.

2. Configure Environment Variables
     - Ensure your `.env` file (as described in the previous method) is in the root directory.

3. Build and Run the Containers

    - Ensure that the Docker Engine is up and running in your computer before proceeding.

    - This command below builds the web service (Flask app) and starts all services in detached mode.

        ```bash
        docker-compose up --build -d
        ```

4. Access the Dashboard

    - The dashboard will be available at: <http://localhost:80> (or your host's IP address) because Nginx listens on port 80 and proxies requests to the Flask backend.

#### 🔄 Load Balancing Test

- The setup uses **Nginx** as a reverse proxy to load balance requests across potentially multiple Flask application instances (containers).

- To test if the round-robin load balancing is working, you can scale the web service and hit the `/whoami` endpoint multiple times:

    ```bash
    docker-compose up --scale web=3 -d
    # Then access http://localhost/whoami repeatedly in your browser
    ```

- The response for the `/whoami` route will show a different container hostname each time, confirming that Nginx is distributing the requests.

### 🔒 Authentication and User Roles

- The dashboard uses a session-based authentication system to manage access and tailor the data displayed.

#### 🔑 Login and Security

- Upon launching the application, you will be redirected to the [login page](http://localhost/login).
- All dashboard routes are protected by the `@login_required` decorator.
- User credentials are checked against the `AdminAccount` table using an MD5 hash comparison for the password.

#### 👩‍🏫 User Roles and Data Access

Upon successful login, a session role is assigned based on the username:

| **Role**          | **Username**                                  | **Data Access Scope**                                                   |
|-------------------|-----------------------------------------------|-------------------------------------------------------------------------|
| Admin (`admin`)     | Default (Username does not contain `"teacher"`) | Sees all student data across the application.                           |
| Teacher (`teacher`) | Username contains `"teacher"`                   | Only sees data for students linked to their account via `IMA_Admin_User`. |

## 🗃️ Project Structure

```graphql
├── app.py                      # Main entrypoint
├── config.py                   # Environment configuration
├── Dockerfile                  # Docker image definition for the Flask app 
├── docker-compose.yml          # Defines web (Flask) and nginx services
├── nginx.conf                  # Nginx reverse proxy and load balancer configuration
├── analysis/                   # Logic for AI analysis
│   ├── minigames_analysis.py
│   ├── overall_analysis.py
│   └── user_analysis.py
├── routes/                     # Flask routes
│   ├── home.py
│   ├── login.py                # User login/logout routes
│   ├── minigame.py
│   ├── overall.py
│   ├── settings.py
│   └── user.py
├── utils/
│   ├── auth.py                 # Login required decorator for authentication
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
- Monthly average score trend line for all minigames
- Error vs Completion Time scatter plot
- Top 3 vs Bottom 3 student performance analysis
- Personalized student feedback based on performance
- AI summary of overall user training behaviour

### 🎮 Minigame Analysis

- Summary statistics: attempts, scores, completion rates
- Top minor and severe errors
- Monthly warning trend analysis (Current month vs. Last month)
- AI-generated executive summaries per game
- AI-powered prioritization brief for low-performing minigames
- Search & Sort minigames by name or average score for quick lookup
- Filtering Options (**Total Attempts**, **Completion Rate**, **Average Score**, **Failed**) for easier navigation.

### 👤 User Analysis

- Game-specific and overall assessment
- Trend analysis across attempts
- Single attempt AI analysis
- Bulk AI evaluation with strengths/weakness insights
- AI categorization and recommendation for all time errors
- User grouping based on ID (e.g., 'Staff', 'Year XXXX Cohort').

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
