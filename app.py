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
from langchain_google_genai import ChatGoogleGenerativeAI # Back to this
import os
import traceback # For detailed error logging

# --- Function to get AI Chef's Response ---
def get_chef_recipe(dish_name: str, api_key: str) -> str:
    """
    Initializes the CrewAI agent and tasks to get a recipe for the given dish.
    Uses Langchain's ChatGoogleGenerativeAI.
    """
    # Store original env var for GOOGLE_API_KEY to restore it later
    original_google_api_key_env = os.environ.get("GOOGLE_API_KEY")
    # LiteLLM (used by CrewAI) often picks up the GOOGLE_API_KEY from the environment
    os.environ["GOOGLE_API_KEY"] = api_key
    print(f"DEBUG: Temporarily set os.environ['GOOGLE_API_KEY']")

    try:
        # Model name for ChatGoogleGenerativeAI
        # We know this will internally become "models/gemini-1.5-flash"
        model_name_for_langchain = "gemini-1.5-flash"
        # model_name_for_langchain = "gemini-pro" # Alternative for testing

        print(f"DEBUG: Initializing ChatGoogleGenerativeAI with model: '{model_name_for_langchain}'")

        llm = ChatGoogleGenerativeAI(
            model=model_name_for_langchain,
            verbose=True,
            temperature=0.7,
            google_api_key=api_key # Explicitly pass API key here too
            # convert_system_message_to_human=True # Can try this if LLM responses are odd
        )

        # This debug line showed us that llm.model becomes "models/gemini-1.5-flash"
        print(f"DEBUG: ChatGoogleGenerativeAI LLM object initialized. Internal model name: {getattr(llm, 'model', 'N/A')}")

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

        recipe_task = Task(
            description=(
                f"Create a detailed recipe for preparing {dish_name}. "
                # ... (full description)
            ),
            expected_output=(
                f"A comprehensive, well-formatted, and easy-to-follow recipe for {dish_name}."
            ),
            agent=master_chef
        )

        cooking_crew = Crew(
            agents=[master_chef],
            tasks=[recipe_task],
            verbose=2,
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
        print(traceback.format_exc())
        st.error(f"An error occurred while generating the recipe. Details: {e}")
        return "Sorry, I couldn't prepare the recipe due to an error."
    finally:
        # Restore the original GOOGLE_API_KEY environment variable state
        if original_google_api_key_env is None:
            if os.environ.get("GOOGLE_API_KEY") == api_key: # Check if we were the ones who set it
                 del os.environ["GOOGLE_API_KEY"]
                 print("DEBUG: Restored os.environ['GOOGLE_API_KEY'] by deleting.")
        else:
            os.environ["GOOGLE_API_KEY"] = original_google_api_key_env
            print(f"DEBUG: Restored os.environ['GOOGLE_API_KEY'] to original value: {original_google_api_key_env}")


# --- Streamlit App Interface (remains the same as your last full version) ---
st.set_page_config(page_title="🍳 AI Master Chef", layout="wide")
st.title("🍳 AI Master Chef Bot")
st.markdown("Ask for any dish, and the AI Master Chef will give you the recipe!")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "What dish would you like to learn how to cook today?"}]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

google_api_key_from_secrets = st.secrets.get("GOOGLE_API_KEY")

if not google_api_key_from_secrets:
    st.warning("Google API Key not found! Please add it to your Streamlit Cloud secrets (key: GOOGLE_API_KEY).", icon="⚠️")
    st.stop()

if prompt := st.chat_input("e.g., Jollof Rice, Spaghetti Carbonara, etc."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Chef is thinking... 🧑‍🍳"):
            ai_response = get_chef_recipe(prompt, google_api_key_from_secrets)
            st.markdown(ai_response)
            st.session_state.messages.append({"role": "assistant", "content": ai_response})

if st.sidebar.button("Clear Chat History"):
    st.session_state.messages = [{"role": "assistant", "content": "What dish would you like to learn how to cook today?"}]
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("Built with [CrewAI](https://www.crewai.com/) & [Streamlit](https://streamlit.io)")
