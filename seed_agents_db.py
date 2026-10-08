#!/usr/bin/env python3
"""Seed the Agent Hotline database with default agents from seed_agents.json."""
import json
import asyncio
from app.database import async_engine, Base, AsyncSessionLocal
from app.models.agent import Agent


async def seed():
    async with AsyncSessionLocal() as session:
        with open("seed_agents.json") as f:
            data = json.load(f)
        agents = data.get("agents", {})
        for key, agent_data in agents.items():
            # Check if agent with same token exists
            result = await session.execute(
                __import__("sqlalchemy").select(Agent).where(Agent.token == agent_data["token"])
            )
            existing = result.scalar_one_or_none()
            if existing:
                print(f"Agent '{agent_data['name']}' already exists, skipping.")
                continue
            agent = Agent(
                token=agent_data.get("token", ""),
                endpoint=agent_data.get("endpoint", ""),
                environment=agent_data.get("environment", "local"),
                js_source=agent_data.get("js_source", ""),
                script=agent_data.get("script", ""),
                category=agent_data.get("category", "general"),
                language=agent_data.get("language", "en"),
                name=agent_data.get("name", key),
                mode=agent_data.get("mode", "text"),
                finger_hole=agent_data.get("finger-hole"),
                scrollable_agent_card=agent_data.get("scrollable-agent-card"),
                info=agent_data.get("info"),
                is_active=True,
            )
            session.add(agent)
            print(f"Added agent: {agent.name}")
        await session.commit()
        print("Seeding complete.")


if __name__ == "__main__":
    asyncio.run(seed())
