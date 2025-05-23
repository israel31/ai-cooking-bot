# Try to import and patch sqlite3 before anything else.
# This is a common workaround for ChromaDB/sqlite3 issues on some platforms.
try:
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
    print("Successfully patched sqlite3 with pysqlite3.") # For logging
except ImportError:
    print("pysqlite3 not found, ChromaDB might face issues.") # For logging
    pass # Or raise an error if you want to be strict

import streamlit as st
from crewai import Agent, Task, Crew, Process
from crewai.llms import LiteLLM as CrewAILiteLLM # Using CrewAI's LiteLLM wrapper
import os
import traceback # For detailed error logging

# --- Function to get AI Chef's Response ---
def get_chef_recipe(dish_name: str, api_key: str) -> str:
    """
    Initializes the CrewAI agent and tasks to get a recipe for the given dish.
    Uses CrewAI's direct LiteLLM wrapper.
    """
    original_google_api_key_env = os.environ.get("GOOGLE_API_KEY") # Store original, if any

    try:
        # For CrewAI's LiteLLM wrapper, LiteLLM expects "gemini/" prefix for Google AI Studio
        model_for_crewai_litellm = "gemini/gemini-1.5-flash"
        # model_for_crewai_litellm = "gemini/gemini-pro" # Alternative if 1.5-flash has issues or for different capabilities

        print(f"DEBUG: Initializing CrewAI's LiteLLM wrapper with model: '{model_for_crewai_litellm}'")

        # Set the API key as an environment variable for LiteLLM
        # LiteLLM primarily checks os.environ for many API keys including Google's.
        os.environ["GOOGLE_API_KEY"] = api_key

        llm = CrewAILiteLLM(
            model=model_for_crewai_litellm,
            temperature=0.7
            # Note: Some versions/configurations of LiteLLM might also accept an `api_key` parameter directly.
            # If the environment variable method gives issues, you could check documentation for:
            # llm = CrewAILiteLLM(model=..., temperature=..., api_key=api_key)
            # However, for Google, os.environ["GOOGLE_API_KEY"] is the most standard way for LiteLLM.
        )

        print(f"DEBUG: CrewAI LiteLLM object initialized: {llm}")

        # Define the Master Chef Agent
        master_chef = Agent(
            role="Chef de Cuisine or Executive Chef",
            goal="Provide clear, step-by-step instructions on how to prepare any dish requested by the user.",
            backstory=(
                "You are a world-renowned chef with extensive experience in cooking styles from every continent. "
                "You are currently based in Nigeria, bringing a unique fusion perspective. You pride yourself on "
                "making complex dishes accessible to home cooks with detailed, easy-to-follow recipes."
            ),
            verbose=True, # CrewAI agent verbosity
            llm=llm,      # Pass the CrewAI LiteLLM object
            allow_delegation=False
        )

        # Define the Task for the Chef
        recipe_task = Task(
            description=(
                f"Create a detailed recipe for preparing {dish_name}. "
                "The recipe should include: an introduction to the dish, "
                "a list of ingredients with quantities (e.g., 2 cups, 100g), step-by-step preparation instructions, "
                "cooking time, difficulty level, and any special tips or variations. "
                "Ensure the instructions are very clear and easy for a home cook to follow. "
                "Format the output nicely, using markdown for headings and lists where appropriate."
            ),
            expected_output=(
                f"A comprehensive, well-formatted, and easy-to-follow recipe for {dish_name}."
            ),
            agent=master_chef
        )

        # Create and run the Crew
        cooking_crew = Crew(
            agents=[master_chef],
            tasks=[recipe_task],
            verbose=2, # Crew verbosity (0, 1, or 2)
            process=Process.sequential
        )

        print("DEBUG: Crew and Task setup complete. Kicking off crew...")
        result = cooking_crew.kickoff()
        print(f"DEBUG: Crew kickoff finished. Result snippet: {str(result)[:200]}...") # Log a snippet
        return result

    except Exception as e:
        error_message = f"Error in get_chef_recipe: {type(e).__name__} - {e}"
        print(f"DEBUG: EXCEPTION CAUGHT IN get_chef_recipe: {error_message}")
        print("DEBUG: Full traceback for exception in get_chef_recipe:")
        print(traceback.format_exc())

        st.error(f"An error occurred while generating the recipe. Details: {e}")
        return "Sorry, I couldn't prepare the recipe due to an error. Please check the logs and try again."
    finally:
        # Restore the original GOOGLE_API_KEY environment variable state
        if original_google_api_key_env is None:
            # If it wasn't set before, and we set it, remove it
            if os.environ.get("GOOGLE_API_KEY") == api_key: # Check if we were the ones who set it to this value
                del os.environ["GOOGLE_API_KEY"]
        else:
            # If it was set before, restore its original value
            os.environ["GOOGLE_API_KEY"] = original_google_api_key_env
        print(f"DEBUG: GOOGLE_API_KEY environment variable restored (if changed). Current value: {os.environ.get('GOOGLE_API_KEY')}")


# --- Streamlit App Interface ---
st.set_page_config(page_title="🍳 AI Master Chef", layout="wide")
st.title("🍳 AI Master Chef Bot")
st.markdown("Ask for any dish, and the AI Master Chef will give you the recipe!")

# Initialize chat history in session state
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "What dish would you like to learn how to cook today?"}]

# Display past messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Get GOOGLE_API_KEY from Streamlit secrets
# This key will be passed to get_chef_recipe and set as an environment variable temporarily
google_api_key_from_secrets = st.secrets.get("GOOGLE_API_KEY")

if not google_api_key_from_secrets:
    st.warning("Google API Key not found! Please add it to your Streamlit Cloud secrets (key: GOOGLE_API_KEY).", icon="⚠️")
    st.stop() # Stop execution if key is not found

# Get user input
if prompt := st.chat_input("e.g., Jollof Rice, Spaghetti Carbonara, etc."):
    # Add user message to history and display it
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get AI response
    with st.chat_message("assistant"):
        with st.spinner("Chef is thinking... 🧑‍🍳"):
            # Pass the API key from secrets to the function
            ai_response = get_chef_recipe(prompt, google_api_key_from_secrets)
            st.markdown(ai_response)
            # Add AI response to history
            st.session_state.messages.append({"role": "assistant", "content": ai_response})

# Optional: A button to clear chat history
if st.sidebar.button("Clear Chat History"):
    st.session_state.messages = [{"role": "assistant", "content": "What dish would you like to learn how to cook today?"}]
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("Built with [CrewAI](https://www.crewai.com/) & [Streamlit](https://streamlit.io)")
