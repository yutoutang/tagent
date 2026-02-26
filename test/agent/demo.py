import asyncio

from pi.agent import AgentContext, AgentLoopConfig, agent_loop, default_convert_to_llm


async def main():
    prompts = [
        {
            "role": "user",
            "content": [{"type": "text", "text": "Hello"}],
            "timestamp": 12345,
        }
    ]

    context: AgentContext = {
        "systemPrompt": "You are a helpful assistant.",
        "messages": [],
        "tools": [],
    }

    config: AgentLoopConfig = {
        "model": {
            "id": "glm-4.7",
            "name": "GLM-4.7",
            "compat": {"supportsDeveloperRole": False, "thinkingFormat": "zai"},
            "api": "openai-completions",
            "baseUrl": "https://api.z.ai/api/coding/paas/v4",
            "provider": "zai",
            "reasoning": True,
            "input": ["text"],
            "cost": {
                "input": 0.6,
                "output": 2.2,
                "cacheRead": 0.11,
                "cacheWrite": 0,
            },
            "contextWindow": 204800,
            "maxTokens": 131072,
        },
        "convertToLlm": default_convert_to_llm,
        "transformContext": None,
        "apiKey": "cc22fb11057d43cc8c23f56808f73880.jAcYCWFeYtQElItA",
        "getSteeringMessages": None,
        "getFollowUpMessages": None,
    }

    stream = agent_loop(prompts, context, config)

    events = []
    async for event in stream:
        print(event)
        events.append(event)


if __name__ == '__main__':
    asyncio.run(main())
