from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Score, PDF, Question
from config import Config
import requests
import random
import base64
import json
import os
from werkzeug.utils import secure_filename
import PyPDF2
import io

app = Flask(__name__)
app.config.from_object(Config)

# PDF Upload Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'instance', 'uploads')
ALLOWED_EXTENSIONS = {'pdf'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

db.init_app(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create tables if they don't exist
with app.app_context():
    db.create_all()

# Helper functions for PDF processing
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_using_ai_vision(pdf_path, max_pages=3):
    """Extract text from PDF using AI Vision API"""
    try:
        from pdf2image import convert_from_path
        import base64
        from io import BytesIO
        
        print("Converting PDF to images for AI-powered text extraction...")
        images = convert_from_path(pdf_path, first_page=1, last_page=max_pages)
        
        api_key = app.config.get('QUIZ_API_KEY')
        if not api_key:
            print("No API key configured for AI vision extraction")
            return None
        
        all_text = ""
        
        for page_num, image in enumerate(images):
            try:
                print(f"Extracting text from page {page_num + 1} using AI Vision...")
                
                # Convert image to base64
                buffer = BytesIO()
                image.save(buffer, format='PNG')
                buffer.seek(0)
                img_b64 = base64.b64encode(buffer.getvalue()).decode()
                
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost:5000",
                    "X-Title": "QuizMaster"
                }
                
                payload = {
                    "model": app.config.get('QUIZ_VISION_MODEL', 'gpt-4-vision'),
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Extract ALL text content from this PDF page image. Return only the extracted text."
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{img_b64}"
                                    }
                                }
                            ]
                        }
                    ],
                    "temperature": 0.3
                }
                
                response = requests.post("https://openrouter.ai/api/v1/chat/completions", 
                                       headers=headers, json=payload, timeout=30)
                response_json = response.json()
                
                if 'choices' in response_json and response_json['choices']:
                    text = response_json['choices'][0]['message']['content']
                    all_text += text + "\n"
                    print(f"Extracted {len(text)} characters from page {page_num + 1}")
            except Exception as page_error:
                print(f"Failed to extract page {page_num + 1}: {page_error}")
                continue
        
        if all_text and len(all_text.strip()) > 50:
            print(f"Successfully extracted {len(all_text)} characters using AI Vision")
            return all_text
        
        return None
        
    except ImportError:
        print("pdf2image not installed. Cannot convert PDF to images for AI extraction.")
        return None
    except Exception as e:
        print(f"AI Vision extraction failed: {e}")
        return None

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF file with OCR support for scanned PDFs"""
    try:
        text = ""
        
        # Step 1: Try traditional text extraction (for text-based PDFs)
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                # Check if PDF is encrypted
                if pdf_reader.is_encrypted:
                    pdf_reader.decrypt('')
                
                # Extract text from all pages
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text and len(page_text.strip()) > 0:
                            text += page_text + "\n"
                    except Exception as page_error:
                        print(f"Warning: Could not extract text from page {page_num}: {page_error}")
                        continue
        except Exception as pydf_error:
            print(f"PyPDF2 extraction failed: {pydf_error}")
            text = ""

        # If we got substantial text, return it
        if text and len(text.strip()) > 200:
            print(f"Successfully extracted {len(text)} characters using PyPDF2")
            return text

        # Step 2: If text extraction failed, try OCR for scanned PDFs
        print("Attempting OCR extraction for scanned PDF...")
        try:
            from pdf2image import convert_from_path
            import pytesseract
            
            print("Converting PDF to images for OCR...")
            # Convert PDF pages to images
            images = convert_from_path(pdf_path, first_page=1, last_page=10)  # Limit to first 10 pages
            
            ocr_text = ""
            for img_num, image in enumerate(images):
                try:
                    print(f"Performing OCR on page {img_num + 1}...")
                    page_text = pytesseract.image_to_string(image)
                    if page_text and len(page_text.strip()) > 0:
                        ocr_text += page_text + "\n"
                except Exception as ocr_error:
                    print(f"OCR failed for page {img_num}: {ocr_error}")
                    continue
            
            if ocr_text and len(ocr_text.strip()) > 50:
                print(f"Successfully extracted {len(ocr_text)} characters using OCR")
                # Combine with any previously extracted text
                if text:
                    text += "\n" + ocr_text
                else:
                    text = ocr_text
                return text
                
        except ImportError as import_error:
            print(f"OCR libraries not available: {import_error}")
            print("Please install: pip install pdf2image pytesseract")
            print("Also install Tesseract-OCR from: https://github.com/UB-Mannheim/tesseract/wiki")
        except Exception as ocr_error:
            print(f"OCR extraction failed: {ocr_error}")
        
        # Step 3: Try pdfplumber as fallback
        try:
            print("Trying pdfplumber extraction...")
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text and len(page_text.strip()) > 0:
                            text += page_text + "\n"
                    except Exception as page_error:
                        print(f"Warning: pdfplumber page {page_num} extraction failed: {page_error}")
                        continue
            
            if text and len(text.strip()) > 50:
                print(f"Successfully extracted {len(text)} characters using pdfplumber")
                return text
        except ImportError:
            print("pdfplumber not available")
        except Exception as pdfplumber_error:
            print(f"pdfplumber extraction also failed: {pdfplumber_error}")
        
        # Step 4: Last resort - use AI Vision API for scanned PDFs
        print("Attempting AI Vision-based text extraction...")
        ai_text = extract_text_using_ai_vision(pdf_path, max_pages=5)
        if ai_text and len(ai_text.strip()) > 50:
            print(f"Successfully extracted {len(ai_text)} characters using AI Vision")
            return ai_text
        
        # Final validation
        if text and len(text.strip()) > 50:
            return text
        else:
            print(f"Insufficient text extracted. Got {len(text.strip() if text else '')} characters")
            return None
            
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        import traceback
        traceback.print_exc()
        return None

def generate_mcq_from_text(text, pdf_title):
    """Generate MCQ from text using AI model"""
    try:
        api_key = app.config.get('QUIZ_API_KEY')
        model_name = app.config.get('QUIZ_MODEL_NAME', 'gpt-3.5-turbo')
        
        if not api_key:
            return None
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:5000",
            "X-Title": "QuizMaster"
        }
        
        prompt = f"""Analyze the following text and generate 10 multiple-choice questions (MCQs) with 4 options each. 
        
Text: {text[:2000]}

Generate the questions in JSON format exactly like this:
{{"results": [{{"question": "Question text?", "correct_answer": "Answer", "incorrect_answers": ["Wrong1", "Wrong2", "Wrong3"]}}]}}

Important:
- Make questions clear and unambiguous
- Ensure 3 incorrect answers are plausible
- Return ONLY valid JSON, no markdown or extra text"""
        
        payload = {
            "model": model_name,
            "messages": [
                {{"role": "system", "content": "You are an expert educator. Generate clear, well-structured multiple-choice questions."}},
                {{"role": "user", "content": prompt}}
            ],
            "temperature": 0.7
        }
        
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=30)
        response_json = response.json()
        
        if 'error' in response_json:
            print(f"OpenRouter Error: {response_json['error']}")
            return None
        
        if 'choices' not in response_json or not response_json['choices']:
            return None
        
        ai_content = response_json['choices'][0]['message']['content']
        
        # Parse JSON from response
        if "```json" in ai_content:
            ai_content = ai_content.split("```json")[1].split("```")[0].strip()
        elif "```" in ai_content:
            ai_content = ai_content.split("```")[1].split("```")[0].strip()
        
        quiz_data = json.loads(ai_content)
        return quiz_data.get('results', [])
        
    except Exception as e:
        print(f"Error generating MCQ: {e}")
        return None

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        user_exists = User.query.filter_by(email=email).first()
        if user_exists:
            flash('Email already exists.', 'danger')
            return redirect(url_for('signup'))
        
        username_exists = User.query.filter_by(username=username).first()
        if username_exists:
            flash('Username already exists. Please choose another.', 'danger')
            return redirect(url_for('signup'))
        
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(username=username, name=name, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Account created! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        new_password = request.form.get('new_password')
        
        user = User.query.filter_by(username=username).first()
        if user:
            hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
            user.password = hashed_password
            db.session.commit()
            flash('Password has been reset successfully! You can now log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Username not found.', 'danger')
    return render_template('forgot_password.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Login unsuccessful. Please check email and password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', name=current_user.name)

@app.route('/quiz/<category>')
@login_required
def quiz(category):
    category_ids = {
        'science': 17,
        'technology': 18,
        'general': 9,
        'sports': 21
    }
    cat_id = category_ids.get(category.lower(), 9)
    return render_template('quiz.html', category=category, cat_id=cat_id)

@app.route('/api/questions/<int:cat_id>')
@login_required
def get_questions(cat_id):
    # If using the NVIDIA/OpenRouter Model via API Key
    api_key = app.config.get('QUIZ_API_KEY')
    model_name = app.config.get('QUIZ_MODEL_NAME')
    
    # We can keep the Open Trivia DB as fallback, 
    # but the API key is now configured for future AI integration
    api_url = f"https://opentdb.com/api.php?amount=10&category={cat_id}&type=multiple"
    
    # Example of how you would use the new API key and model if needed:
    # headers = {"Authorization": f"Bearer {api_key}"}
    # payload = {"model": model_name, "prompt": "Generate quiz questions..."}
    
    response = requests.get(api_url)
    if response.status_code == 200:
        return jsonify(response.json())
    return jsonify({"error": "Failed to fetch questions"}), 500

@app.route('/api/save-score', methods=['POST'])
@login_required
def save_score():
    data = request.get_json()
    new_score = Score(
        user_id=current_user.id,
        category=data['category'],
        score=data['score'],
        total_questions=data['total_questions']
    )
    db.session.add(new_score)
    db.session.commit()
    # Return the ID of the score to allow viewing it on result page
    return jsonify({"message": "Score saved successfully", "score_id": new_score.id}), 201

@app.route('/result/<int:score_id>')
@login_required
def result(score_id):
    score_data = Score.query.get_or_404(score_id)
    if score_data.user_id != current_user.id:
        return redirect(url_for('dashboard'))
    
    # Calculate performance message
    percentage = (score_data.score / score_data.total_questions) * 100
    if percentage == 100: msg = "Perfect Score! You're a Genius!"
    elif percentage >= 80: msg = "Great job! You know your stuff."
    elif percentage >= 50: msg = "Good effort! Keep practicing."
    else: msg = "Better luck next time! Keep learning."
    
    return render_template('result.html', score=score_data, message=msg)

@app.route('/leaderboard')
@login_required
def leaderboard():
    scores = Score.query.order_by(Score.score.desc()).limit(10).all()
    return render_template('leaderboard.html', scores=scores)

@app.route('/history')
@login_required
def history():
    user_scores = Score.query.filter_by(user_id=current_user.id).order_by(Score.timestamp.desc()).all()
    return render_template('history.html', scores=user_scores)

# PDF Upload and Quiz Generation Routes
@app.route('/upload-pdf', methods=['POST'])
@login_required
def upload_pdf():
    """Handle PDF upload and MCQ generation"""
    try:
        if 'pdf_file' not in request.files:
            return jsonify({"error": "No PDF file provided"}), 400
        
        file = request.files['pdf_file']
        if not file or file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        if not allowed_file(file.filename):
            return jsonify({"error": "Only PDF files are allowed"}), 400
        
        # Save PDF file
        filename = secure_filename(file.filename)
        # Add timestamp to avoid filename conflicts
        import time
        filename = f"{int(time.time())}__{filename}"
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(pdf_path)
        
        # Validate file exists
        if not os.path.exists(pdf_path):
            return jsonify({"error": "Failed to save PDF file"}), 500
        
        # Extract text from PDF
        pdf_text = extract_text_from_pdf(pdf_path)
        if not pdf_text or len(pdf_text.strip()) == 0:
            # Clean up the file
            try:
                os.remove(pdf_path)
            except:
                pass
            
            error_msg = (
                "Failed to extract text from PDF. Possible reasons:\n"
                "1. PDF is encrypted with a password\n"
                "2. PDF has no extractable content\n"
                "3. API key not configured for AI Vision extraction\n"
                "Please try:\n"
                "- Upload a different PDF with extractable text\n"
                "- Or configure your AI API key for advanced extraction"
            )
            return jsonify({"error": error_msg}), 400
        
        # Generate MCQ from text
        questions = generate_mcq_from_text(pdf_text, filename)
        if not questions or len(questions) == 0:
            error_msg = "Failed to generate questions from PDF. The AI service may be unavailable or the extracted text may be insufficient."
            try:
                os.remove(pdf_path)
            except:
                pass
            return jsonify({"error": error_msg}), 400
        
        # Save PDF metadata to database
        pdf_title = request.form.get('pdf_title', filename.replace('.pdf', ''))
        new_pdf = PDF(
            user_id=current_user.id,
            filename=filename,
            title=pdf_title,
            content=pdf_text[:10000]  # Store first 10000 chars
        )
        db.session.add(new_pdf)
        db.session.flush()  # Get the PDF ID
        
        # Save generated questions
        for q in questions:
            question = Question(
                pdf_id=new_pdf.id,
                question=q.get('question', ''),
                correct_answer=q.get('correct_answer', ''),
                incorrect_answers=json.dumps(q.get('incorrect_answers', [])),
                category=pdf_title
            )
            db.session.add(question)
        
        db.session.commit()
        
        return jsonify({
            "message": "PDF processed successfully",
            "pdf_id": new_pdf.id,
            "results": questions
        }), 201
        
    except Exception as e:
        print(f"Error uploading PDF: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route('/my-pdf-quizzes')
@login_required
def my_pdf_quizzes():
    """View user's PDF uploads and generated quizzes"""
    user_pdfs = PDF.query.filter_by(user_id=current_user.id).all()
    return render_template('mypdfs.html', pdfs=user_pdfs)

@app.route('/quiz-from-pdf/<int:pdf_id>')
@login_required
def quiz_from_pdf(pdf_id):
    """Start quiz from PDF questions"""
    pdf = PDF.query.get_or_404(pdf_id)
    if pdf.user_id != current_user.id:
        return redirect(url_for('dashboard'))
    return render_template('quiz.html', category=pdf.title, pdf_id=pdf_id, is_pdf=True)

@app.route('/api/pdf-questions/<int:pdf_id>')
@login_required
def get_pdf_questions(pdf_id):
    """Get questions for a specific PDF quiz"""
    pdf = PDF.query.get_or_404(pdf_id)
    if pdf.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403
    
    questions = Question.query.filter_by(pdf_id=pdf_id).all()
    
    # Format questions to match Open Trivia DB format
    results = []
    for q in questions:
        results.append({
            'question': q.question,
            'correct_answer': q.correct_answer,
            'incorrect_answers': json.loads(q.incorrect_answers)
        })
    
    return jsonify({"results": results})

@app.route('/delete-pdf/<int:pdf_id>', methods=['DELETE', 'POST'])
@login_required
def delete_pdf(pdf_id):
    """Delete a PDF and its associated questions"""
    pdf = PDF.query.get_or_404(pdf_id)
    if pdf.user_id != current_user.id:
        return redirect(url_for('dashboard'))
    
    # Delete PDF file
    pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf.filename)
    if os.path.exists(pdf_path):
        os.remove(pdf_path)
    
    # Delete from database (questions will be deleted due to cascade)
    db.session.delete(pdf)
    db.session.commit()
    
    return jsonify({"message": "PDF deleted successfully"}), 200

@app.route('/convert-pdf-to-images/<int:pdf_id>')
@login_required
def convert_pdf_to_images(pdf_id):
    """Convert PDF to images for vision-based text extraction"""
    pdf = PDF.query.get_or_404(pdf_id)
    if pdf.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        from pdf2image import convert_from_path
        import base64
        from io import BytesIO
        
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf.filename)
        
        # Convert first 5 pages to images
        images = convert_from_path(pdf_path, first_page=1, last_page=5)
        image_data = []
        
        for img in images:
            # Convert PIL image to base64
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            b64 = base64.b64encode(buffer.getvalue()).decode()
            image_data.append(b64)
        
        return jsonify({"images": image_data}), 200
        
    except Exception as e:
        print(f"Error converting PDF to images: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/extract-text-from-images', methods=['POST'])
@login_required
def extract_text_from_images():
    """Extract text from images using AI vision"""
    data = request.get_json()
    images = data.get('images', [])
    
    if not images:
        return jsonify({"error": "No images provided"}), 400
    
    api_key = app.config.get('QUIZ_API_KEY')
    if not api_key:
        return jsonify({"error": "AI extraction not configured"}), 500
    
    try:
        all_text = ""
        
        for img_b64 in images[:3]:  # Limit to first 3 pages
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:5000",
                "X-Title": "QuizMaster"
            }
            
            payload = {
                "model": app.config.get('QUIZ_VISION_MODEL', 'gpt-4-vision'),
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Extract ALL text from this PDF page image. Return only the extracted text, nothing else."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{img_b64}"
                                }
                            }
                        ]
                    }
                ]
            }
            
            response = requests.post("https://openrouter.ai/api/v1/chat/completions", 
                                   headers=headers, json=payload, timeout=30)
            response_json = response.json()
            
            if 'choices' in response_json and response_json['choices']:
                text = response_json['choices'][0]['message']['content']
                all_text += text + "\n"
        
        return jsonify({"text": all_text}), 200
        
    except Exception as e:
        print(f"Error extracting text from images: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/generate-quiz-from-extracted-text', methods=['POST'])
@login_required
def generate_quiz_from_image():
    data = request.get_json()
    image_data = data.get('image') # Base64 encoded image
    
    if not image_data:
        return jsonify({"error": "No image provided"}), 400

    api_key = app.config.get('QUIZ_API_KEY')
    model_name = app.config.get('QUIZ_VISION_MODEL')
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5000", # Optional for OpenRouter
        "X-Title": "QuizMaster"
    }
    
    # Payload for Vision Model
    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Analyze this image and generate 10 multiple-choice questions (MCQs) with 4 options each and indicate the correct answer. Format the response as JSON in the style of Open Trivia DB: {'results': [{'question': '...', 'correct_answer': '...', 'incorrect_answers': ['...', '...', '...']}, ...]}"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_data}"
                        }
                    }
                ]
            }
        ]
    }

    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
        response_json = response.json()
        
        if 'error' in response_json:
            print(f"OpenRouter Vision Error: {response_json['error']}")
            return jsonify({"error": f"Vision Model Error: {response_json['error'].get('message', 'Unknown error')}"}), 500
            
        if 'choices' not in response_json or not response_json['choices']:
            return jsonify({"error": "No response from vision model"}), 500

        ai_content = response_json['choices'][0]['message']['content']
        
        # Parse the JSON string from AI response
        if "```json" in ai_content:
            ai_content = ai_content.split("```json")[1].split("```")[0].strip()
        elif "```" in ai_content:
            ai_content = ai_content.split("```")[1].split("```")[0].strip()
            
        quiz_data = json.loads(ai_content)
        return jsonify(quiz_data)
        
    except Exception as e:
        print(f"Error calling OpenRouter: {e}")
        return jsonify({"error": "Failed to generate quiz from image"}), 500

@app.route('/chat', methods=['POST'])
@login_required
def chat_assistant():
    data = request.get_json()
    user_message = data.get('message')
    
    api_key = app.config.get('QUIZ_API_KEY')
    model_name = app.config.get('QUIZ_CHAT_MODEL')
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5000",
        "X-Title": "QuizMaster"
    }
    
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": "You are a helpful Quiz Assistant. Help the user with quiz questions, explanations, and general knowledge."},
            {"role": "user", "content": user_message}
        ]
    }
    
    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
        response_json = response.json()
        print(f"OpenRouter Chat Response: {response_json}") 
        
        if 'error' in response_json:
            print(f"OpenRouter Chat Error: {response_json['error']}")
            return jsonify({"error": f"AI model error: {response_json['error'].get('message', 'Unknown error')}"}), 500
            
        return jsonify(response_json)
    except Exception as e:
        print(f"Chat Exception: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
