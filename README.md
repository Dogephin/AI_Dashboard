# ITP-Projek

## Set up

- Install dependencies using `pip install -r requirements.txt`

## Environment Variables

Create .env file in root folder

Include the following:

1. DEEPSEEK_API_KEY=
2. DB_HOST=
3. DB_PORT=
4. DB_USER=
5. DB_PASSWORD=
6. DB_DATABASE=

## Installing Ollama for Local DeepSeek LLM

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
