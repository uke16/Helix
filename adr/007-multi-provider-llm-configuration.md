# ADR-007: Multi-Provider LLM Configuration

**Status:** Akzeptiert  
**Datum:** 2025-12-21  
**Bezug:** ADR-000, ADR-004

---

## Kontext

HELIX v4 soll flexibel verschiedene LLM-Provider nutzen können:
- OpenRouter (Default, viele Models)
- Anthropic (Direkt)
- OpenAI (Direkt)
- xAI/Grok
- Google Gemini
- Lokale Models

Der Consultant soll bei Escalation auch das Model wechseln können.

---

## Entscheidung

### Provider-Konfiguration

```yaml
# config/llm-providers.yaml

# Globale Defaults
defaults:
  provider: "openrouter"
  model: "openai/gpt-4o"
  temperature: 0.7
  max_tokens: 4096

# Provider-Definitionen
providers:
  openrouter:
    name: "OpenRouter"
    base_url: "https://openrouter.ai/api/v1"
    api_key_env: "OPENROUTER_API_KEY"
    api_format: "openai"              # OpenAI-kompatibles Format
    models:
      gpt-4o:
        id: "openai/gpt-4o"
        context_window: 128000
        cost_per_1k_input: 0.005
        cost_per_1k_output: 0.015
      gpt-4o-mini:
        id: "openai/gpt-4o-mini"
        context_window: 128000
        cost_per_1k_input: 0.00015
        cost_per_1k_output: 0.0006
      claude-sonnet:
        id: "anthropic/claude-sonnet-4"
        context_window: 200000
        cost_per_1k_input: 0.003
        cost_per_1k_output: 0.015
      claude-opus:
        id: "anthropic/claude-opus-4"
        context_window: 200000
        cost_per_1k_input: 0.015
        cost_per_1k_output: 0.075
      grok-2:
        id: "x-ai/grok-2"
        context_window: 131072
        cost_per_1k_input: 0.002
        cost_per_1k_output: 0.010
        
  anthropic:
    name: "Anthropic Direct"
    base_url: "https://api.anthropic.com/v1"
    api_key_env: "ANTHROPIC_API_KEY"
    api_format: "anthropic"           # Native Anthropic Format
    models:
      claude-sonnet:
        id: "claude-sonnet-4-20250514"
        context_window: 200000
      claude-opus:
        id: "claude-opus-4-20250514"
        context_window: 200000
        
  openai:
    name: "OpenAI Direct"
    base_url: "https://api.openai.com/v1"
    api_key_env: "OPENAI_API_KEY"
    api_format: "openai"
    models:
      gpt-4o:
        id: "gpt-4o"
        context_window: 128000
      gpt-4o-mini:
        id: "gpt-4o-mini"
        context_window: 128000
      o1:
        id: "o1"
        context_window: 200000
        api_format: "openai-o1"       # Spezialformat für Reasoning
        
  xai:
    name: "xAI (Grok)"
    base_url: "https://api.x.ai/v1"
    api_key_env: "XAI_API_KEY"
    api_format: "openai"
    models:
      grok-2:
        id: "grok-2"
        context_window: 131072
        
  google:
    name: "Google Gemini"
    base_url: "https://generativelanguage.googleapis.com/v1beta"
    api_key_env: "GOOGLE_API_KEY"
    api_format: "google"              # Google-spezifisches Format
    models:
      gemini-pro:
        id: "gemini-1.5-pro"
        context_window: 2000000
      gemini-flash:
        id: "gemini-1.5-flash"
        context_window: 1000000

# Model-Aliases für einfache Referenz
aliases:
  "fast": "openrouter:gpt-4o-mini"
  "balanced": "openrouter:gpt-4o"
  "reasoning": "openrouter:claude-sonnet"
  "complex": "openrouter:claude-opus"
  "cheap": "openrouter:gpt-4o-mini"
```

### Environment Variables (.env)

```bash
# .env - Migriert von helix-v3

# OpenRouter (Default)
OPENROUTER_API_KEY=sk-or-v1-xxxxx

# Direct Providers (Optional)
ANTHROPIC_API_KEY=sk-ant-xxxxx
OPENAI_API_KEY=sk-xxxxx
XAI_API_KEY=xai-xxxxx
GOOGLE_API_KEY=AIzaxxxxx

# Default Model (kann überschrieben werden)
HELIX_DEFAULT_MODEL=openrouter:gpt-4o
```

### Migration von v3

```bash
#!/bin/bash
# scripts/migrate-env.sh

V3_ENV="/home/aiuser01/helix-v3/.env"
V4_ENV="/home/aiuser01/helix-v4/.env"

if [ -f "$V3_ENV" ]; then
    echo "Migriere .env von v3..."
    
    # Keys extrahieren
    grep "OPENROUTER_API_KEY" "$V3_ENV" >> "$V4_ENV"
    grep "ANTHROPIC_API_KEY" "$V3_ENV" >> "$V4_ENV"
    grep "OPENAI_API_KEY" "$V3_ENV" >> "$V4_ENV"
    
    echo "✅ .env migriert"
else
    echo "❌ v3 .env nicht gefunden"
fi
```

### Model-Selection pro Phase

```yaml
# In phases.yaml kann pro Phase ein Model gewählt werden

phases:
  - id: "01-consultant"
    config:
      model: "reasoning"            # Alias → claude-sonnet
      
  - id: "02-developer"
    config:
      model: "openrouter:gpt-4o"    # Explizit
      
  - id: "03-reviewer"
    config:
      model: "openrouter:claude-sonnet"  # Anderes Model für Review!
```

### Escalation Model-Switch

```python
# escalation.py - Model-Wechsel bei Stufe 1

async def consultant_decides_model_switch(
    current_model: str,
    failure_analysis: dict,
    available_models: list[str]
) -> dict | None:
    """Consultant entscheidet ob Model gewechselt werden soll."""
    
    # Consultant analysiert
    prompt = f"""
    Der Developer mit Model '{current_model}' ist 3x gescheitert.
    
    Failure-Analyse:
    {json.dumps(failure_analysis, indent=2)}
    
    Verfügbare Models:
    {json.dumps(available_models, indent=2)}
    
    Soll ein anderes Model versucht werden?
    Falls ja, welches und warum?
    
    Antworte als JSON:
    {{
      "switch_model": true/false,
      "new_model": "provider:model",
      "reasoning": "..."
    }}
    """
    
    response = await run_consultant_query(prompt)
    return json.loads(response)


# Model-Empfehlungen basierend auf Failure-Typ
MODEL_RECOMMENDATIONS = {
    "syntax_error": {
        "from": ["gpt-4o-mini", "grok-2"],
        "to": "claude-sonnet",
        "reason": "Claude ist besser für sauberen Code"
    },
    "logic_error": {
        "from": ["gpt-4o", "gpt-4o-mini"],
        "to": "claude-opus",
        "reason": "Opus hat besseres Reasoning"
    },
    "complex_refactor": {
        "from": ["*"],
        "to": "claude-sonnet",
        "reason": "Claude versteht große Codebasen besser"
    },
    "api_integration": {
        "from": ["claude-*"],
        "to": "gpt-4o",
        "reason": "GPT-4 hat mehr API-Beispiele gesehen"
    }
}
```

### LLM Client Wrapper

```python
# llm_client.py

from dataclasses import dataclass
from typing import AsyncIterator

@dataclass
class ModelConfig:
    provider: str
    model_id: str
    base_url: str
    api_key: str
    api_format: str
    context_window: int
    cost_per_1k_input: float
    cost_per_1k_output: float

class LLMClient:
    """Unified LLM Client für alle Provider."""
    
    def __init__(self, config_path: Path = None):
        self.config = self._load_config(config_path)
        self._clients = {}
    
    def _load_config(self, config_path: Path) -> dict:
        if config_path is None:
            config_path = HELIX_ROOT / "config" / "llm-providers.yaml"
        return yaml.safe_load(config_path.read_text())
    
    def resolve_model(self, model_spec: str) -> ModelConfig:
        """Löst Model-Spezifikation auf (Alias oder explizit)."""
        
        # Alias?
        if model_spec in self.config.get("aliases", {}):
            model_spec = self.config["aliases"][model_spec]
        
        # Format: "provider:model" oder nur "model" (dann default provider)
        if ":" in model_spec:
            provider, model = model_spec.split(":", 1)
        else:
            provider = self.config["defaults"]["provider"]
            model = model_spec
        
        provider_config = self.config["providers"][provider]
        model_config = provider_config["models"][model]
        
        return ModelConfig(
            provider=provider,
            model_id=model_config["id"],
            base_url=provider_config["base_url"],
            api_key=os.getenv(provider_config["api_key_env"]),
            api_format=model_config.get("api_format", provider_config["api_format"]),
            context_window=model_config.get("context_window", 128000),
            cost_per_1k_input=model_config.get("cost_per_1k_input", 0.01),
            cost_per_1k_output=model_config.get("cost_per_1k_output", 0.03),
        )
    
    async def complete(
        self,
        model_spec: str,
        messages: list[dict],
        **kwargs
    ) -> str:
        """Führt Completion mit beliebigem Model aus."""
        
        config = self.resolve_model(model_spec)
        
        if config.api_format == "openai":
            return await self._complete_openai(config, messages, **kwargs)
        elif config.api_format == "anthropic":
            return await self._complete_anthropic(config, messages, **kwargs)
        elif config.api_format == "google":
            return await self._complete_google(config, messages, **kwargs)
        else:
            raise ValueError(f"Unknown API format: {config.api_format}")
    
    async def _complete_openai(self, config: ModelConfig, messages: list, **kwargs):
        """OpenAI-kompatible Completion (OpenRouter, OpenAI, xAI)."""
        
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{config.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {config.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": config.model_id,
                    "messages": messages,
                    **kwargs
                }
            )
            
            data = response.json()
            return data["choices"][0]["message"]["content"]
    
    async def _complete_anthropic(self, config: ModelConfig, messages: list, **kwargs):
        """Native Anthropic Completion."""
        
        import anthropic
        
        client = anthropic.AsyncAnthropic(
            api_key=config.api_key,
            base_url=config.base_url
        )
        
        # Konvertiere OpenAI-Messages zu Anthropic-Format
        system = None
        anthropic_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                anthropic_messages.append(msg)
        
        response = await client.messages.create(
            model=config.model_id,
            system=system,
            messages=anthropic_messages,
            max_tokens=kwargs.get("max_tokens", 4096)
        )
        
        return response.content[0].text
```

### Claude Code Environment Setup

```python
# claude_code_runner.py

def get_claude_code_env(model_spec: str) -> dict:
    """Erstellt Environment für Claude Code basierend auf Model."""
    
    client = LLMClient()
    config = client.resolve_model(model_spec)
    
    env = os.environ.copy()
    
    if config.provider == "openrouter":
        # OpenRouter als "Anthropic Skin"
        env["ANTHROPIC_BASE_URL"] = config.base_url
        env["ANTHROPIC_API_KEY"] = ""  # Muss leer sein!
        env["OPENROUTER_API_KEY"] = config.api_key
        env["ANTHROPIC_MODEL"] = config.model_id
        
    elif config.provider == "anthropic":
        # Direkte Anthropic API
        env["ANTHROPIC_API_KEY"] = config.api_key
        env["ANTHROPIC_MODEL"] = config.model_id
        
    else:
        # Andere Provider via OpenRouter routen
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        env["ANTHROPIC_BASE_URL"] = "https://openrouter.ai/api/v1"
        env["ANTHROPIC_API_KEY"] = ""
        env["OPENROUTER_API_KEY"] = openrouter_key
        env["ANTHROPIC_MODEL"] = config.model_id
    
    return env
```

---

## Konsequenzen

### Positiv
- Vendor-unabhängig
- Einfacher Model-Wechsel
- Kosten-Transparenz
- Escalation kann Model anpassen

### Negativ
- Verschiedene API-Formate
- Nicht alle Features bei allen Providern
- API-Key Management

---

## Referenzen

- ADR-000: Vision & Architecture
- ADR-004: Escalation Meeting System
- HELIX v3 ADR-023: Multi-Provider


---

## Nachtrag: y-router Integration (2025-12-21)

### Problem

Claude Code CLI unterstützt nativ nur die Anthropic API. OpenRouter nutzt aber 
ein leicht anderes Format.

### Lösung: y-router

**y-router** ist ein lokaler Proxy der das Anthropic-Format in OpenAI-Format 
umwandelt und an OpenRouter weiterleitet.

```
Claude Code CLI
      │
      │ Anthropic API Format
      ▼
┌─────────────────┐
│   y-router      │  localhost:8787
│   (Docker)      │
└────────┬────────┘
         │
         │ OpenAI API Format
         ▼
┌─────────────────┐
│   OpenRouter    │  openrouter.ai
│   (Cloud)       │
└────────┬────────┘
         │
    ┌────┴────┬────────┬────────┐
    ▼         ▼        ▼        ▼
  GPT-4    Claude   Gemini    Grok
```

### Setup

```bash
# 1. y-router klonen (einmalig)
cd /home/aiuser01/helix-v4
git clone https://github.com/luohy15/y-router.git

# 2. y-router starten
./scripts/start-y-router.sh

# 3. Claude Code mit Model starten
./start-phase-openrouter.sh 01-foundation openai/gpt-4o
```

### Environment Variables

```bash
# Für Claude Code mit y-router:
export ANTHROPIC_BASE_URL="http://localhost:8787"
export ANTHROPIC_API_KEY="$HELIX_OPENROUTER_API_KEY"
export ANTHROPIC_CUSTOM_HEADERS="x-api-key: $ANTHROPIC_API_KEY"
export ANTHROPIC_MODEL="openai/gpt-4o"  # oder anderes Model
```

### Verfügbare Models über OpenRouter

| Model | ID | Stärke |
|-------|----|----|
| GPT-4o | `openai/gpt-4o` | Allrounder |
| GPT-4o Mini | `openai/gpt-4o-mini` | Schnell & günstig |
| Claude Sonnet 4 | `anthropic/claude-sonnet-4` | Coding |
| Claude 3.5 Sonnet | `anthropic/claude-3.5-sonnet` | Coding |
| Gemini 2.0 Flash | `google/gemini-2.0-flash-001` | Schnell |
| Llama 3.3 70B | `meta-llama/llama-3.3-70b-instruct` | Open Source |

### Getestet und funktioniert

- ✅ GPT-4o-mini
- ✅ GPT-4o  
- ✅ Claude Sonnet 4
- ✅ Gemini 2.0 Flash

