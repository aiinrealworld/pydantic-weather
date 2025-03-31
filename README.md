# Pydantic Weather Agent

This project implements a weather agent that can provide weather information for a given location using a combination of tools and APIs. It leverages `pydantic-ai` for agent management, external APIs for weather data and geocoding, and offers both a command-line interface and a voice-enabled Streamlit application. It also includes an n8n workflow for potential integration with other systems.

## Components Description

*   **`weather_agent.py`**: This file contains the core logic of the weather agent.
    *   It defines an `Agent` using `pydantic-ai` to manage the interaction with external tools and APIs.
    *   It uses tools like `get_lat_lng` (to fetch latitude and longitude from a location description) and `get_weather` (to fetch weather data from given coordinates).
    *   It uses `logfire` for observability.
    *   It also defines a `get_forecast` tool to get weather forecast for the next five days
    *   The agent is configured with a system prompt to guide its responses.
    *   It includes a command-line interface for interacting with the agent.

*   **`weather_agent_voice.py`**: This file implements a voice-enabled Streamlit application that allows users to interact with the weather agent using their voice.
    *   It uses the `speech_recognition` library to convert voice input to text.
    *   It uses the `gTTS` library to convert the agent's text responses to speech.
    *   It uses Streamlit to create a user-friendly interface for interacting with the agent.
    *   It maintains chat history using Streamlit's session state.

*   **`Weather_Agent_n8n.json`**: This file defines an n8n workflow that can be used to integrate the weather agent with other systems.
    *   It includes nodes for receiving chat messages, interacting with the OpenAI language model, using the `get_lat_lng` and `get_weather` tools, and managing memory.
    *   It shows how the agent could be triggered by events in other systems and how its responses could be used to automate other tasks.

*   **`requirements.txt`**: This file lists the Python dependencies required to run the project.
    *   `pydantic_ai`: For creating and managing AI agents.
    *   `python-dotenv`: For loading environment variables from a `.env` file.
    *   `httpx`: For making asynchronous HTTP requests to external APIs.
    *   `streamlit`: For creating the voice-enabled web application.
    *   `speech_recognition`: For converting voice input to text.
    *   `gTTS`: For converting text responses to speech.
    *   `logfire`: For observability

*   **`.env`**: This file stores sensitive information, such as API keys, as environment variables. An `.env.example` file is provided as a template.

## Setup Environment

1.  **Clone the repository:**

    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```

2.  **Create a virtual environment (recommended):**

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate  # On Linux/macOS
    .venv\Scripts\activate  # On Windows
    ```

3.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Create a `.env` file:**

    *   Copy the `.env.example` file to a new file named `.env`:

        ```bash
        cp .env.example .env
        ```

    *   Edit the `.env` file and fill in the required API keys:

        ```
        GEO_API_KEY=<your_geocode_maps_api_key>        # Get one at https://geocode.maps.co/
        WEATHER_API_KEY=<your_tomorrow_io_api_key>    # Get one at https://www.tomorrow.io/weather-api/
        LOGFIRE_TOKEN=<your_logfire_token>              # Optional, for observability
        OPENAI_API_KEY=<your_openai_api_key>            # Required for the n8n workflow
        ```

    *   **Note:** The `LOGFIRE_TOKEN` is optional. If not provided, the agent will still function, but you won't be able to see detailed logs in Logfire. The `OPENAI_API_KEY` is needed if you want to use the n8n workflow, as it uses the OpenAI Chat Model.

## How to Run

1.  **Run the command-line agent:**

    ```bash
    python weather_agent.py
    ```

    This will start an interactive chat session in your terminal.

2.  **Run the voice-enabled Streamlit application:**

    ```bash
    streamlit run weather_agent_voice.py
    ```

    This will open the Streamlit application in your web browser. You can then interact with the weather agent using your voice or by typing in the text box.

That's the initial `README.md` file. Let me know if you would like me to elaborate on anything or add further sections.