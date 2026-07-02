import os
import csv
import random
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_groq import ChatGroq
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

# Load environment variables
load_dotenv()

# Verify GROQ_API_KEY
if not os.environ.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY") == "your_api_key_here":
    raise RuntimeError("Missing GROQ_API_KEY environment variable. Please check your .env file.")

# Initialize FastAPI app
app = FastAPI(title="E-Commerce Support Bot API")

# Enable CORS (Cross-Origin Resource Sharing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local/development use
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define Pydantic request model
class ChatRequest(BaseModel):
    query: str
    customer_name: str = "John Doe"
    order_id: str = "ORD-9921"

# --- Globals to hold pipeline components ---
rag_chain = None

def setup_rag_pipeline():
    global rag_chain
    # 1. Load the documents
    loader = DirectoryLoader("data/", glob="**/*.txt", loader_cls=TextLoader, loader_kwargs={'encoding': 'utf-8'})
    docs = loader.load()

    # 2. Split the document into chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    splits = text_splitter.split_documents(docs)

    # 3. Create embeddings and vector store
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    vectorstore = FAISS.from_documents(splits, embeddings)
    retriever = vectorstore.as_retriever()

    # 4. Setup LLM
    llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)

    # 5. Create System Prompt Guardrail with CRM Context
    system_prompt = (
        "You are a helpful customer support assistant for an e-commerce store. "
        "The customer's name is {customer_name} and they are asking about order {order_id}. Greet them by name. "
        "You must ONLY answer questions based on the provided context (shipping, returns, and warranties). "
        "If the user asks a question that is not covered in the context, or asks to speak to a human, you must say: "
        "'I specialize in shipping, returns, and warranties. For other inquiries, please contact our support team at support@company.com or type CREATE TICKET to escalate this to a human agent.' "
        "Do not guess or make up answers.\n\n"
        "Context: {context}"
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "{input}"),
        ]
    )

    # 6. Create the chain
    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)

# Initialize RAG pipeline on application startup
@app.on_event("startup")
def startup_event():
    try:
        setup_rag_pipeline()
    except Exception as e:
        raise RuntimeError(f"Error initializing RAG pipeline: {e}")

@app.get("/")
def read_root():
    return {"status": "running", "message": "E-Commerce Customer Support API is active."}

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    global rag_chain
    if not rag_chain:
        raise HTTPException(status_code=500, detail="RAG pipeline is not initialized.")

    query = request.query.strip()
    customer_name = request.customer_name.strip()
    order_id = request.order_id.strip()

    # MOCK TICKETING SYSTEM (Human Handoff Simulation)
    if query.lower() == "create ticket":
        ticket_id = f"TKT-{random.randint(1000, 9999)}"
        # Log ticket to CSV
        with open('tickets.csv', mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if f.tell() == 0:
                writer.writerow(['TicketID', 'CustomerName', 'OrderID', 'Timestamp'])
            writer.writerow([ticket_id, customer_name, order_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        
        return {
            "answer": f"🎫 **Ticket Created!** Your support ticket ID is `{ticket_id}`. A human agent will review your chat history and contact you shortly.",
            "ticket_created": True,
            "ticket_id": ticket_id
        }

    # Log the interaction
    with open('chat_logs.csv', mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if f.tell() == 0:
            writer.writerow(['Timestamp', 'UserQuery', 'CustomerName'])
        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), query, customer_name])

    try:
        # Get bot response
        response = rag_chain.invoke({
            "input": query,
            "customer_name": customer_name,
            "order_id": order_id
        })
        return {
            "answer": response["answer"],
            "ticket_created": False
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating response: {e}")
