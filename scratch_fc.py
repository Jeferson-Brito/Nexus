import os
import sys
import django

# Setup django to access settings
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nexus.settings')
django.setup()

from google import genai
from google.genai import types
from django.conf import settings

client = genai.Client(api_key=settings.GEMINI_API_KEY)

def get_current_weather(location: str) -> str:
    """Returns the current weather in the given location."""
    return f"The weather in {location} is 22C and sunny."

def change_password(new_password: str) -> str:
    """Altera a senha do usuario."""
    return "Senha alterada com sucesso."

prompt = "Qual é o clima em São Paulo e depois altere minha senha para 123456"

response = client.models.generate_content(
    model='gemini-2.5-flash',
    contents=prompt,
    config=types.GenerateContentConfig(
        tools=[get_current_weather, change_password],
        temperature=0
    )
)

print("Text:", response.text)
if response.function_calls:
    for fc in response.function_calls:
        print("Function Call:", fc.name, fc.args)
