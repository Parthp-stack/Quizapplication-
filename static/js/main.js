document.addEventListener('DOMContentLoaded', () => {
    const themeToggle = document.getElementById('theme-toggle');
    const body = document.body;
    const icon = themeToggle ? themeToggle.querySelector('i') : null;

    // Check for saved theme preference
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
        body.classList.add('dark-mode');
        if (icon) icon.classList.replace('fa-moon', 'fa-sun');
    }

    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            body.classList.toggle('dark-mode');
            const isDark = body.classList.contains('dark-mode');
            localStorage.setItem('theme', isDark ? 'dark' : 'light');
            
            if (isDark) {
                icon.classList.replace('fa-moon', 'fa-sun');
            } else {
                icon.classList.replace('fa-sun', 'fa-moon');
            }
        });
    }

    // Chat Widget Logic
    const chatToggle = document.getElementById('chat-toggle');
    const chatWidget = document.getElementById('chat-widget');
    const closeChat = document.getElementById('close-chat');
    const chatInput = document.getElementById('chat-input');
    const sendChat = document.getElementById('send-chat');
    const chatBody = document.getElementById('chat-body');

    if (chatToggle && chatWidget) {
        chatToggle.addEventListener('click', () => {
            chatWidget.classList.toggle('d-none');
            chatToggle.classList.toggle('d-none');
        });

        closeChat.addEventListener('click', () => {
            chatWidget.classList.add('d-none');
            chatToggle.classList.remove('d-none');
        });

        const appendMessage = (message, role) => {
            const div = document.createElement('div');
            div.className = `chat-message ${role}`;
            div.textContent = message;
            chatBody.appendChild(div);
            chatBody.scrollTop = chatBody.scrollHeight;
        };

        const handleChat = async () => {
            const message = chatInput.value.trim();
            if (!message) return;

            appendMessage(message, 'user');
            chatInput.value = '';

            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message })
                });
                const data = await response.json();
                if (data.choices && data.choices[0].message.content) {
                    appendMessage(data.choices[0].message.content, 'bot');
                } else if (data.error) {
                    appendMessage(`Error: ${data.error}`, 'bot');
                } else {
                    appendMessage("Sorry, I'm having trouble responding right now.", 'bot');
                }
            } catch (error) {
                appendMessage("Error: Could not connect to assistant.", 'bot');
            }
        };

        sendChat.addEventListener('click', handleChat);
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') handleChat();
        });
    }

    // AI Quiz from Photo Logic
    const aiQuizBtn = document.getElementById('ai-quiz-btn');
    const aiQuizModal = document.getElementById('aiQuizModal');
    const aiImageInput = document.getElementById('ai-image-input');
    const selectImageBtn = document.getElementById('select-image-btn');
    const imagePreviewContainer = document.getElementById('image-preview-container');
    const imagePreview = document.getElementById('image-preview');
    const generateAiQuizBtn = document.getElementById('generate-ai-quiz-btn');
    const aiLoading = document.getElementById('ai-loading');
    const uploadControls = document.getElementById('upload-controls');

    if (aiQuizBtn && aiQuizModal) {
        const bsModal = new bootstrap.Modal(aiQuizModal);
        
        aiQuizBtn.addEventListener('click', () => bsModal.show());

        if (selectImageBtn) {
            selectImageBtn.addEventListener('click', () => aiImageInput.click());
        }

        if (aiImageInput) {
            aiImageInput.addEventListener('change', function() {
                const file = this.files[0];
                if (file) {
                    // Check photo count limit (Simulated using localStorage for now)
                    let photoCount = parseInt(localStorage.getItem('ai_photo_count') || '0');
                    if (photoCount >= 50) {
                        alert("You have reached the limit of 50 photos.");
                        return;
                    }

                    const reader = new FileReader();
                    reader.onload = (e) => {
                        imagePreview.src = e.target.result;
                        imagePreviewContainer.classList.remove('d-none');
                        generateAiQuizBtn.classList.remove('d-none');
                    };
                    reader.readAsDataURL(file);
                }
            });
        }

        if (generateAiQuizBtn) {
            generateAiQuizBtn.addEventListener('click', async () => {
                const base64Image = imagePreview.src.split(',')[1];
                
                aiLoading.classList.remove('d-none');
                generateAiQuizBtn.classList.add('d-none');
                uploadControls.classList.add('d-none');

                try {
                    const response = await fetch('/api/generate-quiz-from-image', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ image: base64Image })
                    });
                    
                    const data = await response.json();
                    if (data.results) {
                        // Store the generated quiz in session storage
                        sessionStorage.setItem('ai_generated_quiz', JSON.stringify(data.results));
                        
                        // Increment photo count
                        let photoCount = parseInt(localStorage.getItem('ai_photo_count') || '0');
                        localStorage.setItem('ai_photo_count', (photoCount + 1).toString());
                        
                        // Redirect to quiz page with special flag
                        window.location.href = '/quiz/ai';
                    } else {
                        alert("AI failed to generate quiz. Try another image.");
                        location.reload();
                    }
                } catch (error) {
                    console.error(error);
                    alert("Error connecting to AI.");
                    location.reload();
                }
            });
        }
    }
});
