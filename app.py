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
def get_chef_recipe(dish_name: str, api_key: str) -> str: # dish_name is the user prompt
    original_google_api_key_env = os.environ.get("GOOGLE_API_KEY")
    os.environ["GOOGLE_API_KEY"] = api_key
    print(f"DEBUG: Temporarily set os.environ['GOOGLE_API_KEY']")

    try:
        model_name_for_langchain = "gemini-1.5-flash"
        print(f"DEBUG: Initializing ChatGoogleGenerativeAI with model: '{model_name_for_langchain}'")
        llm = ChatGoogleGenerativeAI(
            model=model_name_for_langchain,
            verbose=True,
            temperature=0.7,
            google_api_key=api_key
        )
        print(f"DEBUG: ChatGoogleGenerativeAI LLM object initialized. Internal model name: {getattr(llm, 'model', 'N/A')}")

        master_chef = Agent(
            role="Simple Responder", # Simpler role
            goal="Respond to a simple greeting.", # Simpler goal
            backstory="You are a friendly AI that just says hello.", # Simpler backstory
            verbose=True,
            llm=llm,
            allow_delegation=False
        )

        # VERY SIMPLE TASK
        simple_task_description = f"The user said: '{dish_name}'. Respond with a very short, friendly greeting. For example, if the user says 'Hi', you say 'Hello there!'."
        print(f"DEBUG: Simple task description: {simple_task_description}")

        recipe_task = Task( # Still named recipe_task for consistency in variable names
            description=simple_task_description,
            expected_output="A short, friendly greeting.",
            agent=master_chef
        )
        print(f"DEBUG: Simple Task object created: {recipe_task}")


        cooking_crew = Crew(
            agents=[master_chef],
            tasks=[recipe_task],
            verbose=True, # Max verbosity
            process=Process.sequential
        )
        print(f"DEBUG: Crew object created: {cooking_crew}")
        print("DEBUG: Crew and Task setup complete. Kicking off crew...") # This is the line we want to see

        result = cooking_crew.kickoff() # THE CALL

        print(f"DEBUG: Crew kickoff finished. Result: {str(result)}") # Print full result for simple task
        return str(result) # Return the raw result for now

    except Exception as e:
        error_message = f"Error in get_chef_recipe: {type(e).__name__} - {e}"
        print(f"DEBUG: EXCEPTION CAUGHT IN get_chef_recipe: {error_message}")
        print(f"DEBUG: Full traceback for exception in get_chef_recipe:")
        import traceback
        print(traceback.format_exc())
        st.error(f"An error occurred: {e}")
        return "Sorry, an error occurred during processing."
    finally:
        if original_google_api_key_env is None:
            if os.environ.get("GOOGLE_API_KEY") == api_key:
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
