import os

from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from pydantic import BaseModel

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

import faiss
import numpy as np
import pandas as pd


load_dotenv()

app = FastAPI()


@app.get("/")
def serve_ui():
    return FileResponse("index.html")


app.mount("/static", StaticFiles(directory="static"), name="static")

llm = ChatOpenAI(
    model="gpt-3.5-turbo",
    temperature=0.7,
    openai_api_key=os.getenv("OPENAI_API_KEY")
)


class ChatRequest(BaseModel):
    user_id: str
    message: str


def ask_llm(question: str):
    response = llm.invoke(question)
    return response


@app.post("/chat")
def chat_endpoint(chat_req: ChatRequest):
    response = ask_llm(chat_req.message)
    return {"response": str(response.content)}


# --------Vector Database---------
dimension = 1536
index = faiss.IndexFlatL2(dimension)

user_memories = {}

embeddings = OpenAIEmbeddings()


def store_user_preference(user_id: str, text: str):
    vector = embeddings.embed_query(text)
    index.add(np.array([vector]))
    user_memories[user_id] = {"vector": vector, "text": text}


# ---------RAG----------
df = pd.read_csv("final_cocktails.csv")


def retrieve_cocktail_info(query: str):
    results = df[df["ingredients"].str.contains(query, case=False, na=False)]
    return results.head(5).to_dict(orient="records")


@app.post("/search-cocktail")
def search_cocktail(chat_req: ChatRequest):
    cocktails = retrieve_cocktail_info(chat_req.message)
    return {"cocktails": cocktails}


@app.post("/recommend")
def recommend_cocktail(chat_req: ChatRequest):
    user_id = chat_req.user_id
    if user_id in user_memories:
        user_prefs = user_memories[user_id]["text"]
        response = llm.predict(f"Recommend 5 cocktails based on these preferences: {user_prefs}")
        return {"recommendations": response}
    else:
        return {"message": "No preferences found. Start by sharing your favorite ingredients!"}
