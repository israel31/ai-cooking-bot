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
from langchain_google_genai import ChatGoogleGenerativeAI
import os

# --- Function to get AI Chef's Response ---
def get_chef_recipe(dish_name: str, api_key: str) -> str:
    """
    Initializes the CrewAI agent and tasks to get a recipe for the given dish.
    """
    try:
        # Initialize the LLM (Google Gemini)
        # Ensure you have the correct model name.
        # 'gemini-1.5-flash' or 'gemini-1.5-flash-latest' are common.
        # 'gemini-pro' is also an option for potentially more detailed responses.
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash-latest", # Or "gemini-1.5-flash-latest"
            verbose=True,
            temperature=0.7,
            google_api_key=api_key
        )

        # Define the Master Chef Agent
        master_chef = Agent(
            role="Chef de Cuisine or Executive Chef",
            goal="Provide clear, step-by-step instructions on how to prepare any dish requested by the user.",
            backstory=(
                "You are a world-renowned chef with extensive experience in cooking styles from every continent. "
                "You are currently based in Nigeria, bringing a unique fusion perspective. You pride yourself on "
                "making complex dishes accessible to home cooks with detailed, easy-to-follow recipes."
            ),
            verbose=True,
            llm=llm,
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
            verbose=1, # 0 for no logs, 1 for some, 2 for detailed
            process=Process.sequential
        )

        # Kick off the crew's work
        result = cooking_crew.kickoff()
        return result

    except Exception as e:
        st.error(f"An error occurred while generating the recipe: {e}")
        return "Sorry, I couldn't prepare the recipe due to an error. Please check the logs or try again."

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
# IMPORTANT: Users will need to set this in their Streamlit Cloud app settings
google_api_key = st.secrets.get("GOOGLE_API_KEY")

if not google_api_key:
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
            try:
                ai_response = get_chef_recipe(prompt, google_api_key)
                st.markdown(ai_response)
                # Add AI response to history
                st.session_state.messages.append({"role": "assistant", "content": ai_response})
            except Exception as e:
                error_message = f"Sorry, an error occurred: {str(e)}"
                st.error(error_message)
                st.session_state.messages.append({"role": "assistant", "content": error_message})

# Optional: A button to clear chat history
if st.sidebar.button("Clear Chat History"):
    st.session_state.messages = [{"role": "assistant", "content": "What dish would you like to learn how to cook today?"}]
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("Built with [CrewAI](https://www.crewai.com/) & [Streamlit](https://streamlit.io)")
