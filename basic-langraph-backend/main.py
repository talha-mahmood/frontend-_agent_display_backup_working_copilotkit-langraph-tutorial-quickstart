from dotenv import load_dotenv
from typing import Annotated, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from typing_extensions import TypedDict
import os
from langsmith import utils
from fastapi import FastAPI, Request
import uvicorn

# --- CopilotKit integration ---
from copilotkit.integrations.fastapi import add_fastapi_endpoint
from copilotkit import CopilotKitSDK, LangGraphAgent
from langgraph.checkpoint.memory import MemorySaver

load_dotenv()

# os.environ["LANGCHAIN_API_KEY"] = "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"
# os.environ["LANGCHAIN_TRACING_V2"] = "true"
# os.environ["LANGCHAIN_PROJECT"] = "multiagent"

utils.tracing_is_enabled()

llm = ChatOpenAI(model="gpt-3.5-turbo")  # or "gpt-4", "gpt-3.5-turbo", etc.

class MessageClassifier(BaseModel):
    message_type: Literal["legal", "technology", "sales", "marketing", "operations", "hr", "finance", "executive"] = Field(
        ...,
        description="Classify if the message requires an legal or technology or sales or marketing or operations or hr or finance or executive."
    )

class State(TypedDict):
    messages: Annotated[list, add_messages]
    message_type: str | None

def classify_message(state: State):
    last_message = state["messages"][-1]
    classifier_llm = llm.with_structured_output(MessageClassifier)
    result = classifier_llm.invoke([
        {
            "role": "system",
            "content": """You are a classification agent in a corporate AI system. Your role is to analyze the user’s message and determine which of the following specialized agents should handle it. Carefully evaluate the intent, language, and domain of the message to make the best decision.

Classify the user message as one of the following categories:

- 'executive': if the query is about business strategy, vision, high-level decision-making, leadership direction, or inter-department coordination.
- 'finance': if the query relates to money, budgeting, expenses, accounting, financial planning, investments, or compliance in financial operations.
- 'hr': if the query involves hiring, employee relations, payroll, workplace issues, HR policies, recruitment, onboarding, or performance management.
- 'operations': if the message focuses on internal process optimization, logistics, supply chain, delivery, workflows, or daily execution tasks.
- 'marketing': if the user asks about promotion, branding, advertising, content creation, customer outreach, social media, or growing audience.
- 'sales': if it involves closing deals, customer leads, CRM, negotiation, pitching, client conversion, or revenue generation.
- 'technology': if the request is about digital infrastructure, IT support, software development, cybersecurity, or system integration.
- 'legal': if it refers to laws, contracts, compliance issues, regulatory requirements, legal risks, or corporate governance.

Return only one of the keywords above based on the user’s intent, like this:
"content": "executive"

Do not include any explanation or extra text—just return the selected keyword exactly.
            """
        },
        {"role": "user", "content": last_message.content}
    ])
    print(f"message type: is {result.message_type}")
    # Do NOT append a [message_type]: ... message to the messages array
    # Just update the state with the message_type
    return {"message_type": result.message_type, "messages": state["messages"]}

def router(state: State):
    message_type = state.get("message_type", "logical")
    next_node = None
    if message_type == "legal": 
        next_node = "legal"
    elif message_type == "technology":
        next_node = "technology"
    elif message_type == "sales":
        next_node = "sales"
    elif message_type == "marketing": 
        next_node = "marketing"
    elif message_type == "operations":
        next_node = "operations"
    elif message_type == "hr":
        next_node = "hr"
    elif message_type == "finance":
        next_node = "finance"
    elif message_type == "executive":
        next_node = "executive"
    # Always return the full state plus the next key for routing
    return {**state, "next": next_node}

def executive_agent(state: State):
    last_message = state["messages"][-1]
    messages = [
        {"role": "system",
         "content": """You are the Chief Executive Agent responsible for overseeing and aligning the entire organization. You think strategically, set goals, and coordinate cross-department efforts. Your decisions shape the direction, culture, and sustainability of the company. Evaluate risks, ensure mission alignment, and prioritize long-term value creation. Delegate effectively while maintaining high-level insight and control."""
         },
        {
            "role": "user",
            "content": last_message.content
        }
    ]
    reply = llm.invoke(messages)
    return {"messages": [{"role": "assistant", "content": reply.content}]}

def finance_agent(state: State):
    last_message = state["messages"][-1]
    messages = [
        {"role": "system",
         "content": """You manage all financial functions of the organization. This includes budgeting, forecasting, accounting, and financial reporting. Ensure the company is financially healthy, compliant with regulations, and maximizing profitability. You evaluate investments, reduce financial risk, and assist in strategic planning with data-driven insights. Keep track of cash flow and ensure accurate financial statements."""
         },
        {
            "role": "user",
            "content": last_message.content
        }
    ]
    reply = llm.invoke(messages)
    return {"messages": [{"role": "assistant", "content": reply.content}]}

def get_available_positions() -> str:
    """Returns a string listing currently available positions in the company."""
    return "Currently, we have openings for AI Engineers and Data Scientists."


def hr_agent(state: State):
    last_message = state["messages"][-1]
    available_roles = get_available_positions() # HR agent calls the function
    messages = [
        {"role": "system",
         "content": f"""You are responsible for managing the human capital of the company. Oversee recruitment, onboarding, employee engagement, and retention. Design and manage compensation, performance appraisals, and training programs. Ensure legal compliance with labor laws and nurture a healthy workplace culture. Act as a bridge between management and employees.
         When asked about available positions, job openings, or recruitment, please use the following information: {available_roles}"""
         },
        {
            "role": "user",
            "content": last_message.content
        }
    ]
    reply = llm.invoke(messages)
    return {"messages": [{"role": "assistant", "content": reply.content}]}

def operations_agent(state: State):
    last_message = state["messages"][-1]
    messages = [
        {"role": "system",
         "content": """You ensure that the company’s day-to-day functions run smoothly and efficiently. Optimize internal processes, supply chains, resource allocation, and quality control. Identify bottlenecks, reduce operational costs, and enhance workflow productivity. Collaborate across departments to meet delivery timelines and customer expectations. Ensure consistency and scalability in execution."""
         },
        {
            "role": "user",
            "content": last_message.content
        }
    ]
    reply = llm.invoke(messages)
    return {"messages": [{"role": "assistant", "content": reply.content}]}

def marketing_agent(state: State):
    last_message = state["messages"][-1]
    messages = [
        {"role": "system",
         "content": """You lead the company’s marketing initiatives to grow brand awareness and customer engagement. Create and manage campaigns, analyze market trends, and develop positioning strategies. Oversee content creation, advertising, SEO, and performance analytics. Align marketing efforts with sales and product strategies to drive demand. Ensure consistent brand messaging across channels."""
         },
        {
            "role": "user",
            "content": last_message.content
        }
    ]
    reply = llm.invoke(messages)
    return {"messages": [{"role": "assistant", "content": reply.content}]}

def sales_agent(state: State):
    last_message = state["messages"][-1]
    messages = [
        {"role": "system",
         "content": """You are responsible for generating revenue and managing customer relationships. Develop sales strategies, close deals, and maintain strong client pipelines. Understand customer needs and align offerings to maximize value and conversion rates. Collaborate with marketing and product teams to refine messaging and offerings. Track KPIs, manage CRM data, and optimize the sales funnel."""
         },
        {
            "role": "user",
            "content": last_message.content
        }
    ]
    reply = llm.invoke(messages)
    return {"messages": [{"role": "assistant", "content": reply.content}]}

def technology_agent(state: State):
    last_message = state["messages"][-1]
    messages = [
        {"role": "system",
         "content": """You manage the organization’s technology infrastructure and digital systems. Ensure network security, maintain uptime, and support users across departments. Oversee software development, system integrations, and tech troubleshooting. Keep systems scalable, secure, and aligned with business goals. Stay up-to-date with emerging technologies to recommend improvements."""
         },
        {
            "role": "user",
            "content": last_message.content
        }
    ]
    reply = llm.invoke(messages)
    return {"messages": [{"role": "assistant", "content": reply.content}]}

def legal_agent(state: State):
    last_message = state["messages"][-1]
    messages = [
        {"role": "system",
         "content": """You are the legal advisor responsible for minimizing legal risks and ensuring corporate compliance. Draft, review, and manage contracts, policies, and legal documents. Provide counsel on regulatory requirements, IP protection, and dispute resolution. Ensure ethical governance and risk mitigation across departments. Maintain awareness of local and international laws relevant to the business."""
         },
        {
            "role": "user",
            "content": last_message.content
        }
    ]
    reply = llm.invoke(messages)
    return {"messages": [{"role": "assistant", "content": reply.content}]}

graph_builder = StateGraph(State)
graph_builder.add_node("classifier", classify_message)
graph_builder.add_node("router", router)
graph_builder.add_node("executive", executive_agent)
graph_builder.add_node("finance", finance_agent)
graph_builder.add_node("hr", hr_agent)
graph_builder.add_node("operations", operations_agent)
graph_builder.add_node("marketing", marketing_agent)
graph_builder.add_node("sales", sales_agent)
graph_builder.add_node("technology", technology_agent)
graph_builder.add_node("legal", legal_agent)
graph_builder.add_edge(START, "classifier")
graph_builder.add_edge("classifier", "router")
graph_builder.add_conditional_edges(
    "router",
    lambda state: state.get("next"),
    {"executive": "executive", "finance": "finance" , "hr": "hr", "operations": "operations", "marketing": "marketing", "sales": "sales", "technology": "technology", "legal": "legal"},
)
graph_builder.add_edge("executive", END)
graph_builder.add_edge("finance", END)
graph_builder.add_edge("hr", END)
graph_builder.add_edge("operations", END)
graph_builder.add_edge("marketing", END)
graph_builder.add_edge("sales", END)
graph_builder.add_edge("technology", END)
graph_builder.add_edge("legal", END)
memory = MemorySaver()
graph = graph_builder.compile(checkpointer=memory)

# --- CopilotKit integration ---
sdk = CopilotKitSDK(
    agents=[
        LangGraphAgent(
            name="quickstart_agent",
            description="Quickstart agent.",
            graph=graph,
        ),
    ],
)

app = FastAPI()
add_fastapi_endpoint(app, sdk, "/copilotkit")

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
