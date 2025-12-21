"""Test: OpenRouter API für HELIX v4 llm_client.py"""
import os
import httpx
import asyncio

async def test_openrouter():
    api_key = os.environ.get("HELIX_OPENROUTER_API_KEY")
    if not api_key:
        print("❌ HELIX_OPENROUTER_API_KEY nicht gesetzt")
        return
    
    print("=== OpenRouter Multi-Model Test ===\n")
    
    models = [
        ("openai/gpt-4o-mini", "GPT-4o Mini"),
        ("anthropic/claude-sonnet-4", "Claude Sonnet 4"),
        ("x-ai/grok-2", "Grok 2"),
    ]
    
    async with httpx.AsyncClient() as client:
        for model_id, name in models:
            try:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model_id,
                        "messages": [{"role": "user", "content": "Say 'Hello from HELIX v4!' in exactly those words."}],
                        "max_tokens": 20,
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    cost = data.get("usage", {}).get("cost", 0)
                    print(f"✅ {name}: {content.strip()}")
                    print(f"   Cost: ${cost:.6f}")
                else:
                    print(f"❌ {name}: HTTP {response.status_code}")
                    
            except Exception as e:
                print(f"❌ {name}: {e}")
            
            print()

if __name__ == "__main__":
    asyncio.run(test_openrouter())
