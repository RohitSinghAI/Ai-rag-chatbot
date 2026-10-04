import os
import shutil
import uuid

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from groq import Groq
import pymupdf

from database import get_connection, create_tables

from rag import (
    create_vector_index,
    search_document
)


# ==================================================
# Environment
# ==================================================

load_dotenv()


# ==================================================
# FastAPI
# ==================================================

app = FastAPI(
    title="AI Chatbot API",
    version="1.0.0"
)


# ==================================================
# CORS
# ==================================================

app.add_middleware(
    CORSMiddleware,

    allow_origins=["*"],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"]
)


# ==================================================
# Groq Client
# ==================================================

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)


# ==================================================
# Database
# ==================================================

create_tables()


# ==================================================
# Upload Directory
# ==================================================

UPLOAD_DIR = "uploads"

os.makedirs(
    UPLOAD_DIR,
    exist_ok=True
)


# ==================================================
# Request Model
# ==================================================

class ChatRequest(BaseModel):

    chat_id: int | None = None

    message: str

    # PDF / RAG document ID
    document_id: str | None = None


# ==================================================
# HOME
# ==================================================

@app.get("/")
def home():

    return {
        "message": "AI Chatbot Backend is running!"
    }


# ==================================================
# CHAT APIs
# ==================================================


# --------------------------------------------------
# Create New Chat
# --------------------------------------------------

@app.post("/chats")
def create_chat():

    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        INSERT INTO chats (title)
        VALUES (?)
        """,
        ("New Chat",)
    )


    chat_id = cursor.lastrowid


    connection.commit()

    connection.close()


    return {
        "chat_id": chat_id,
        "title": "New Chat"
    }


# --------------------------------------------------
# Get All Chats
# --------------------------------------------------

@app.get("/chats")
def get_chats():

    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        SELECT id, title, created_at
        FROM chats
        ORDER BY id DESC
        """
    )


    chats = [
        dict(row)
        for row in cursor.fetchall()
    ]


    connection.close()


    return chats


# --------------------------------------------------
# Get Chat Messages
# --------------------------------------------------

@app.get("/chats/{chat_id}")
def get_chat_messages(chat_id: int):

    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        SELECT role, content, created_at
        FROM messages
        WHERE chat_id = ?
        ORDER BY id ASC
        """,
        (chat_id,)
    )


    messages = [
        dict(row)
        for row in cursor.fetchall()
    ]


    connection.close()


    return messages


# --------------------------------------------------
# Delete Chat
# --------------------------------------------------

@app.delete("/chats/{chat_id}")
def delete_chat(chat_id: int):

    connection = get_connection()
    cursor = connection.cursor()

    try:
        # Delete messages of this chat
        cursor.execute(
            """
            DELETE FROM messages
            WHERE chat_id = ?
            """,
            (chat_id,)
        )

        # Delete chat
        cursor.execute(
            """
            DELETE FROM chats
            WHERE id = ?
            """,
            (chat_id,)
        )

        if cursor.rowcount == 0:
            connection.rollback()
            connection.close()

            return {
                "success": False,
                "message": "Chat not found"
            }

        connection.commit()
        connection.close()

        return {
            "success": True,
            "message": "Chat deleted successfully",
            "chat_id": chat_id
        }

    except Exception as error:

        connection.rollback()
        connection.close()

        print("Delete Chat Error:", error)

        return {
            "success": False,
            "message": "Failed to delete chat"
        }

# ==================================================
# CHAT WITH AI + RAG
# ==================================================

@app.post("/chat")
def chat(request: ChatRequest):

    connection = get_connection()
    cursor = connection.cursor()

    # ==================================================
    # CREATE CHAT
    # ==================================================

    chat_id = request.chat_id

    if chat_id is None:

        cursor.execute(
            """
            INSERT INTO chats (title)
            VALUES (?)
            """,
            ("New Chat",)
        )

        chat_id = cursor.lastrowid

    # ==================================================
    # SAVE USER MESSAGE
    # ==================================================

    cursor.execute(
        """
        INSERT INTO messages
        (chat_id, role, content)
        VALUES (?, ?, ?)
        """,
        (
            chat_id,
            "user",
            request.message
        )
    )

    # ==================================================
    # GET CHAT HISTORY
    # ==================================================

    cursor.execute(
        """
        SELECT role, content
        FROM messages
        WHERE chat_id = ?
        ORDER BY id ASC
        """,
        (chat_id,)
    )

    previous_messages = cursor.fetchall()

    # ==================================================
    # SYSTEM PROMPT
    # ==================================================

    system_prompt = """
You are a helpful AI assistant.

Rules:

1. Give short and clear answers.
2. Answer exactly what the user asks.
3. For simple questions, answer in 1-3 sentences.
4. Do not repeat the user's question.
5. Be professional and friendly.
6. You can have normal conversations.
7. Answer general questions using your general knowledge.
8. If relevant document information is provided, use it.
9. Never force a document answer for a general conversation.
10. Never say information is missing from the document unless
    the user specifically asks about the document and the
    information is genuinely unavailable.
"""

    messages = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]

    # ==================================================
    # RAG SEARCH
    # ==================================================

    document_context = ""
    use_rag = False

    if request.document_id:

        try:

            results = search_document(
                request.document_id,
                request.message,
                top_k=8
            )

            # ------------------------------------------
            # Detect document-specific questions
            # ------------------------------------------

            document_words = [
                "pdf", "document", "file", "this",
                "summarize", "summary", "main topics",
                "key points", "important concepts",
                "explain", "list the key", "according to"
            ]

            message_lower = request.message.lower()

            is_document_question = any(
                word in message_lower
                for word in document_words
            )

            # ------------------------------------------
            # For explicit PDF questions, use the best
            # retrieved chunks even when similarity is
            # slightly below the normal threshold.
            # This is important for queries like:
            # "Summarize this PDF".
            # ------------------------------------------

            if is_document_question:

                relevant_results = results[:8]

            else:

                relevant_results = [
                    result
                    for result in results
                    if (
                        result.get("score", 0) >= 0.45
                        or
                        result.get("keyword_score", 0) >= 0.20
                    )
                ]

            if relevant_results:

                use_rag = True

                document_context = "\n\n".join(

                    result["text"]

                    for result in relevant_results

                )


        except Exception as error:

            print(
                "RAG Search Error:",
                error
            )

            use_rag = False

    # ==================================================
    # ADD RAG CONTEXT
    # ==================================================

    if use_rag:

        messages.append({

            "role": "system",

            "content": f"""
The user has uploaded a document.

The following information was retrieved
from that document:

-------------------------
{document_context}
-------------------------

Use this information when the user's
question is related to the uploaded document.

If the question is general or unrelated
to the document, answer normally.

Do not invent information from the document.
"""

        })

    # ==================================================
    # ADD CONVERSATION HISTORY
    # ==================================================

    for message in previous_messages:

        messages.append({

            "role": message["role"],

            "content": message["content"]

        })

    # ==================================================
    # GROQ
    # ==================================================

    try:

        response = client.chat.completions.create(

            model="openai/gpt-oss-120b",

            messages=messages,

            temperature=0.3,

            max_tokens=700

        )

        ai_response = (

            response
            .choices[0]
            .message
            .content
            .strip()

        )

    except Exception as error:

        print(
            "Groq Error:",
            error
        )

        connection.close()

        return {

            "chat_id": chat_id,

            "response":
                "Sorry, something went wrong."

        }

    # ==================================================
    # SAVE AI RESPONSE
    # ==================================================

    cursor.execute(

        """
        INSERT INTO messages
        (chat_id, role, content)
        VALUES (?, ?, ?)
        """,

        (
            chat_id,
            "assistant",
            ai_response
        )

    )

    # ==================================================
    # UPDATE CHAT TITLE
    # ==================================================

    cursor.execute(

        """
        UPDATE chats
        SET title = ?
        WHERE id = ?
        AND title = 'New Chat'
        """,

        (
            request.message[:40],
            chat_id
        )

    )

    # ==================================================
    # COMMIT
    # ==================================================

    connection.commit()

    connection.close()

    # ==================================================
    # RETURN
    # ==================================================

    return {

        "chat_id":
            chat_id,

        "response":
            ai_response,

        "used_rag":
            use_rag

    }

# ==================================================
# PDF UPLOAD + RAG
# ==================================================

@app.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...)
):

    # ==================================================
    # Check PDF
    # ==================================================

    if file.content_type != "application/pdf":

        return {

            "success": False,

            "message":
                "Only PDF files are allowed."

        }


    # ==================================================
    # Generate Document ID
    # ==================================================

    document_id = str(
        uuid.uuid4()
    )


    # ==================================================
    # Secure File Name
    # ==================================================

    filename = os.path.basename(
        file.filename
    )


    # ==================================================
    # File Path
    # ==================================================

    file_path = os.path.join(

        UPLOAD_DIR,

        f"{document_id}_{filename}"

    )


    # ==================================================
    # Save PDF
    # ==================================================

    try:

        with open(
            file_path,
            "wb"
        ) as buffer:

            shutil.copyfileobj(
                file.file,
                buffer
            )

    except Exception as error:

        print(
            "File Save Error:",
            error
        )

        return {

            "success": False,

            "message":
                "Failed to save PDF."

        }


    # ==================================================
    # Read PDF + Extract Text
    # ==================================================

    text = ""
    total_pages = 0

    try:

        pdf_document = pymupdf.open(file_path)

        total_pages = len(pdf_document)

        for page_number, page in enumerate(pdf_document):

            try:

                page_text = page.get_text("text")

                if page_text:
                    text += page_text
                    text += "\n"

            except Exception as page_error:

                print(
                    f"PDF Page {page_number + 1} Error:",
                    page_error
                )

        pdf_document.close()

    except Exception as error:

        print(
            "PDF Read Error:",
            error
        )

        return {
            "success": False,
            "message":
                "Failed to read PDF."
        }


    # ==================================================
    # Clean Extracted Text
    # ==================================================

    text = text.strip()


    # ==================================================
    # Check Extracted Text
    # ==================================================

    if not text:

        # Remove saved PDF because processing failed.
        try:

            if os.path.exists(file_path):
                os.remove(file_path)

        except Exception as cleanup_error:

            print(
                "PDF Cleanup Error:",
                cleanup_error
            )

        return {
            "success": False,
            "message":
                "Could not extract text from this PDF. "
                "The PDF may be scanned/image-based or contain no selectable text."
        }


    # ==================================================
    # Create RAG Vector Index
    # ==================================================

    try:

        rag_result = create_vector_index(

            document_id,

            text

        )

    except Exception as error:

        print(
            "RAG Index Error:",
            error
        )

        return {

            "success": False,

            "message":
                "Failed to create RAG index."

        }


    # ==================================================
    # Return
    # ==================================================

    return {

        "success": True,

        "document_id":
            document_id,

        "filename":
            filename,

        "pages":
            total_pages,

        "text_length":
            len(text),

        "chunks":
            rag_result["chunks"],

        "message":
            "PDF processed successfully."

    }