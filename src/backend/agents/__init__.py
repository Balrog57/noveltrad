"""Agent implementations.

Each agent is an isolated subprocess; agents share state only via the
State Store (mediated by the orchestrator) and exchange lightweight
{chunk_id, action} messages through multiprocessing queues.
"""
