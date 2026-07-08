# AI-Powered Professional Skill Assessment Platform

An intelligent skill assessment platform that evaluates users through adaptive MCQs and AI-generated open-ended questions to provide personalized skill analysis, growth insights, career recommendations, and performance reports.

---

## Features

### User Assessment

- 40 MCQ-based skill assessment
- Category-wise progress tracking
- 20-minute assessment timer
- Dynamic navigation between categories
- Real-time score calculation

### AI-Powered Evaluation

- Personalized open-ended questions generated using Gemini AI
- Context-aware question generation based on:
  - User profile
  - Education
  - Career goals
  - MCQ performance
- AI scoring of subjective responses

### Skill Analysis

Assessment covers five major domains:

1. Cognitive & Creative Skills
2. Work & Professional Behavior
3. Emotional & Social Competence
4. Learning & Self Management
5. Family & Relationships

### Advanced Reports

- Overall Skill Score
- Category-wise Performance
- Skill Radar Analysis
- Growth Projection
- Market Analysis
- Peer Benchmarking
- Personalized Recommendations

### Data Visualization

- Interactive charts using Recharts
- Performance breakdown
- Skill distribution graphs
- Comparative analysis

---

## Tech Stack

### Frontend

- React.js
- React Router
- PapaParse
- Recharts
- React Icons
- jsPDF

### Backend

- FastAPI
- Python
- Pandas
- NumPy
- Google Gemini AI
- Groq API

### AI Models

- Gemini 2.5 Pro
- Groq LLM APIs

---

## Project Structure

```bash
skill-assessment-main
│
├── frontend
│   ├── public
│   ├── src
│   │   ├── pages
│   │   │   ├── Home.js
│   │   │   ├── Assessment.js
│   │   │   ├── MCQCompletion.js
│   │   │   ├── OpenEndedQuestions.js
│   │   │   └── Results.js
│   │   │
│   │   ├── App.js
│   │   └── index.js
│   │
│   └── package.json
│
├── backend
│   ├── app.py
│   ├── Assessment_chat_v2.csv
│   ├── requirements.txt
│   └── package.json
│
└── README.md
```

---

## Installation

### Clone Repository

```bash
git clone <repository-url>
cd skill-assessment-main
```

---

## Frontend Setup

```bash
cd frontend

npm install

npm start
```

Frontend runs on:

```bash
http://localhost:3000
```

---

## Backend Setup

### Create Virtual Environment

```bash
cd backend

python -m venv venv
```

### Activate Environment

Windows

```bash
venv\Scripts\activate
```

Linux/Mac

```bash
source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Create .env

```env
GOOGLE_API_KEY=your_gemini_api_key

GROQ_API_KEY=your_groq_key
GROQ_API_KEY_2=your_groq_key
GROQ_API_KEY_3=your_groq_key
GROQ_API_KEY_4=your_groq_key
```

### Run Backend

```bash
uvicorn app:app --reload
```

Backend runs on:

```bash
http://localhost:8000
```

---

## API Endpoints

### Health Check

```http
GET /
```

### Generate Open-Ended Questions

```http
POST /generate_open_ended_questions
```

Generates personalized AI-based questions using:

- User Profile
- Assessment Scores

---

### Score Open-Ended Responses

```http
POST /score_open_ended_responses
```

Returns:

- Category Scores
- AI Feedback
- Skill Evaluation

---

### Generate Tooltips

```http
POST /generate_tooltips
```

Provides contextual insights for reports.

---

### Generate Growth Projection

```http
POST /generate_growth_projection
```

Predicts future skill growth opportunities.

---

### Generate Market Analysis

```http
POST /generate_market_analysis
```

Provides market relevance analysis.

---

### Generate Peer Benchmark

```http
POST /generate_peer_benchmark
```

Compares user performance against peer groups.

---

## Assessment Workflow

```text
User Registration
        ↓
MCQ Assessment
        ↓
Score Calculation
        ↓
AI Generates Open-Ended Questions
        ↓
User Responses
        ↓
AI Evaluation
        ↓
Combined Scoring
        ↓
Insights & Recommendations
        ↓
Final Skill Report
```

---

## Scoring Methodology

### Final Score

```text
Final Score =
70% MCQ Score +
30% Open-Ended Score
```

### Assessment Areas

- Analytical Thinking
- Creativity
- Communication
- Leadership
- Teamwork
- Emotional Intelligence
- Adaptability
- Self-Management
- Relationship Building

---

## Future Enhancements

- User Authentication
- Assessment History
- Resume Analysis
- Career Recommendation Engine
- Learning Path Suggestions
- Industry Benchmark Dashboard
- Multi-language Support

---

## Deployment

### Frontend

- Render
- Netlify
- Vercel

### Backend

- Render
- Railway
- AWS
- Google Cloud Run

---

