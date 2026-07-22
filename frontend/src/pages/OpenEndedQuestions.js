import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import './OpenEndedQuestions.css';

const STORAGE_KEY = "openENdedProgress";

const saveProgressToStorage = (data) =>{
  try{
    localStorage.setItem(STORAGE_KEY ,JSON.stringify(data));

  } catch (e){
    console.error("Failed to save opem-ended progress",e);
  }
};

const loadProgressFromStorage = () =>{
  try{
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch(e){
    console.error("failed to load saved openended progress",e);
    return null;
  }
};

const clearProgressFromStorage = () =>{
  try{
    localStorage.removeItem(STORAGE_KEY);

  }catch (e){
    console.error("failed to clear saved open ended progress",e);
    
  }
};

// Mirrors in-progress open-ended answers to SQL, tied to the user record from
// the Home page, so progress survives a cleared localStorage / different browser.
const saveProgressToDB = async (data) => {
  try {
    const userId = localStorage.getItem("user_id");
    if (!userId) return;
    await fetch("https://bizvidya-intern.onrender.com/save_progress", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: parseInt(userId, 10),
        stage: "open_ended",
        data,
      }),
    });
  } catch (e) {
    console.error("Failed to save open-ended progress to database:", e);
  }
};


function OpenEndedQuestions() {
  const location = useLocation();
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);

  const handleSubmitClick = async () => {
    if (submitting) return;

    // Check minimum 100 words for each question
    for (let i = 0; i < openEndedQuestions.length; i++) {
      const answer = responses[`q${i + 1}`] || '';
      const wordCount = answer.trim().split(/\s+/).filter(Boolean).length;
      if (wordCount < 100) {
        alert(`Question ${i + 1} requires at least 100 words. You have written ${wordCount} words.`);
        return;
      }
    }

    setSubmitting(true);
    await handleSubmit();
    setSubmitting(false);
  };
  const [sessionData, setSessionData] = useState(() => {
    if (location.state) return location.state;
    return loadProgressFromStorage() || {};
  });

  const {
    userInfo = {},
    mcqAnswers = {},
    totalMCQs = 0,
    totalScore = 0,
    categoryScores = {},
    maxPossibleScore = 0,
    maxCategoryScores = {},
  } = sessionData;
console.log("maxCategoryScores:", maxCategoryScores);
console.log("categoryScores:", categoryScores);
  const [openEndedScores, setOpenEndedScores] = useState([]);
  const [openEndedQuestions, setOpenEndedQuestions] = useState([]);
  const [responses, setResponses] = useState(() => {
  const saved = loadProgressFromStorage();
  return saved?.responses || {};
});

  // If there's nothing to work with locally (no navigation state and no
  // localStorage draft — e.g. localStorage was cleared and the user logged
  // back in on this or another browser), fall back to whatever was last
  // saved to the database for this account.
  useEffect(() => {
    if (location.state || loadProgressFromStorage()) return;

    const userId = localStorage.getItem('user_id');
    if (!userId) return;

    (async () => {
      try {
        const res = await fetch(`https://bizvidya-intern.onrender.com/get_progress/${userId}/open_ended`);
        if (!res.ok) return;
        const { data } = await res.json();
        if (data) {
          setSessionData(data);
          setResponses(data.responses || {});
        }
      } catch (err) {
        console.error('Failed to restore open-ended progress from the database:', err);
      }
    })();
  }, []);

  useEffect(() => {
    const hardcodedQuestions = [
      {
        question: "Describe a moment — inside or outside school — when you lost track of time because you were so absorbed in what you were doing. What were you doing, and why do you think it captured you?"
      },
      {
        question: "If money, marks, and family expectations were completely removed from the equation, what would you study and why?"
      },
      {
        question: "What kind of person do you want to be by the time you're 30 — not what job, but what kind of person? And what do you think you need to build or learn to get there?"
      }
    ];

    setOpenEndedQuestions(hardcodedQuestions);

    setResponses(prev => {
      const merged = {...prev};
      hardcodedQuestions.forEach((_,idx) => {
        const key = `q${idx + 1}`;
        if (merged[key]=== undefined)  merged[key] = ' '; 
      });
      return merged;
    });
  }, []);
    

  const handleChange = (e) => {
    const { name, value } = e.target;
    setResponses(prev => ({ ...prev, [name]: value }));
  };

    useEffect(() => {
    const progressPayload = {
      userInfo,
      mcqAnswers,
      totalMCQs,
      totalScore,
      categoryScores,
      maxPossibleScore,
      maxCategoryScores,
      responses
    };
    saveProgressToStorage(progressPayload);
    saveProgressToDB(progressPayload);
  }, [responses]);

  async function scoreOpenEndedResponses(userProfile, questionList, responsesMap) {
    const answers = questionList.map((q, idx) => ({
      question: q.question,
      answer: responsesMap[`q${idx + 1}`] || '',
      categories: q.categories || []
    }));

    const payload = {
      user_profile: {
        name: userProfile.fullName || "",
        age: Number(userProfile.age) || 0,
        education_level: userProfile.educationLevel || "",
        field: userProfile.currentRole || userProfile.field || "",
        domain: userProfile.professionalDomain || userProfile.professionalDomainOther || "",
        exp_level: userProfile.workExperience || "",
        interests: userProfile.hobbies
          ? userProfile.hobbies.split(',').map(s => s.trim())
          : (userProfile.interests || []),
        aspirations: userProfile.careerGoals || userProfile.aspiration || "",
        career_goal: userProfile.careerGoals || userProfile.careerGoalsOther || "",
      },
      answers
    };

    const startTime = performance.now();
    const API_BASE = process.env.REACT_APP_API_URL || 'http://1https://bizvidya-intern.onrender.com27.0.0.1:8000';
    const response = await fetch(`${API_BASE}/score_open_ended_responses`, {

      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error("Scoring API error:", errorText);
      throw new Error("Failed to fetch open-ended scores");
    }

    const data = await response.json();
    const endTime = performance.now();
    console.log(`Scores time taken : ${(endTime - startTime).toFixed(2)} ms ...endtime is ${endTime}`);
    if (!data.scores) throw new Error("Response missing 'scores' key");

    return data.scores;
  }

  // Submit all answers and navigate to results
  const handleSubmit = async () => {
    try {
      const scores = await scoreOpenEndedResponses(userInfo, openEndedQuestions, responses);
      console.log("open_ended_scores", scores);
      setOpenEndedScores(scores);

      // Persist open-ended answers + scores to SQL, tied to the user record from the Home page
      const userId = localStorage.getItem("user_id");
      let savedToDB = false;
      if (userId) {
        try {
          const saveRes = await fetch("http:/https://bizvidya-intern.onrender.com/save_open_ended_results", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              user_id: parseInt(userId, 10),
              answers: openEndedQuestions.map((q, idx) => ({
                question: q.question,
                answer: responses[`q${idx + 1}`] || "",
              })),
              scores,
            }),
          });
          if (saveRes.ok) {
            savedToDB = true;
          } else {
            const errData = await saveRes.json().catch(() => ({}));
            console.error("Failed to save open-ended results:", errData.detail || saveRes.statusText);
          }
        } catch (e) {
          console.error("Failed to save open-ended results:", e);
        }
      } else {
        console.error("No user_id found in localStorage — open-ended results were not saved to the database.");
      }

      // Only wipe the in-progress backups once the final results are confirmed
      // saved — if the save failed, keep the draft around so nothing is lost.
      if (savedToDB) {
        clearProgressFromStorage();
        try {
          await fetch(`https://bizvidya-intern.onrender.com/clear_progress/${userId}/open_ended`, { method: "DELETE" });
        } catch (e) {
          console.error("Failed to clear saved open-ended progress from the database:", e);
        }
      }

      navigate('/results', {
        state: {
          mcqAnswers,
          openEndedResponses: responses,
          openEndedScores: scores,
          totalMCQs,
          totalScore,
          categoryScores,
          maxPossibleScore,
          maxCategoryScores,
          questions: openEndedQuestions,
          userInfo,
          responses
        }
      });
    } catch (error) {
      console.error("Error scoring open-ended responses:", error);
      alert("Something went wrong while evaluating your answers. Please try again.");
    }
  };

  return (
    <div className="open-ended-container">
      <h1 className="title">Final Reflection: 3 Open Questions</h1>
      <p className="intro-text">
        These are the most important questions in the assessment. Take your time. Write as much or as little as feels honest.
      </p>

      {openEndedQuestions.map((q, index) => (
        <div className="question-block" key={index}>
          <label className="question-label">Question {index + 1} of {openEndedQuestions.length}</label>
          <p className="question-text">{q.question}</p>
          <textarea
            name={`q${index + 1}`}
            value={responses[`q${index + 1}`] || ''}
            onChange={handleChange}
            placeholder="Share your thoughts here... (minimum 100 words required)"
          />
        </div>
      ))}

      {openEndedQuestions.length > 0 && (
        <div className="submit-section">
          <button
            onClick={handleSubmitClick}
            className="submit-button"
            disabled={submitting}
          >
            {submitting ? (
              <>
                <span className="spinner"></span> Submitting...
              </>
            ) : (
              "✓ Complete Assessment"
            )}
          </button>
        </div>
      )}
    </div>
  );
}

export default OpenEndedQuestions;