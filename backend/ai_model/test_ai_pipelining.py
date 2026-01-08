from backend.retrieval.interactive_retriever import InteractiveRetriever
from backend.ai_model.agent_controller import AgentController

retriever = InteractiveRetriever(collection_name="lollllll")
agent = AgentController(retriever)

while True:
    q = input("\n🧠 Ask: ")
    if q.lower() in ("exit", "quit"):
        break

    result = agent.answer(q)

    print("\n🤖 ANSWER:")
    print(result["answer"])
    print("\n📚 CITATIONS:")
    for c in result["citations"]:
        print(f"- {c['doc']} (page {c['page']})")
    print("🔐 Confidence:", result["confidence"])
