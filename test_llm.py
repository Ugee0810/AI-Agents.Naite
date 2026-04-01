from dotenv import load_dotenv
import litellm
import os

load_dotenv()
try:
    print(f"Testing LLM with model: gemini/{os.getenv('GEMINI_MODEL')}")
    response = litellm.completion(
        model=f"gemini/{os.getenv('GEMINI_MODEL')}",
        messages=[{"role": "user", "content": "Hello"}],
        api_key=os.getenv('GOOGLE_API_KEY')
    )
    print("Success:", response.choices[0].message.content)
except Exception as e:
    print("Error:", str(e))
