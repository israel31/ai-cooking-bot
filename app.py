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

# ... (sqlite3 patch at the top) ...
import streamlit as st
from crewai import Agent, Task, Crew, Process
from langchain_google_genai import ChatGoogleGenerativeAI
import os
import traceback
import litellm # Import litellm

# --- Configure LiteLLM Model Alias ---
# Do this ONCE at the top level of your script, before any LLM calls.
# This tells LiteLLM to treat "models/gemini-1.5-flash" as if it were "gemini/gemini-1.5-flash"
# and "models/gemini-pro" as "gemini/gemini-pro"
# The key in the alias map is what LiteLLM will receive.
# The value is what LiteLLM *should* use for the actual API call.
litellm.model_alias_map = {
    "models/gemini-2.0-flash": "gemini/gemini-2.0-flash",
    "models/gemini-pro": "gemini/gemini-pro"
}
print(f"DEBUG: LiteLLM model_alias_map configured: {litellm.model_alias_map}")
# --- End LiteLLM Configuration ---


# --- Function to get AI Chef's Response ---
def get_chef_recipe(dish_name: str, api_key: str) -> str:
    original_google_api_key_env = os.environ.get("GOOGLE_API_KEY")
    os.environ["GOOGLE_API_KEY"] = api_key # Still good to have for LiteLLM
    print(f"DEBUG: Temporarily set os.environ['GOOGLE_API_KEY']")

    try:
        # Let's stick with gemini-1.5-flash for now, as it's current
        model_name_for_langchain = "gemini-2.0-flash"
        # model_name_for_langchain = "gemini-pro" # Can switch back if needed

        print(f"DEBUG: Initializing ChatGoogleGenerativeAI with model: '{model_name_for_langchain}'")
        llm = ChatGoogleGenerativeAI(
            model=model_name_for_langchain,
            verbose=True,
            temperature=0.7,
            google_api_key=api_key
        )
        # This will print "models/gemini-1.5-flash" or "models/gemini-pro"
        print(f"DEBUG: ChatGoogleGenerativeAI LLM object initialized. Internal model name: {getattr(llm, 'model', 'N/A')}")

        # Using the simplified agent/task for now to confirm LLM call works
        simple_agent = Agent(
            role="Simple Responder",
            goal="Respond to a simple greeting.",
            backstory="You are a friendly AI that just says hello.",
            verbose=True,
            llm=llm,
            allow_delegation=False
        )

        simple_task_description = f"The user said: '{dish_name}'. Respond with a very short, friendly greeting."
        current_task = Task(
            description=simple_task_description,
            expected_output="A short, friendly greeting.",
            agent=simple_agent
        )
        print(f"DEBUG: Task object created: {current_task.description}")

        # Restore the original complex agent/task if the simple one works
        # master_chef = Agent(
        #     role="Chef de Cuisine or Executive Chef",
        #     goal="Provide clear, step-by-step instructions on how to prepare any dish requested by the user.",
        #     backstory="You are a world-renowned chef...",
        #     verbose=True,
        #     llm=llm,
        #     allow_delegation=False
        # )
        # recipe_task_description = (
        #     f"Create a detailed recipe for preparing {dish_name}. "
        #     "The recipe should include: an introduction to the dish, "
        #     "a list of ingredients with quantities (e.g., 2 cups, 100g), step-by-step preparation instructions, "
        #     "cooking time, difficulty level, and any special tips or variations. "
        #     "Ensure the instructions are very clear and easy for a home cook to follow. "
        #     "Format the output nicely, using markdown for headings and lists where appropriate."
        # )
        # current_task = Task(
        #     description=recipe_task_description,
        #     expected_output=f"A comprehensive, well-formatted, and easy-to-follow recipe for {dish_name}.",
        #     agent=master_chef
        # )
        # print(f"DEBUG: Task object created: {current_task.description}")


        current_crew = Crew(
            agents=[simple_agent], # or [master_chef] if using complex task
            tasks=[current_task],
            verbose=True,
            process=Process.sequential
        )
        print(f"DEBUG: Crew object created.")
        print("DEBUG: Crew and Task setup complete. Kicking off crew...")

        result = current_crew.kickoff()

        print(f"DEBUG: Crew kickoff finished. Result: {str(result)}")
        return str(result)

    except Exception as e:
        # ... (your existing exception handling) ...
        error_message = f"Error in get_chef_recipe: {type(e).__name__} - {e}"
        print(f"DEBUG: EXCEPTION CAUGHT IN get_chef_recipe: {error_message}")
        print(f"DEBUG: Full traceback for exception in get_chef_recipe:")
        print(traceback.format_exc())
        st.error(f"An error occurred: {e}")
        return "Sorry, an error occurred during processing."
    finally:
        # ... (your existing finally block to restore GOOGLE_API_KEY) ...
        if original_google_api_key_env is None:
            if os.environ.get("GOOGLE_API_KEY") == api_key:
                 del os.environ["GOOGLE_API_KEY"]
                 print("DEBUG: Restored os.environ['GOOGLE_API_KEY'] by deleting.")
        else:
            os.environ["GOOGLE_API_KEY"] = original_google_api_key_env
            print(f"DEBUG: Restored os.environ['GOOGLE_API_KEY'] to original value: {original_google_api_key_env}")


# --- Streamlit App Interface (remains the same) ---
# ... (no changes needed in the UI part) ...
st.set_page_config(page_title="🍳 AI Master Chef", layout="wide")
st.title("🍳 AI Master Chef Bot")
st.markdown("Ask for any dish, and the AI Master Chef will give you the recipe!")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "What dish would you like to learn how to cook today?"}]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

google_api_key_from_secrets = st.secrets.get("GOOGLE_API_KEY")


# --- TEMPORARY DEBUGGING: PRINT PART OF THE RETRIEVED KEY ---
if google_api_key_from_secrets:
    # Print first 8 and last 4 characters to verify without exposing the whole key in logs if possible
    # For an AIzaSy... key, the first 8 are quite distinct.
    key_preview = f"{google_api_key_from_secrets[:8]}...{google_api_key_from_secrets[-4:]}"
    print(f"DEBUG: Retrieved GOOGLE_API_KEY from st.secrets. Key preview: {key_preview}")
    print(f"DEBUG: Full retrieved key for self-check (REMOVE THIS PRINT FOR PRODUCTION): '{google_api_key_from_secrets}'") # More risky
else:
    print("DEBUG: GOOGLE_API_KEY not found in st.secrets!")
# --- END TEMPORARY DEBUGGING ---


if not google_api_key_from_secrets:
    st.warning("Google API Key not found! Please add it to your Streamlit Cloud secrets (key: GOOGLE_API_KEY).", icon="⚠️")
    st.stop()


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
