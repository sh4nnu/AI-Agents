# file to test if the langgraph package is installed correctly


from langchain_google_genai import ChatGoogleGenerativeAI
# from langchain_openai import ChatOpenAI

from dotenv import load_dotenv

load_dotenv()  # take environment variables from .env.
llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=0)
print(llm.invoke("Hello, world!").content)