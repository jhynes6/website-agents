import os
from getpass import getpass
from pinecone import Pinecone

base_url = 'https://api.pinecone.io'
pinecone_api_key = os.environ.get("PINECONE_API_KEY")


if not api_key:
    raise ValueError("PINECONE_API_KEY environment variable is not set")

pc = Pinecone(api_key=api_key, base_url=base_url)

def get_pinecone_api_key():
    """
    Get Pinecone API key from environment variable or prompt user for input.
    Returns the API key as a string.

    Only necessary for notebooks. When using Pinecone yourself, 
    you can use environment variables or the like to set your API key.
    """
    api_key = os.environ.get("PINECONE_API_KEY")
    
    if api_key is None:
        try:
            # Try Colab authentication if available
            from pinecone_notebooks.colab import Authenticate
            Authenticate()
            # If successful, key will now be in environment
            api_key = os.environ.get("PINECONE_API_KEY")
        except ImportError:
            # If not in Colab or authentication fails, prompt user for API key
            print("Pinecone API key not found in environment.")
            api_key = getpass("Please enter your Pinecone API key: ")
            # Save to environment for future use in session
            os.environ["PINECONE_API_KEY"] = api_key
    
    return api_key

api_key = get_pinecone_api_key()
/Users/hynes/Downloads/lawson_case_study_2023.pdf




pc = Pinecone(
    # source_tag isn't necessary for production workloads, so feel free to remove later
    source_tag="pinecone_examples:docs:langchain_retrieval_agent",
    api_key=api_key)


assistant_list = pc.assistant.list_assistants()


assistant_exists = True if "textbook-assistant" in [assistant.name for assistant in assistant_list] else False

if not assistant_exists:
    assistant = pc.assistant.create_assistant(
        assistant_name="textbook-assistant", 
        instructions="Help answer questions about provided textbooks with aim toward creating study guides and grounded learning materials", # Description or directive for the assistant to apply to all responses.
        region="us", # Region to deploy assistant. Options: "us" (default) or "eu".
        timeout=30 # Maximum seconds to wait for assistant status to become "Ready" before timing out.
        
    )

assistant = pc.assistant.Assistant(
    assistant_name="textbook-assistant", 
)


url = "https://assets.openstax.org/oscms-prodcms/media/documents/Introduction_To_Computer_Science_-_WEB.pdf"


import requests

response = requests.get(url)

with open("textbook.pdf", "wb") as f:
    f.write(response.content)
