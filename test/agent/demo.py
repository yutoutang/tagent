import asyncio

from pi.agent import AgentContext, AgentLoopConfig, agent_loop, default_convert_to_llm, CalculatorTool, EchoTool, \
    dicts_to_agent_messages
from pi.ai import Model
from pi.ai.types import ModelCost, OpenAICompletionsCompat


async def main():
    prompts = [
        {
            "role": "user",
            "content": [{"type": "text", "text": "计算 1 + 1"}],
            "timestamp": 12345,
        }
    ]

    agent_messages = dicts_to_agent_messages(prompts)

    tools = [CalculatorTool(), EchoTool()]

    context: AgentContext = {
        "systemPrompt": "You are a helpful assistant.",
        "messages": [],
        "tools": tools,
    }

    model = Model(
        id="glm-4.7",
        name="GLM-4.7",
        api="openai-completions",
        provider="zai",
        baseUrl="https://api.z.ai/api/coding/paas/v4",
        reasoning=True,
        input=["text"],
        cost=ModelCost(input=0.6, output=2.2, cacheRead=0.11,
                       cacheWrite=0),
        contextWindow=204800,
        maxTokens=131072,
        compat=OpenAICompletionsCompat(supportsDeveloperRole=False,
                                       thinkingFormat="zai"),
    )

    config: AgentLoopConfig = {
        "model": model,
        "convertToLlm": default_convert_to_llm,
        "transformContext": None,
        "apiKey": "cc22fb11057d43cc8c23f56808f73880.jAcYCWFeYtQElItA",
        "getSteeringMessages": None,
        "getFollowUpMessages": None,
    }

    stream = agent_loop(agent_messages, context, config)

    events = []
    async for event in stream:
        print(event)
        events.append(event)


if __name__ == '__main__':
    asyncio.run(main())
