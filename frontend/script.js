// ==================================================
// DOM ELEMENTS
// ==================================================

const input = document.getElementById("messageInput");
const sendButton = document.getElementById("sendButton");
const messagesBox = document.getElementById("messages");
const newChatButton = document.getElementById("newChat");
const recentChats = document.getElementById("recentChats");

const pdfInput = document.getElementById("pdfInput");
const uploadButton = document.getElementById("uploadButton");
const uploadStatus = document.getElementById("uploadStatus");


// ==================================================
// BACKEND URL
// ==================================================

const API_URL = "http://127.0.0.1:8000";


// ==================================================
// CURRENT CHAT
// ==================================================

let currentChatId = null;


// ==================================================
// CURRENT DOCUMENT
// ==================================================

let currentDocumentId = null;


// ==================================================
// REQUEST STATE
// ==================================================

let isSending = false;
let isUploading = false;


// ==================================================
// API ERROR HELPER
// ==================================================

async function getErrorMessage(response) {
    try {
        const data = await response.json();

        return (
            data.detail ||
            data.message ||
            `Request failed with HTTP ${response.status}`
        );
    } catch (error) {
        return `Request failed with HTTP ${response.status}`;
    }
}


// ==================================================
// SCROLL TO BOTTOM
// ==================================================

function scrollMessagesToBottom() {
    if (!messagesBox) {
        return;
    }

    messagesBox.scrollTop = messagesBox.scrollHeight;
}


// ==================================================
// INLINE MARKDOWN
// ==================================================

function addInlineFormatting(container, text) {

    if (!container) {
        return;
    }

    const value = String(text || "");

    const parts = value.split(
        /(\*\*.*?\*\*|`.*?`|\*.*?\*)/g
    );

    parts.forEach((part) => {

        if (!part) {
            return;
        }

        // Bold
        if (
            part.startsWith("**") &&
            part.endsWith("**") &&
            part.length >= 4
        ) {

            const bold = document.createElement("strong");

            bold.textContent = part.slice(2, -2);

            container.appendChild(bold);

            return;
        }


        // Inline code
        if (
            part.startsWith("`") &&
            part.endsWith("`") &&
            part.length >= 2
        ) {

            const code = document.createElement("code");

            code.textContent = part.slice(1, -1);

            container.appendChild(code);

            return;
        }


        // Italic
        if (
            part.startsWith("*") &&
            part.endsWith("*") &&
            !part.startsWith("**") &&
            part.length >= 2
        ) {

            const italic = document.createElement("em");

            italic.textContent = part.slice(1, -1);

            container.appendChild(italic);

            return;
        }


        container.appendChild(
            document.createTextNode(part)
        );
    });
}


// ==================================================
// FORMAT AI RESPONSE
// ==================================================

function formatAIResponse(text) {

    const container = document.createElement("div");

    const lines = String(text || "").split("\n");

    let inCodeBlock = false;
    let codeContent = "";

    lines.forEach((line) => {

        // ==================================================
        // CODE BLOCK
        // ==================================================

        if (line.trim().startsWith("```")) {

            if (!inCodeBlock) {

                inCodeBlock = true;
                codeContent = "";

            } else {

                inCodeBlock = false;

                const codeWrapper =
                    document.createElement("div");

                codeWrapper.className =
                    "code-wrapper";

                const code =
                    document.createElement("pre");

                code.textContent =
                    codeContent.replace(/\n$/, "");

                const copyButton =
                    document.createElement("button");

                copyButton.type = "button";

                copyButton.className =
                    "copy-code-btn";

                copyButton.textContent = "Copy";

                const codeToCopy = codeContent;

                copyButton.addEventListener(
                    "click",
                    async () => {

                        try {

                            await navigator.clipboard.writeText(
                                codeToCopy
                            );

                            copyButton.textContent =
                                "Copied!";

                            setTimeout(() => {

                                copyButton.textContent =
                                    "Copy";

                            }, 1500);

                        } catch (error) {

                            console.error(
                                "Copy failed:",
                                error
                            );

                        }
                    }
                );

                codeWrapper.appendChild(code);
                codeWrapper.appendChild(copyButton);

                container.appendChild(codeWrapper);
            }

            return;
        }


        // ==================================================
        // INSIDE CODE BLOCK
        // ==================================================

        if (inCodeBlock) {

            codeContent += line + "\n";

            return;
        }


        // ==================================================
        // EMPTY LINE
        // ==================================================

        if (line.trim() === "") {

            container.appendChild(
                document.createElement("br")
            );

            return;
        }


        // ==================================================
        // HEADINGS
        // ==================================================

        if (line.startsWith("### ")) {

            const heading =
                document.createElement("h4");

            heading.textContent =
                line.substring(4);

            container.appendChild(heading);

            return;
        }


        if (line.startsWith("## ")) {

            const heading =
                document.createElement("h3");

            heading.textContent =
                line.substring(3);

            container.appendChild(heading);

            return;
        }


        if (line.startsWith("# ")) {

            const heading =
                document.createElement("h2");

            heading.textContent =
                line.substring(2);

            container.appendChild(heading);

            return;
        }


        // ==================================================
        // BULLET
        // ==================================================

        const trimmedLine = line.trim();

        if (
            trimmedLine.startsWith("- ") ||
            trimmedLine.startsWith("* ")
        ) {

            const bullet =
                document.createElement("div");

            bullet.className =
                "ai-bullet";

            const symbol =
                document.createElement("span");

            symbol.textContent = "•";

            const content =
                document.createElement("span");

            addInlineFormatting(
                content,
                trimmedLine.substring(2)
            );

            bullet.appendChild(symbol);
            bullet.appendChild(content);

            container.appendChild(bullet);

            return;
        }


        // ==================================================
        // NUMBERED LIST
        // ==================================================

        const numberMatch =
            trimmedLine.match(
                /^(\d+)\.\s+(.+)$/
            );

        if (numberMatch) {

            const numbered =
                document.createElement("div");

            numbered.className =
                "ai-numbered";

            const number =
                document.createElement("span");

            number.textContent =
                `${numberMatch[1]}.`;

            const content =
                document.createElement("span");

            addInlineFormatting(
                content,
                numberMatch[2]
            );

            numbered.appendChild(number);
            numbered.appendChild(content);

            container.appendChild(numbered);

            return;
        }


        // ==================================================
        // NORMAL TEXT
        // ==================================================

        const paragraph =
            document.createElement("div");

        addInlineFormatting(
            paragraph,
            line
        );

        container.appendChild(paragraph);
    });


    // Unclosed code block
    if (inCodeBlock && codeContent) {

        const codeWrapper =
            document.createElement("div");

        codeWrapper.className =
            "code-wrapper";

        const code =
            document.createElement("pre");

        code.textContent =
            codeContent.replace(/\n$/, "");

        codeWrapper.appendChild(code);

        container.appendChild(codeWrapper);
    }


    return container;
}


// ==================================================
// ADD NORMAL MESSAGE
// ==================================================

function addMessage(role, text) {

    if (!messagesBox) {
        return;
    }

    const messageDiv =
        document.createElement("div");

    messageDiv.className =
        role === "assistant"
            ? "message bot"
            : "message";


    // Avatar
    const avatar =
        document.createElement("div");

    avatar.className = "avatar";

    avatar.textContent =
        role === "user"
            ? "👤"
            : "🤖";


    // Content
    const contentWrapper =
        document.createElement("div");

    contentWrapper.className =
        "message-content";


    // Bubble
    const bubble =
        document.createElement("div");

    bubble.className = "bubble";


    if (role === "assistant") {

        bubble.appendChild(
            formatAIResponse(text)
        );

    } else {

        bubble.textContent =
            String(text || "");

    }


    // Time
    const time =
        document.createElement("div");

    time.className =
        "message-time";

    time.textContent =
        new Date().toLocaleTimeString(
            [],
            {
                hour: "2-digit",
                minute: "2-digit"
            }
        );


    contentWrapper.appendChild(bubble);
    contentWrapper.appendChild(time);

    messageDiv.appendChild(avatar);
    messageDiv.appendChild(contentWrapper);

    messagesBox.appendChild(messageDiv);

    scrollMessagesToBottom();
}


// ==================================================
// ADD AI MESSAGE
// ==================================================

function addAIMessage(
    text,
    usedRag = false
) {

    if (!messagesBox) {
        return;
    }

    const messageDiv =
        document.createElement("div");

    messageDiv.className =
        "message bot";


    // Avatar
    const avatar =
        document.createElement("div");

    avatar.className = "avatar";

    avatar.textContent = "🤖";


    // Content
    const contentWrapper =
        document.createElement("div");

    contentWrapper.className =
        "message-content";


    // Bubble
    const bubble =
        document.createElement("div");

    bubble.className = "bubble";

    bubble.appendChild(
        formatAIResponse(text)
    );


    // Actions
    const actions =
        document.createElement("div");

    actions.className =
        "message-actions";


    // Copy button
    const copyButton =
        document.createElement("button");

    copyButton.type = "button";

    copyButton.className =
        "copy-response";

    copyButton.textContent =
        "📋 Copy";


    copyButton.addEventListener(
        "click",
        async () => {

            try {

                await navigator.clipboard.writeText(
                    String(text || "")
                );

                copyButton.textContent =
                    "✅ Copied";

                setTimeout(() => {

                    copyButton.textContent =
                        "📋 Copy";

                }, 1500);

            } catch (error) {

                console.error(
                    "Copy failed:",
                    error
                );
            }
        }
    );


    actions.appendChild(copyButton);


    // RAG status
    const ragStatus =
        document.createElement("span");

    ragStatus.className =
        "rag-status";

    ragStatus.textContent =
        usedRag
            ? "📄 Document used"
            : "🤖 General AI";

    actions.appendChild(ragStatus);


    // Time
    const time =
        document.createElement("div");

    time.className =
        "message-time";

    time.textContent =
        new Date().toLocaleTimeString(
            [],
            {
                hour: "2-digit",
                minute: "2-digit"
            }
        );


    contentWrapper.appendChild(bubble);
    contentWrapper.appendChild(actions);
    contentWrapper.appendChild(time);

    messageDiv.appendChild(avatar);
    messageDiv.appendChild(contentWrapper);

    messagesBox.appendChild(messageDiv);

    scrollMessagesToBottom();
}


// ==================================================
// LOADING
// ==================================================

function showLoading() {

    removeLoading();

    if (!messagesBox) {
        return;
    }

    const loading =
        document.createElement("div");

    loading.id =
        "loading-message";

    loading.className =
        "message bot";

    loading.innerHTML = `
        <div class="avatar">🤖</div>

        <div class="message-content">

            <div class="bubble typing">

                <span></span>
                <span></span>
                <span></span>

            </div>

        </div>
    `;

    messagesBox.appendChild(loading);

    scrollMessagesToBottom();
}


// ==================================================
// REMOVE LOADING
// ==================================================

function removeLoading() {

    const loading =
        document.getElementById(
            "loading-message"
        );

    if (loading) {
        loading.remove();
    }
}


// ==================================================
// SEND MESSAGE
// ==================================================

async function sendMessage() {

    if (isSending) {
        return;
    }

    if (!input) {
        return;
    }

    const message =
        input.value.trim();

    if (!message) {
        return;
    }


    // ==================================================
    // CREATE CHAT IF NEEDED
    // ==================================================

    if (currentChatId === null) {

        const newChatId =
            await createNewChat(false);

        if (newChatId === null) {

            addAIMessage(
                "Unable to create a new chat. Please try again."
            );

            return;
        }
    }


    if (currentChatId === null) {
        return;
    }


    // ==================================================
    // LOCK INPUT
    // ==================================================

    isSending = true;

    input.disabled = true;

    if (sendButton) {
        sendButton.disabled = true;
    }


    // ==================================================
    // SHOW USER MESSAGE
    // ==================================================

    addMessage(
        "user",
        message
    );

    input.value = "";

    showLoading();


    try {

        const response =
            await fetch(
                `${API_URL}/chat`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({

                        chat_id:
                            Number(currentChatId),

                        message:
                            message,

                        document_id:
                            currentDocumentId || null

                    })
                }
            );


        if (!response.ok) {

            const errorMessage =
                await getErrorMessage(
                    response
                );

            throw new Error(
                errorMessage
            );
        }


        const data =
            await response.json();


        if (
            data.chat_id === undefined ||
            data.chat_id === null
        ) {

            throw new Error(
                "Backend did not return chat_id."
            );
        }


        currentChatId =
            Number(data.chat_id);


        removeLoading();


        addAIMessage(
            data.response ||
                "Sorry, I couldn't generate a response.",

            data.used_rag === true
        );


        await loadChats();


    } catch (error) {

        console.error(
            "Chat Error:",
            error
        );

        removeLoading();

        addAIMessage(
            `❌ ${error.message || "Something went wrong. Please try again."}`
        );

    } finally {

        isSending = false;

        input.disabled = false;

        if (sendButton) {
            sendButton.disabled = false;
        }

        input.focus();
    }
}


// ==================================================
// CREATE NEW CHAT
// ==================================================

async function createNewChat(
    showWelcome = true
) {

    try {

        const response =
            await fetch(
                `${API_URL}/chats`,
                {
                    method: "POST"
                }
            );


        if (!response.ok) {

            const errorMessage =
                await getErrorMessage(
                    response
                );

            throw new Error(
                errorMessage
            );
        }


        const data =
            await response.json();


        if (
            data.chat_id === undefined ||
            data.chat_id === null
        ) {

            throw new Error(
                "Backend did not return chat_id."
            );
        }


        currentChatId =
            Number(data.chat_id);


        // New chat should not use old PDF context.
        currentDocumentId = null;


        if (uploadStatus) {
            uploadStatus.textContent = "";
        }


        if (messagesBox) {
            messagesBox.innerHTML = "";
        }


        if (showWelcome) {

            addAIMessage(
                "Hello! 👋 How can I help you today?",
                false
            );
        }


        await loadChats();

        input.focus();

        return currentChatId;


    } catch (error) {

        console.error(
            "New Chat Error:",
            error
        );

        currentChatId = null;

        return null;
    }
}


// ==================================================
// FORMAT CHAT TIME
// ==================================================

function formatChatTime(dateValue) {

    if (!dateValue) {
        return "Today";
    }

    const date =
        new Date(dateValue);

    if (
        Number.isNaN(
            date.getTime()
        )
    ) {
        return "Today";
    }

    const now = new Date();

    const diff =
        now.getTime() -
        date.getTime();

    const minutes =
        Math.floor(
            diff / 60000
        );


    if (minutes < 1) {
        return "Just now";
    }


    if (minutes < 60) {
        return `${minutes} min ago`;
    }


    const hours =
        Math.floor(
            minutes / 60
        );


    if (hours < 24) {
        return `${hours} hr ago`;
    }


    const days =
        Math.floor(
            hours / 24
        );


    if (days === 1) {
        return "Yesterday";
    }


    if (days < 7) {
        return `${days} days ago`;
    }


    return date.toLocaleDateString(
        "en-IN",
        {
            day: "2-digit",
            month: "short"
        }
    );
}


// ==================================================
// REMOVE CHAT FROM UI
// ==================================================

function removeChatFromUI(
    chatElement
) {

    if (!chatElement) {
        return;
    }

    chatElement.style.transition =
        "all 0.2s ease";

    chatElement.style.opacity =
        "0";

    chatElement.style.transform =
        "translateX(-10px)";

    setTimeout(() => {

        chatElement.remove();

    }, 200);
}


// ==================================================
// DELETE CHAT
// ==================================================

async function deleteChat(
    chatId,
    chatElement = null
) {

    try {

        const response =
            await fetch(
                `${API_URL}/chats/${chatId}`,
                {
                    method: "DELETE"
                }
            );


        if (!response.ok) {

            const errorMessage =
                await getErrorMessage(
                    response
                );

            throw new Error(
                errorMessage
            );
        }


        const data =
            await response.json();


        if (!data.success) {

            throw new Error(
                data.message ||
                "Failed to delete chat"
            );
        }


        if (chatElement) {

            removeChatFromUI(
                chatElement
            );
        }


        // Current chat deleted
        if (
            Number(currentChatId) ===
            Number(chatId)
        ) {

            currentChatId = null;
            currentDocumentId = null;

            if (messagesBox) {
                messagesBox.innerHTML = "";
            }

            await initializeChat();

        } else {

            await loadChats();
        }


    } catch (error) {

        console.error(
            "Delete Chat Error:",
            error
        );

        alert(
            error.message ||
            "Failed to delete chat."
        );
    }
}


// ==================================================
// LOAD CHATS
// ==================================================

async function loadChats() {

    try {

        const response =
            await fetch(
                `${API_URL}/chats`
            );


        if (!response.ok) {

            throw new Error(
                await getErrorMessage(
                    response
                )
            );
        }


        const chats =
            await response.json();


        const container =
            document.getElementById(
                "recentChats"
            );


        if (!container) {
            return;
        }


        container.innerHTML = "";


        if (
            !Array.isArray(chats) ||
            chats.length === 0
        ) {

            const empty =
                document.createElement("div");

            empty.textContent =
                "No recent chats";

            empty.style.padding =
                "15px 10px";

            empty.style.color =
                "#718096";

            empty.style.fontSize =
                "12px";

            container.appendChild(empty);

            return;
        }


        chats.forEach((chat) => {

            const item =
                document.createElement("div");

            item.className =
                "recent-chat";


            // Active chat
            if (
                currentChatId !== null &&
                Number(currentChatId) ===
                Number(chat.id)
            ) {

                item.classList.add(
                    "active"
                );
            }


            // Chat icon
            const icon =
                document.createElement("div");

            icon.className =
                "chat-history-icon";

            icon.textContent =
                "💬";


            // Content
            const content =
                document.createElement("div");

            content.className =
                "chat-history-content";


            const title =
                document.createElement("div");

            title.className =
                "chat-history-title";

            title.textContent =
                chat.title ||
                "New Chat";


            const time =
                document.createElement("div");

            time.className =
                "chat-history-time";

            time.textContent =
                formatChatTime(
                    chat.updated_at ||
                    chat.created_at
                );


            content.appendChild(title);
            content.appendChild(time);


            // Delete button
            const deleteButton =
                document.createElement("button");

            deleteButton.type = "button";

            deleteButton.className =
                "delete-chat-btn";

            deleteButton.title =
                "Delete chat";

            deleteButton.textContent =
                "🗑";


            deleteButton.addEventListener(
                "click",
                (event) => {

                    event.stopPropagation();

                    deleteChat(
                        chat.id,
                        item
                    );
                }
            );


            // Open chat
            item.addEventListener(
                "click",
                () => {

                    loadChat(
                        chat.id
                    );
                }
            );


            item.appendChild(icon);
            item.appendChild(content);
            item.appendChild(deleteButton);

            container.appendChild(item);
        });


    } catch (error) {

        console.error(
            "History Error:",
            error
        );
    }
}


// ==================================================
// LOAD EXISTING CHAT
// ==================================================

async function loadChat(
    chatId
) {

    try {

        const response =
            await fetch(
                `${API_URL}/chats/${chatId}`
            );


        if (!response.ok) {

            throw new Error(
                await getErrorMessage(
                    response
                )
            );
        }


        const messages =
            await response.json();


        currentChatId =
            Number(chatId);


        // We don't know which document was used
        // by an old chat, so clear it.
        currentDocumentId = null;


        if (uploadStatus) {
            uploadStatus.textContent = "";
        }


        if (messagesBox) {
            messagesBox.innerHTML = "";
        }


        if (Array.isArray(messages)) {

            messages.forEach((message) => {

                if (
                    message.role ===
                    "assistant"
                ) {

                    addAIMessage(
                        message.content,
                        false
                    );

                } else {

                    addMessage(
                        "user",
                        message.content
                    );
                }
            });
        }


        await loadChats();

        input.focus();


    } catch (error) {

        console.error(
            "Load Chat Error:",
            error
        );

        addAIMessage(
            "❌ Failed to load this chat."
        );
    }
}


// ==================================================
// INITIALIZE CHAT
// ==================================================

async function initializeChat() {

    try {

        const response =
            await fetch(
                `${API_URL}/chats`
            );


        if (!response.ok) {

            throw new Error(
                await getErrorMessage(
                    response
                )
            );
        }


        const chats =
            await response.json();


        // Existing chat
        if (
            Array.isArray(chats) &&
            chats.length > 0
        ) {

            const latestChat =
                chats[0];

            await loadChat(
                latestChat.id
            );

            return;
        }


        // No chat exists
        await createNewChat(true);


    } catch (error) {

        console.error(
            "Initialize Chat Error:",
            error
        );

        addAIMessage(
            "❌ Unable to connect to the backend. Make sure FastAPI is running."
        );
    }
}


// ==================================================
// UPDATE DOCUMENT UI
// ==================================================

function updateDocumentUI(
    filename,
    size
) {

    const documentName =
        document.getElementById(
            "documentName"
        );

    const documentSize =
        document.getElementById(
            "documentSize"
        );


    if (documentName) {

        documentName.textContent =
            filename ||
            "Document";
    }


    if (documentSize) {

        if (size) {

            const mb =
                size /
                (1024 * 1024);

            documentSize.textContent =
                `${mb.toFixed(1)} MB • Uploaded just now`;

        } else {

            documentSize.textContent =
                "PDF • Uploaded just now";
        }
    }
}


// ==================================================
// RESET DOCUMENT UI
// ==================================================

function resetDocumentUI() {

    const documentName =
        document.getElementById(
            "documentName"
        );

    const documentSize =
        document.getElementById(
            "documentSize"
        );


    if (documentName) {

        documentName.textContent =
            "No document";
    }


    if (documentSize) {

        documentSize.textContent =
            "Upload a PDF to get started";
    }
}


// ==================================================
// PDF UPLOAD BUTTON
// ==================================================

if (
    uploadButton &&
    pdfInput
) {

    uploadButton.addEventListener(
        "click",
        () => {

            if (isUploading) {
                return;
            }

            pdfInput.click();
        }
    );
}


// ==================================================
// PDF UPLOAD
// ==================================================

if (pdfInput) {

    pdfInput.addEventListener(
        "change",
        async () => {

            const file =
                pdfInput.files?.[0];


            if (!file) {
                return;
            }


            if (isUploading) {
                return;
            }


            // ==================================================
            // PDF CHECK
            // ==================================================

            const isPDF =
                file.type ===
                    "application/pdf" ||
                file.name
                    .toLowerCase()
                    .endsWith(".pdf");


            if (!isPDF) {

                if (uploadStatus) {

                    uploadStatus.textContent =
                        "❌ Only PDF files are allowed.";
                }

                pdfInput.value = "";

                return;
            }


            // ==================================================
            // LOADING
            // ==================================================

            isUploading = true;


            if (uploadButton) {
                uploadButton.disabled = true;
            }


            if (uploadStatus) {

                uploadStatus.textContent =
                    "⏳ Processing PDF...";
            }


            const formData =
                new FormData();

            formData.append(
                "file",
                file
            );


            try {

                const response =
                    await fetch(
                        `${API_URL}/upload`,
                        {
                            method: "POST",
                            body: formData
                        }
                    );


                if (!response.ok) {

                    throw new Error(
                        await getErrorMessage(
                            response
                        )
                    );
                }


                const data =
                    await response.json();


                if (!data.success) {

                    throw new Error(
                        data.message ||
                        "PDF processing failed."
                    );
                }


                if (!data.document_id) {

                    throw new Error(
                        "Backend did not return document_id."
                    );
                }


                // ==================================================
                // SAVE DOCUMENT ID
                // ==================================================

                currentDocumentId =
                    data.document_id;


                // ==================================================
                // UPDATE DOCUMENT UI
                // ==================================================

                updateDocumentUI(
                    data.filename ||
                    file.name,
                    file.size
                );


                if (uploadStatus) {

                    uploadStatus.textContent =
                        `✅ ${data.filename || file.name} uploaded`;
                }


                // ==================================================
                // SHOW SUCCESS MESSAGE
                // ==================================================

                addAIMessage(
                    `📄 **${data.filename || file.name}** is ready.\n\n` +
                    `${data.pages || 0} page(s) processed and ` +
                    `${data.chunks || 0} chunks created.\n\n` +
                    `You can now ask questions about this document.`,
                    true
                );


            } catch (error) {

                console.error(
                    "Upload Error:",
                    error
                );


                currentDocumentId =
                    null;


                if (uploadStatus) {

                    uploadStatus.textContent =
                        `❌ ${error.message || "PDF upload failed."}`;
                }
            } finally {

                isUploading = false;


                if (uploadButton) {
                    uploadButton.disabled = false;
                }


                pdfInput.value = "";
            }
        }
    );
}


// ==================================================
// SEND BUTTON
// ==================================================

if (sendButton) {

    sendButton.addEventListener(
        "click",
        sendMessage
    );
}


// ==================================================
// NEW CHAT BUTTON
// ==================================================

if (newChatButton) {

    newChatButton.addEventListener(
        "click",
        async () => {

            if (isSending) {
                return;
            }

            await createNewChat(true);
        }
    );
}


// ==================================================
// ENTER KEY
// ==================================================

if (input) {

    input.addEventListener(
        "keydown",
        (event) => {

            if (
                event.key === "Enter" &&
                !event.shiftKey
            ) {

                event.preventDefault();

                sendMessage();
            }
        }
    );
}


// ==================================================
// INITIAL LOAD
// ==================================================

document.addEventListener(
    "DOMContentLoaded",
    () => {

        initializeChat();

    }
);