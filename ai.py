import requests

def ask_ai(question):
    """Simple DeepSeek R1 function"""
    API_KEY = " " #your_DeepSeekapi_key_here👈 
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek/deepseek-r1:free",
                "messages": [{"role": "user", "content": question}]
            }
        )
        return response.json()["choices"][0]["message"]["content"]
    except:
        return "Sorry, I can't answer right now"
