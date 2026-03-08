let questions = [];
let currentQuestionIndex = 0;
let score = 0;
let timeLeft = 15;
let timerInterval;
let canAnswer = true;

const questionCounter = document.getElementById('question-counter');
const quizProgress = document.getElementById('quiz-progress');
const timerSeconds = document.getElementById('timer-seconds');
const questionText = document.getElementById('question-text');
const optionsContainer = document.getElementById('options-container');
const nextBtn = document.getElementById('next-btn');
const submitBtn = document.getElementById('submit-btn');
const questionCard = document.getElementById('question-card');
const resultContainer = document.getElementById('result-container');
const finalScore = document.getElementById('final-score');
const performanceMsg = document.getElementById('performance-msg');
const correctSound = document.getElementById('correct-sound');
const incorrectSound = document.getElementById('incorrect-sound');

async function fetchQuestions() {
    try {
        // Check for AI generated quiz in session storage
        if (categoryName === 'ai') {
            const aiQuiz = sessionStorage.getItem('ai_generated_quiz');
            if (aiQuiz) {
                questions = JSON.parse(aiQuiz);
                showQuestion();
                return;
            }
        }

        // Check for PDF generated quiz
        if (isPDF && pdfId) {
            const response = await fetch(`/api/pdf-questions/${pdfId}`);
            const data = await response.json();
            if (data.results && data.results.length > 0) {
                questions = data.results;
                showQuestion();
                return;
            }
        }

        const response = await fetch(`/api/questions/${categoryId}`);
        const data = await response.json();
        if (data.results && data.results.length > 0) {
            questions = data.results;
            showQuestion();
        } else {
            questionText.innerText = "Failed to load questions. Please try again later.";
        }
    } catch (error) {
        console.error("Error fetching questions:", error);
        questionText.innerText = "Error loading quiz. Please check your connection.";
    }
}

function showQuestion() {
    resetState();
    const currentQuestion = questions[currentQuestionIndex];
    questionText.innerHTML = decodeHTML(currentQuestion.question);
    
    // Combine correct and incorrect answers and shuffle them
    const allOptions = [...currentQuestion.incorrect_answers, currentQuestion.correct_answer];
    shuffleArray(allOptions);

    allOptions.forEach(option => {
        const button = document.createElement('button');
        button.innerHTML = decodeHTML(option);
        button.classList.add('option-btn');
        button.addEventListener('click', () => selectOption(button, option === currentQuestion.correct_answer));
        optionsContainer.appendChild(button);
    });

    // Update UI
    questionCounter.innerText = `Question ${currentQuestionIndex + 1}/${questions.length}`;
    quizProgress.style.width = `${((currentQuestionIndex + 1) / questions.length) * 100}%`;
    
    startTimer();
}

function resetState() {
    canAnswer = true;
    clearInterval(timerInterval);
    timeLeft = 15;
    timerSeconds.innerText = timeLeft;
    optionsContainer.innerHTML = '';
    nextBtn.classList.add('d-none');
    submitBtn.classList.add('d-none');
}

function startTimer() {
    timerInterval = setInterval(() => {
        timeLeft--;
        timerSeconds.innerText = timeLeft;
        if (timeLeft <= 0) {
            clearInterval(timerInterval);
            autoSelectWrong();
        }
    }, 1000);
}

function selectOption(button, isCorrect) {
    if (!canAnswer) return;
    canAnswer = false;
    clearInterval(timerInterval);

    if (isCorrect) {
        score++;
        button.classList.add('correct');
        correctSound.play();
    } else {
        button.classList.add('incorrect');
        incorrectSound.play();
        // Highlight correct answer
        const buttons = optionsContainer.querySelectorAll('.option-btn');
        buttons.forEach(btn => {
            if (btn.innerText === decodeHTML(questions[currentQuestionIndex].correct_answer)) {
                btn.classList.add('correct');
            }
        });
    }

    if (currentQuestionIndex < questions.length - 1) {
        nextBtn.classList.remove('d-none');
    } else {
        submitBtn.classList.remove('d-none');
    }
}

function autoSelectWrong() {
    canAnswer = false;
    const buttons = optionsContainer.querySelectorAll('.option-btn');
    buttons.forEach(btn => {
        if (btn.innerText === decodeHTML(questions[currentQuestionIndex].correct_answer)) {
            btn.classList.add('correct');
        } else {
            btn.classList.add('incorrect');
        }
    });

    if (currentQuestionIndex < questions.length - 1) {
        nextBtn.classList.remove('d-none');
    } else {
        submitBtn.classList.remove('d-none');
    }
}

nextBtn.addEventListener('click', () => {
    currentQuestionIndex++;
    showQuestion();
});

submitBtn.addEventListener('click', async () => {
    // Show loading state
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Saving...';

    // Save score to database
    try {
        const scoreData = {
            category: categoryName,
            score: score,
            total_questions: questions.length
        };

        const response = await fetch('/api/save-score', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(scoreData)
        });
        
        const resultData = await response.json();
        if (resultData.score_id) {
            // Redirect to the dedicated result page
            window.location.href = `/result/${resultData.score_id}`;
        } else {
            console.error("Failed to save score properly");
            alert("Error saving score. Redirecting to dashboard.");
            window.location.href = '/dashboard';
        }
    } catch (error) {
        console.error("Error saving score:", error);
        alert("Network error. Redirecting to dashboard.");
        window.location.href = '/dashboard';
    }
});

// Helper functions
function decodeHTML(html) {
    const txt = document.createElement("textarea");
    txt.innerHTML = html;
    return txt.value;
}

function shuffleArray(array) {
    for (let i = array.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [array[i], array[j]] = [array[j], array[i]];
    }
}

// Start the quiz
fetchQuestions();
