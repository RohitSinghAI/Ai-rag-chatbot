// ==================================================
// DOM ELEMENTS
// ==================================================

const input =
    document.getElementById("messageInput");

const sendButton =
    document.getElementById("sendButton");

const messagesBox =
    document.getElementById("messages");

const newChatButton =
    document.getElementById("newChat");

const recentChats =
    document.getElementById("recentChats");

const pdfInput =
    document.getElementById("pdfInput");

const uploadButton =
    document.getElementById("uploadButton");

const uploadStatus =
    document.getElementById("uploadStatus");


// ==================================================
// BACKEND URL
// ==================================================

const API_URL =
    "http://127.0.0.1:8000";


// ==================================================
// CURRENT CHAT
// ==================================================

let currentChatId = null;


// ==================================================
// CURRENT DOCUMENT
// ==================================================

let currentDocumentId = null;


// ==================================================
// FORMAT AI RESPONSE
// ==================================================

function formatAIResponse(text) {

    const container =
        document.createElement("div");

    const lines =
        String(text || "").split("\n");

    let inCodeBlock = false;
    let codeContent = "";


    lines.forEach((line) => {

        // ==========================================
        // CODE BLOCK
        // ==========================================

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
                    codeContent;


                const copyButton =
                    document.createElement("button");

                copyButton.className =
                    "copy-code-btn";

                copyButton.textContent =
                    "Copy";


                copyButton.addEventListener(
                    "click",
                    async () => {

                        try {

                            await navigator.clipboard.writeText(
                                codeContent
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

                container.appendChild(
                    codeWrapper
                );

            }

            return;
        }


        // ==========================================
        // INSIDE CODE BLOCK
        // ==========================================

        if (inCodeBlock) {

            codeContent +=
                line + "\n";

            return;
        }


        // ==========================================
        // EMPTY LINE
        // ==========================================

        if (line.trim() === "") {

            container.appendChild(
                document.createElement("br")
            );

            return;
        }


        // ==========================================
        // HEADINGS
        // ==========================================

        if (line.startsWith("### ")) {

            const heading =
                document.createElement("h4");

            heading.textContent =
                line.substring(4);

            container.appendChild(
                heading
            );

            return;
        }


        if (line.startsWith("## ")) {

            const heading =
                document.createElement("h3");

            heading.textContent =
                line.substring(3);

            container.appendChild(
                heading
            );

            return;
        }


        if (line.startsWith("# ")) {

            const heading =
                document.createElement("h2");

            heading.textContent =
                line.substring(2);

            container.appendChild(
                heading
            );

            return;
        }


        // ==========================================
        // BULLET
        // ==========================================

        if (
            line.trim().startsWith("- ") ||
            line.trim().startsWith("* ")
        ) {

            const bullet =
                document.createElement("div");

            bullet.className =
                "ai-bullet";


            const symbol =
                document.createElement("span");

            symbol.textContent =
                "•";


            const content =
                document.createElement("span");


            addInlineFormatting(
                content,
                line.trim().substring(2)
            );


            bullet.appendChild(symbol);

            bullet.appendChild(content);

            container.appendChild(bullet);

            return;
        }


        // ==========================================
        // NUMBERED LIST
        // ==========================================

        const numberMatch =
            line.match(
                /^\s*(\d+)\.\s+(.*)$/
            );


        if (numberMatch) {

            const numbered =
                document.createElement("div");

            numbered.className =
                "ai-numbered";


            const number =
                document.createElement("span");

            number.textContent =
                numberMatch[1] + ".";


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


        // ==========================================
        // NORMAL TEXT
        // ==========================================

        const paragraph =
            document.createElement("div");

        addInlineFormatting(
            paragraph,
            line
        );

        container.appendChild(
            paragraph
        );

    });


    return container;
}


// ==================================================
// INLINE MARKDOWN
// ==================================================

function addInlineFormatting(
    container,
    text
) {

    const parts =
        String(text || "").split(
            /(\*\*.*?\*\*|`.*?`|\*.*?\*)/g
        );


    parts.forEach(part => {

        // Bold

        if (
            part.startsWith("**") &&
            part.endsWith("**")
        ) {

            const bold =
                document.createElement("strong");

            bold.textContent =
                part.slice(2, -2);

            container.appendChild(
                bold
            );

            return;
        }


        // Inline code

        if (
            part.startsWith("`") &&
            part.endsWith("`")
        ) {

            const code =
                document.createElement("code");

            code.textContent =
                part.slice(1, -1);

            container.appendChild(
                code
            );

            return;
        }


        // Italic

        if (
            part.startsWith("*") &&
            part.endsWith("*")
        ) {

            const italic =
                document.createElement("em");

            italic.textContent =
                part.slice(1, -1);

            container.appendChild(
                italic
            );

            return;
        }


        container.appendChild(
            document.createTextNode(part)
        );

    });
}


// ==================================================
// ADD USER MESSAGE
// ==================================================

function addMessage(
    role,
    text
) {

    const messageDiv =
        document.createElement("div");


    messageDiv.className =
        role === "assistant"
            ? "message bot"
            : "message";


    // Avatar

    const avatar =
        document.createElement("div");

    avatar.className =
        "avatar";

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

    bubble.className =
        "bubble";


    if (role === "assistant") {

        bubble.appendChild(
            formatAIResponse(text)
        );

    } else {

        bubble.textContent =
            text;

    }


    contentWrapper.appendChild(
        bubble
    );


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


    contentWrapper.appendChild(
        time
    );


    messageDiv.appendChild(
        avatar
    );

    messageDiv.appendChild(
        contentWrapper
    );

    messagesBox.appendChild(
        messageDiv
    );


    messagesBox.scrollTop =
        messagesBox.scrollHeight;
}


// ==================================================
// ADD AI MESSAGE
// ==================================================

function addAIMessage(
    text,
    usedRag = false
) {

    const messageDiv =
        document.createElement("div");

    messageDiv.className =
        "message bot";


    // Avatar

    const avatar =
        document.createElement("div");

    avatar.className =
        "avatar";

    avatar.textContent =
        "🤖";


    // Content

    const contentWrapper =
        document.createElement("div");

    contentWrapper.className =
        "message-content";


    // Bubble

    const bubble =
        document.createElement("div");

    bubble.className =
        "bubble";

    bubble.appendChild(
        formatAIResponse(text)
    );


    // Actions

    const actions =
        document.createElement("div");

    actions.className =
        "message-actions";


    // Copy

    const copyButton =
        document.createElement("button");

    copyButton.className =
        "copy-response";

    copyButton.textContent =
        "📋 Copy";


    copyButton.addEventListener(
        "click",
        async () => {

            try {

                await navigator.clipboard.writeText(
                    text
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


    actions.appendChild(
        copyButton
    );


    // RAG status

    const ragStatus =
        document.createElement("span");

    ragStatus.className =
        "rag-status";


    if (usedRag) {

        ragStatus.textContent =
            "📄 Document used";

    } else {

        ragStatus.textContent =
            "🤖 General AI";

    }


    actions.appendChild(
        ragStatus
    );


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


    // Append

    contentWrapper.appendChild(
        bubble
    );

    contentWrapper.appendChild(
        actions
    );

    contentWrapper.appendChild(
        time
    );


    messageDiv.appendChild(
        avatar
    );

    messageDiv.appendChild(
        contentWrapper
    );

    messagesBox.appendChild(
        messageDiv
    );


    messagesBox.scrollTop =
        messagesBox.scrollHeight;
}


// ==================================================
// LOADING
// ==================================================

function showLoading() {

    removeLoading();


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


    messagesBox.appendChild(
        loading
    );


    messagesBox.scrollTop =
        messagesBox.scrollHeight;
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

    const message =
        input.value.trim();


    if (!message) {
        return;
    }


    input.disabled =
        true;

    sendButton.disabled =
        true;


    // User message

    addMessage(
        "user",
        message
    );


    input.value =
        "";


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
                            currentChatId,

                        message:
                            message,

                        document_id:
                            currentDocumentId

                    })
                }
            );


        if (!response.ok) {

            throw new Error(
                `HTTP ${response.status}`
            );

        }


        const data =
            await response.json();


        currentChatId =
            data.chat_id;


        removeLoading();


        addAIMessage(
            data.response,
            data.used_rag === true
        );


        loadChats();


    } catch (error) {

        console.error(
            "Chat Error:",
            error
        );


        removeLoading();


        addMessage(
            "assistant",
            "Sorry, something went wrong. Please try again."
        );

    }


    input.disabled =
        false;

    sendButton.disabled =
        false;

    input.focus();
}


// ==================================================
// NEW CHAT
// ==================================================

async function createNewChat() {

    try {

        const response =
            await fetch(
                `${API_URL}/chats`,
                {
                    method: "POST"
                }
            );


        if (!response.ok) {

            throw new Error(
                "Failed to create chat"
            );

        }


        const data =
            await response.json();


        currentChatId =
            data.chat_id;


        // Remove old PDF context

        currentDocumentId =
            null;


        uploadStatus.textContent =
            "";


        messagesBox.innerHTML =
            "";


        addMessage(
            "assistant",
            "Hello! 👋 How can I help you today?"
        );


        loadChats();

        input.focus();


    } catch (error) {

        console.error(
            "New Chat Error:",
            error
        );

    }
}


// ==================================================
// FORMAT CHAT TIME
// ==================================================

function formatChatTime(
    dateValue
) {

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


    const now =
        new Date();


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
// DELETE CHAT FROM UI
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
// LOAD CHATS
// ==================================================

async function loadChats() {

    try {

        const response =
            await fetch(
                `${API_URL}/chats`
            );


        if (!response.ok) {

            console.error(
                "Failed to load chats"
            );

            return;
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


        container.innerHTML =
            "";


        if (
            !chats ||
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

            container.appendChild(
                empty
            );

            return;
        }


        chats.forEach(chat => {

            // ======================================
            // Chat item
            // ======================================

            const item =
                document.createElement("div");

            item.className =
                "recent-chat";


            if (
                currentChatId &&
                Number(currentChatId) ===
                Number(chat.id)
            ) {

                item.classList.add(
                    "active"
                );

            }


            // ======================================
            // Chat Icon
            // ======================================

            const icon =
                document.createElement("div");

            icon.className =
                "chat-history-icon";

            icon.textContent =
                "💬";


            // ======================================
            // Content
            // ======================================

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
                chat.name ||
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


            content.appendChild(
                title
            );

            content.appendChild(
                time
            );


            // ======================================
            // Delete Button
            // ======================================

            const deleteButton =
                document.createElement("button");

            deleteButton.className =
                "delete-chat-btn";

            deleteButton.type =
                "button";

            deleteButton.title =
                "Delete chat";

            deleteButton.textContent =
                "🗑";


            deleteButton.addEventListener(
                "click",
                async function (event) {

                    event.stopPropagation();

                    const chatId = chat.id;

                    const confirmed = confirm(
                        "Are you sure you want to delete this chat?"
                    );

                    if (!confirmed) {
                        return;
                    }

                    try {

                        const response = await fetch(
                            `${API_URL}/chats/${chatId}`,
                            {
                                method: "DELETE"
                            }
                        );

                        const data = await response.json();

                        if (!response.ok || !data.success) {
                            throw new Error(
                                data.message || "Failed to delete chat"
                            );
                        }

                        // Agar currently open chat delete hui
                        if (
                            currentChatId &&
                            Number(currentChatId) === Number(chatId)
                        ) {

                            currentChatId = null;
                            currentDocumentId = null;

                            messagesBox.innerHTML = "";

                            addMessage(
                                "assistant",
                                "Hello! 👋 How can I help you today?"
                            );
                        }

                        // UI se remove
                        removeChatFromUI(item);

                        // Database se fresh history load
                        await loadChats();

                        console.log(
                            "Chat deleted successfully:",
                            chatId
                        );

                    } catch (error) {

                        console.error(
                            "Delete Chat Error:",
                            error
                        );

                        alert(
                            "Failed to delete chat. Please try again."
                        );
                    }

                }
            );


            // ======================================
            // Open Chat
            // ======================================

            item.addEventListener(
                "click",
                function () {

                    loadChat(
                        chat.id
                    );

                }
            );


            item.appendChild(
                icon
            );

            item.appendChild(
                content
            );

            item.appendChild(
                deleteButton
            );


            container.appendChild(
                item
            );

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
                "Failed to load chat"
            );

        }


        const messages =
            await response.json();


        currentChatId =
            chatId;


        // Reset document context

        currentDocumentId =
            null;


        uploadStatus.textContent =
            "";


        messagesBox.innerHTML =
            "";


        messages.forEach(
            message => {

                addMessage(
                    message.role,
                    message.content
                );

            }
        );


        loadChats();

        input.focus();


    } catch (error) {

        console.error(
            "Load Chat Error:",
            error
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
// PDF UPLOAD BUTTON
// ==================================================

uploadButton.addEventListener(
    "click",
    () => {

        pdfInput.click();

    }
);


// ==================================================
// PDF UPLOAD
// ==================================================

pdfInput.addEventListener(
    "change",
    async () => {

        const file =
            pdfInput.files[0];


        if (!file) {
            return;
        }


        // ==========================================
        // PDF CHECK
        // ==========================================

        if (
            file.type !==
            "application/pdf"
        ) {

            uploadStatus.textContent =
                "❌ Only PDF files are allowed.";

            pdfInput.value =
                "";

            return;
        }


        // ==========================================
        // Loading
        // ==========================================

        uploadStatus.textContent =
            "⏳ Processing PDF...";

        uploadButton.disabled =
            true;


        // ==========================================
        // FormData
        // ==========================================

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
                    `HTTP ${response.status}`
                );

            }


            const data =
                await response.json();


            // ======================================
            // Backend Error
            // ======================================

            if (!data.success) {

                uploadStatus.textContent =
                    `❌ ${data.message}`;

                return;
            }


            // ======================================
            // Save Document ID
            // ======================================

            currentDocumentId =
                data.document_id;


            // ======================================
            // Update Right Panel
            // ======================================

            updateDocumentUI(
                data.filename,
                file.size
            );


            // ======================================
            // Upload Status
            // ======================================

            uploadStatus.textContent =
                `✅ ${data.filename} uploaded`;


            // ======================================
            // Show Upload Message
            // ======================================

            addMessage(
                "assistant",
                `📄 **${data.filename}** is ready.\n\n${data.pages} page(s) processed and ${data.chunks} chunks created.\n\nYou can now ask questions about this document.`
            );


        } catch (error) {

            console.error(
                "Upload Error:",
                error
            );


            uploadStatus.textContent =
                "❌ PDF upload failed.";

        }


        // ==========================================
        // Enable Upload
        // ==========================================

        uploadButton.disabled =
            false;


        // ==========================================
        // Reset File Input
        // ==========================================

        pdfInput.value =
            "";

    }
);


// ==================================================
// SEND BUTTON
// ==================================================

sendButton.addEventListener(
    "click",
    sendMessage
);


// ==================================================
// NEW CHAT BUTTON
// ==================================================

newChatButton.addEventListener(
    "click",
    createNewChat
);


// ==================================================
// ENTER KEY
// ==================================================

input.addEventListener(
    "keydown",
    function (event) {

        if (
            event.key === "Enter" &&
            !event.shiftKey
        ) {

            event.preventDefault();

            sendMessage();

        }

    }
);


// ==================================================
// INITIAL LOAD
// ==================================================

loadChats();