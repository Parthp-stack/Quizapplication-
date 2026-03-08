# QuizMaster - Modern Quiz Application

A responsive quiz application built with Flask and JavaScript, featuring user authentication, category-based quizzes, leaderboards, and a modern dark-mode UI.

## Features

- **User Authentication**: Secure Login and Signup system.
- **Dynamic Quizzes**: Fetch 10-15 questions from Open Trivia DB.
- **Timer & Progress Bar**: 15s timer for each question with visual feedback.
- **Leaderboard**: Global ranking based on user scores.
- **Dark Mode**: Fully responsive UI with theme toggle.
- **Sound Effects**: Audio feedback for correct/incorrect answers.

## Tech Stack

- **Frontend**: HTML5, CSS3 (Bootstrap 5), JavaScript (ES6) - Optimized for Mobile.
- **Backend**: Python Flask (Gunicorn for production).
- **Database**: SQLite (Stored locally as `database.db` for easy hosting).
- **Hosting**: Render.com.
- **Android Support**: WebView wrapper (loads the live Render URL).

## Deployment Steps for Render.com

1.  **Prepare Repository**:
    - Ensure `requirements.txt` includes `gunicorn`.
    - Ensure `Procfile` contains: `web: gunicorn app:app`.
2.  **Create Render Account**:
    - Go to [Render.com](https://render.com) and connect your GitHub/GitLab.
3.  **Create Web Service**:
    - Click **New** -> **Web Service**.
    - Select your repository.
    - **Build Command**: `pip install -r requirements.txt`.
    - **Start Command**: `gunicorn app:app`.
4.  **Environment Variables**:
    - Add `SECRET_KEY` (any random string).
    - If using an API key, add `QUIZ_API_KEY`.
5.  **Access App**: Render will provide a URL (e.g., `https://quiz-app-v1.onrender.com`).

## Android APK Build Instructions (WebView)

1.  **Open Android Studio**:
    - Start a new project with "Empty Views Activity".
2.  **Update AndroidManifest.xml**:
    - Add Internet permission: `<uses-permission android:name="android.permission.INTERNET" />`.
3.  **MainActivity.java**:
    - Set up the WebView:
    ```java
    WebView myWebView = findViewById(R.id.webview);
    WebSettings webSettings = myWebView.getSettings();
    webSettings.setJavaScriptEnabled(true);
    webSettings.setDomStorageEnabled(true);
    myWebView.setWebViewClient(new WebViewClient());
    myWebView.loadUrl("https://your-render-url.onrender.com");
    ```
4.  **Activity Layout (activity_main.xml)**:
    - Add a WebView component:
    ```xml
    <WebView
        android:id="@+id/webview"
        android:layout_width="match_parent"
        android:layout_height="match_parent" />
    ```
5.  **Build APK**:
    - Go to **Build** -> **Build Bundle(s) / APK(s)** -> **Build APK(s)**.
    - Locate the APK and install it on your phone!

## UI Design

The app uses a "Mobile-First" approach with:
- **Card-style layout** for questions and categories.
- **Smooth transitions** for dark mode and question switching.
- **Progressive feedback** with sounds and color-coded results.
