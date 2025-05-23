# Try to import and patch sqlite3 before anything else.
# This is a common workaround for ChromaDB/sqlite3 issues on some platforms.
try:
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
    print("Successfully patched sqlite3 with pysqlite3.") # For logging
except ImportError:
    print("pysqlite3 not found, ChromaDB might face issues.") # For logging
    pass

import streamlit as st
from crewai import Agent, Task, Crew, Process
from langchain_google_genai import ChatGoogleGenerativeAI # Make sure this is the one you're using
import os
import traceback # For detailed error logging

# --- Function to get AI Chef's Response ---
def get_chef_recipe(dish_name: str, api_key: str) -> str:
    """
    Initializes the CrewAI agent and tasks to get a recipe for the given dish.
    """
    try:
        # STEP 1: Define the model name CLEARLY and SIMPLY
        # For Google AI Studio API keys (like yours: AIzaSy...),
        # the model name for ChatGoogleGenerativeAI should be just the base name.
        model_name_for_langchain = "gemini-1.5-flash"
        # model_name_for_langchain = "gemini-pro" # You can also try this as an alternative

        print(f"DEBUG: Initializing ChatGoogleGenerativeAI with model: '{model_name_for_langchain}'")

        # STEP 2: Initialize ChatGoogleGenerativeAI
        llm = ChatGoogleGenerativeAI(
            model=model_name_for_langchain,
            verbose=True, # Good for Langchain's own debugging if needed
            temperature=0.7,
            google_api_key=api_key
            # convert_system_message_to_human=True # Sometimes needed for Gemini, can try adding if issues persist AFTER fixing model name
        )

        print(f"DEBUG: ChatGoogleGenerativeAI LLM object initialized: {llm}")

        # Define the Master Chef Agent
        master_chef = Agent(
            role="Chef de Cuisine or Executive Chef",
            goal="Provide clear, step-by-step instructions on how to prepare any dish requested by the user.",
            backstory=(
                "You are a world-renowned chef with extensive experience in cooking styles from every continent. "
                "You are currently based in Nigeria, bringing a unique fusion perspective. You pride yourself on "
                "making complex dishes accessible to home cooks with detailed, easy-to-follow recipes."
            ),
            verbose=True, # Good for CrewAI's own debugging
            llm=llm,      # Pass the Langchain LLM object here
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
            verbose=2, # Increased verbosity for CrewAI to see more of its steps
            process=Process.sequential
        )

        print("DEBUG: Crew and Task setup complete. Kicking off crew...")
        result = cooking_crew.kickoff()
        print(f"DEBUG: Crew kickoff finished. Result snippet: {str(result)[:200]}...")
        return result

    except Exception as e:
        error_message = f"Error in get_chef_recipe: {type(e).__name__} - {e}"
        print(f"DEBUG: EXCEPTION CAUGHT IN get_chef_recipe: {error_message}")
        print("DEBUG: Full traceback for exception in get_chef_recipe:")
        print(traceback.format_exc()) # This will print the full traceback to Streamlit Cloud logs

        st.error(f"An error occurred while generating the recipe. Details: {e}")
        return "Sorry, I couldn't prepare the recipe due to an error. Please check the logs and try again."

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
google_api_key = st.secrets.get("GOOGLE_API_KEY")

if not google_api_key:
    st.warning("Google API Key not found! Please add it to your Streamlit Cloud secrets (key: GOOGLE_API_KEY).", icon="⚠️")
    st.stop()

# Get user input
if prompt := st.chat_input("e.g., Jollof Rice, Spaghetti Carbonara, etc."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Chef is thinking... 🧑‍🍳"):
            ai_response = get_chef_recipe(prompt, google_api_key)
            st.markdown(ai_response)
            st.session_state.messages.append({"role": "assistant", "content": ai_response})

if st.sidebar.button("Clear Chat History"):
    st.session_state.messages = [{"role": "assistant", "content": "What dish would you like to learn how to cook today?"}]
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("Built with [CrewAI](https://www.crewai.com/) & [Streamlit](https://streamlit.io)")
