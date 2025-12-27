import os
from gradient import Gradient, AgentDeploymentError, AgentDeploymentTimeoutError

token = os.getenv("GRADIENT_ACCESS_TOKEN")
if not token:
    raise SystemExit("Set GRADIENT_ACCESS_TOKEN to your DO token")

client = Gradient(access_token=token)

try:
    agent_resp = client.agents.create(
        name="gradient-sdk-test",
        instruction="You are a helpful assistant",
        model_uuid="1b07e52b-73c5-11f0-b074-4e013e2ddde4",
        region="nyc1",  # use tor1, since other regions failed for agents
    )
    agent_id = agent_resp.agent.uuid if agent_resp.agent else None
    print(f"Created agent: {agent_id}")

    if agent_id:
        print("Waiting for deployment...")
        ready_agent = client.agents.wait_until_ready(
            agent_id,
            poll_interval=5.0,
            timeout=300.0,
        )
        if ready_agent.agent and ready_agent.agent.deployment:
            print(f"Ready. Status: {ready_agent.agent.deployment.status}")
            print(f"Agent URL: {ready_agent.agent.url}")
except AgentDeploymentError as e:
    print(f"Deployment failed: {e}, status={e.status}")
except AgentDeploymentTimeoutError as e:
    print(f"Timed out: {e}, agent_id={e.agent_id}")
except Exception as e:
    print(f"Unexpected error: {e}")