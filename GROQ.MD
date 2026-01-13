import asyncio
from dotenv import load_dotenv
from agents import AsyncOpenAI, OpenAIChatCompletionsModel, RunConfig, Agent, Runner

load_dotenv()

# 1. Setup Groq API Key
# Get this for free at https://console.groq.com/
# groq_api_key = os.getenv("GROQ_API_KEY")

if not groq_api_key:
    raise ValueError("GROQ_API_KEY is not set in your .env file.")

# 2. Initialize the client for Groq
# Note: Groq is fully OpenAI-compatible
external_client = AsyncOpenAI(
    api_key=groq_api_key,
    base_url="https://api.groq.com/openai/v1",
)

# 3. Define the Model
# Recommended: 'llama-3.3-70b-versatile' or 'llama-3.1-8b-instant'
model = OpenAIChatCompletionsModel(
    model="llama-3.3-70b-versatile",
    openai_client=external_client,
)

# 4. Optional: Run Configuration
config = RunConfig(
    model=model,
)

# 5. Define your Agent
groq_agent = Agent(
    name="GroqSpeedster",
    instructions="You are a high-speed assistant. Keep answers concise.",
    model=model
)

async def main():
    # Run the agentic loop
    result = await Runner.run(groq_agent, "Iqbal ka koi shair likh kar do")
    print(f"Agent: {result.final_output}")
    # print(f"Trace: {result.last_agent.name}")

if __name__ == "__main__":
    asyncio.run(main())