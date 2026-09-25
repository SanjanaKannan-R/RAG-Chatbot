# Citation-Grounded RAG Chatbot 

A full-stack **RAG (Retrieval-Augmented Generation) chatbot** that lets you chat with your **PDF, TXT, and CSV files**.

The main goal is to provide answers that are **grounded in the uploaded documents**. Each answer includes citations showing exactly where the information came from.

## Features

* Upload PDF, TXT, and CSV files
* Ask questions about your documents
* Get answers based only on relevant document content
* View the source file and chunk used for each answer
* Shows a warning when an answer cannot be verified
* Stores documents and chat history using SQLite
* Simple React-based chat interface

## Tech Stack

**Frontend**

* React
* Vite
* Tailwind CSS
* TypeScript

**Backend**

* Python
* Flask
* LangChain

**Database**

* SQLite
* sqlite-vec

**AI**

* Embeddings for document search
* Groq / OpenAI / Ollama support

## How It Works

```text
Upload Document
      ↓
Split into Chunks
      ↓
Store in SQLite
      ↓
Search Relevant Chunks
      ↓
Generate Answer
      ↓
Verify Citations
      ↓
Display Answer + Sources
```

## Project Structure

```text
project/
├── backend/
│   ├── app/
│   │   ├── ingestion/
│   │   ├── retrieval/
│   │   ├── generation/
│   │   ├── db/
│   │   └── main.py
│   ├── tests/
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── App.tsx
│   │   └── types.ts
│   └── package.json
│
└── README.md
```

## Run Locally

### Backend

```powershell
$env:PYTHONPATH="backend"
.\.venv\Scripts\python backend/app/main.py
```

Backend:

```text
http://127.0.0.1:8000
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

## Example

Upload a PDF and ask:

> "What is the total amount mentioned in the invoice?"

The chatbot retrieves the relevant section, generates the answer, and displays the **source file and document chunk** used to verify the answer.

## Goal

The project focuses on making RAG applications more **transparent and trustworthy** by allowing users to verify where an answer came from.

