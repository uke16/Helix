"""Test: OpenRouter API - Alle verfügbaren Models"""
import os
import httpx
import asyncio

async def test_models():
    api_key = os.environ.get("HELIX_OPENROUTER_API_KEY")
    
    print("=== OpenRouter Multi-Model Test (HELIX v4) ===\n")
    
    models = [
        ("openai/gpt-4o-mini", "GPT-4o Mini (Fast/Cheap)"),
        ("openai/gpt-4o", "GPT-4o (Best OpenAI)"),
        ("anthropic/claude-sonnet-4", "Claude Sonnet 4"),
        ("anthropic/claude-3.5-sonnet", "Claude 3.5 Sonnet"),
        ("google/gemini-2.0-flash-001", "Gemini 2.0 Flash"),
        ("meta-llama/llama-3.3-70b-instruct", "Llama 3.3 70B"),
    ]
    
    results = []
    
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
                        "messages": [{"role": "user", "content": "Respond with exactly: OK"}],
                        "max_tokens": 5,
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    cost = data.get("usage", {}).get("cost", 0)
                    results.append((name, "✅", f"${cost:.6f}"))
                else:
                    results.append((name, "❌", f"HTTP {response.status_code}"))
                    
            except Exception as e:
                results.append((name, "❌", str(e)[:30]))
    
    print(f"{'Model':<30} {'Status':<5} {'Cost':<12}")
    print("-" * 50)
    for name, status, info in results:
        print(f"{name:<30} {status:<5} {info:<12}")
    
    print("\n=== Fazit ===")
    ok_count = sum(1 for _, s, _ in results if s == "✅")
    print(f"✅ {ok_count}/{len(results)} Models funktionieren über OpenRouter")

if __name__ == "__main__":
    asyncio.run(test_models())
