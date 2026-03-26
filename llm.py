from groq import Groq
from langchain.chat_models import init_chat_model
from dotenv import load_dotenv
load_dotenv()

llm=init_chat_model(model="gpt-oss-120b", model_provider="openai")
print(llm.invoke("what is python?"))