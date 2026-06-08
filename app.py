import os
import csv
import random
from datetime import datetime
import streamlit as st
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

# Streamlit App Title
st.title("🛍️ E-Commerce Customer Support Bot")
st.write("Ask me anything about our shipping, returns, and warranties!")

# --- Sidebar: CRM & Omnichannel Simulation ---
with st.sidebar:
    st.header("🏢 Kapture CX Simulation")
    st.write("These settings simulate enterprise context injection.")
    
    st.subheader("CRM Context (Customer 360)")
    customer_name = st.text_input("Customer Name", value="John Doe")
    order_id = st.text_input("Order ID", value="ORD-9921")
    
    st.subheader("Omnichannel Delivery")
    channel = st.selectbox("Simulate Channel", ["🌐 Web Interface", "💬 WhatsApp"])

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Determine current avatar
bot_avatar = "🤖" if channel == "🌐 Web Interface" else "💬"

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    avatar = bot_avatar if message["role"] == "assistant" else "👤"
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

@st.cache_resource
def setup_rag_pipeline():
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
        "If the Channel is '💬 WhatsApp', you must keep your answers extremely short, use bullet points, and use emojis. "
        "Do not guess or make up answers.\n\n"
        "Channel: {channel}\n\n"
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
    
    return rag_chain

# Check for API Key
if not os.environ.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY") == "your_api_key_here":
    st.warning("⚠️ Please add your GROQ_API_KEY to the .env file to continue.")
    st.stop()

# Setup pipeline
try:
    rag_chain = setup_rag_pipeline()
except Exception as e:
    st.error(f"Error setting up the application: {e}")
    st.stop()

# React to user input
if prompt := st.chat_input("Ask a question (e.g., What is your return policy?)"):
    
    # MOCK TICKETING SYSTEM (Human Handoff Simulation)
    if prompt.strip().lower() == "create ticket":
        ticket_id = f"TKT-{random.randint(1000, 9999)}"
        # Log ticket to CSV
        with open('tickets.csv', mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if f.tell() == 0:
                writer.writerow(['TicketID', 'CustomerName', 'OrderID', 'Timestamp'])
            writer.writerow([ticket_id, customer_name, order_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        
        st.chat_message("user", avatar="👤").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        escalation_response = f"🎫 **Ticket Created!** Your support ticket ID is `{ticket_id}`. A human agent will review your chat history and contact you shortly."
        st.chat_message("assistant", avatar=bot_avatar).markdown(escalation_response)
        st.session_state.messages.append({"role": "assistant", "content": escalation_response})
        st.stop()

    # Log the interaction
    with open('chat_logs.csv', mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # Write header if file is empty
        if f.tell() == 0:
            writer.writerow(['Timestamp', 'UserQuery', 'Channel', 'CustomerName'])
        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), prompt, channel, customer_name])

    # Display user message in chat message container
    st.chat_message("user", avatar="👤").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Get bot response
    with st.chat_message("assistant", avatar=bot_avatar):
        with st.spinner("Thinking..."):
            response = rag_chain.invoke({
                "input": prompt,
                "customer_name": customer_name,
                "order_id": order_id,
                "channel": channel
            })
            answer = response["answer"]
            st.markdown(answer)
            # Add assistant response to chat history
            st.session_state.messages.append({"role": "assistant", "content": answer})
