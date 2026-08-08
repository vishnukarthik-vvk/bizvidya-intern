// src/pages/OpenEndedQuestions.js
// Place this file at: src/pages/OpenEndedQuestions.js
//
// Bug fixes applied:
//   B1  – replaced all hardcoded localhost URLs
//   B5  – saveProgressToDB is debounced (was one POST per keystroke)
//   B11 – empty string seed instead of ' ' (leading space in textarea)

import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import './OpenEndedQuestions.css';
import { post, get, del, debounce } from '../api';

const STORAGE_KEY = 'openENdedProgress';

const saveProgressToStorage = data => {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(data)); } catch {}
};
const loadProgressFromStorage = () => {
  try { const r = localStorage.getItem(STORAGE_KEY); return r ? JSON.parse(r) : null; } catch { return null; }
};
const clearProgressFromStorage = () => {
  try { localStorage.removeItem(STORAGE_KEY); } catch {}
};

// B5: debounced – fires at most once every 3 s instead of every keystroke.
const saveProgressToDB = debounce(async (data) => {
  try {
    const userId = localStorage.getItem('user_id');
    if (!userId) return;
    await post('/save_progress', { user_id: parseInt(userId, 10), stage: 'open_ended', data });
  } catch (e) {
    console.error('Failed to save open-ended progress to database:', e);
  }
}, 3000);

const HARDCODED_QUESTIONS = [
  {
    question:
      'Describe a moment — inside or outside school — when you lost track of time because you were so absorbed in what you were doing. What were you doing, and why do you think it captured you?',
  },
  {
    question:
      'If money, marks, and family expectations were completely removed from the equation, what would you study and why?',
  },
  {
    question:
      "What kind of person do you want to be by the time you\u2019re 30 \u2014 not what job, but what kind of person? And what do you think you need to build or learn to get there?",
  },
];

function OpenEndedQuestions() {
  const location = useLocation();
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);

  const [sessionData, setSessionData] = useState(() => {
    if (location.state) return location.state;
    return loadProgressFromStorage() || {};
  });

  const {
    userInfo          = {},
    mcqAnswers        = {},
    totalMCQs         = 0,
    totalScore        = 0,
    categoryScores    = {},
    maxPossibleScore  = 0,
    maxCategoryScores = {},
  } = sessionData;

  const [openEndedQuestions] = useState(HARDCODED_QUESTIONS);

  // B11: seed with '' not ' ' so the textarea has no leading space
  const [responses, setResponses] = useState(() => {
    const saved = loadProgressFromStorage();
    const base  = saved?.responses || {};
    const merged = { ...base };
    HARDCODED_QUESTIONS.forEach((_, idx) => {
      const key = `q${idx + 1}`;
      if (merged[key] === undefined) merged[key] = '';   // was ' ' — fixed
    });
    return merged;
  });

  // Flush on unmount
  useEffect(() => () => saveProgressToDB.flush(), []);

  // Restore from DB if neither navigation state nor localStorage exists
  useEffect(() => {
    if (location.state || loadProgressFromStorage()) return;
    const userId = localStorage.getItem('user_id');
    if (!userId) return;

    (async () => {
      try {
        const { data } = await get(`/get_progress/${userId}/open_ended`);
        if (data) {
          setSessionData(data);
          const merged = { ...(data.responses || {}) };
          HARDCODED_QUESTIONS.forEach((_, idx) => {
            const key = `q${idx + 1}`;
            if (merged[key] === undefined) merged[key] = '';
          });
          setResponses(merged);
        }
      } catch (err) {
        if (err.status !== 404) console.error('Failed to restore open-ended progress from DB:', err);
      }
    })();
  }, [location.state]);

  // B5: autosave – localStorage immediately, DB debounced
  useEffect(() => {
    const payload = {
      userInfo, mcqAnswers, totalMCQs, totalScore,
      categoryScores, maxPossibleScore, maxCategoryScores, responses,
    };
    saveProgressToStorage(payload);
    saveProgressToDB(payload);
  }, [responses]);

  const handleChange = e => {
    const { name, value } = e.target;
    setResponses(prev => ({ ...prev, [name]: value }));
  };

  // ---------------------------------------------------------------------------
  // Word count validation
  // ---------------------------------------------------------------------------
  const handleSubmitClick = async () => {
    if (submitting) return;

    for (let i = 0; i < openEndedQuestions.length; i++) {
      const answer    = responses[`q${i + 1}`] || '';
      const wordCount = answer.trim().split(/\s+/).filter(Boolean).length;
      if (wordCount < 10) {
        alert(`Question ${i + 1} requires at least 10 words. You have written ${wordCount} word(s).`);
        return;
      }
    }

    setSubmitting(true);
    try {
      await handleSubmit();
    } catch {
      // handleSubmit shows its own alert
    } finally {
      setSubmitting(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Scoring + save
  // ---------------------------------------------------------------------------
  async function scoreOpenEndedResponses(userProfile, questionList, responsesMap) {
    const answers = questionList.map((q, idx) => ({
      question:   q.question,
      answer:     responsesMap[`q${idx + 1}`] || '',
      categories: q.categories || [],
    }));

    const payload = {
      user_profile: {
        name:          userProfile.fullName || '',
        age:           Number(userProfile.age) || 0,
        education_level: userProfile.educationLevel || '',
        field:         userProfile.currentRole || userProfile.field || '',
        domain:        userProfile.professionalDomain || userProfile.professionalDomainOther || '',
        exp_level:     userProfile.workExperience || '',
        interests:     userProfile.hobbies
          ? userProfile.hobbies.split(',').map(s => s.trim())
          : (userProfile.interests || []),
        aspirations:   userProfile.careerGoals || userProfile.aspiration || '',
        career_goal:   userProfile.careerGoals || userProfile.careerGoalsOther || '',
      },
      answers,
    };

    const data = await post('/score_open_ended_responses', payload);
    if (!data.scores) throw new Error("Response missing 'scores' key");
    return data.scores;
  }

  const handleSubmit = async () => {
    try {
      const scores = await scoreOpenEndedResponses(userInfo, openEndedQuestions, responses);

      const userId     = localStorage.getItem('user_id');
      let savedToDB    = false;

      if (userId) {
        try {
          await post('/save_open_ended_results', {
            user_id: parseInt(userId, 10),
            answers: openEndedQuestions.map((q, idx) => ({
              question: q.question,
              answer:   responses[`q${idx + 1}`] || '',
            })),
            scores,
          });
          savedToDB = true;
        } catch (e) {
          console.error('Failed to save open-ended results:', e);
        }
      }

      if (savedToDB) {
        clearProgressFromStorage();
        try { await del(`/clear_progress/${userId}/open_ended`); } catch {}
      }

      navigate('/results', {
        state: {
          mcqAnswers,
          openEndedResponses: responses,
          openEndedScores:    scores,
          totalMCQs,
          totalScore,
          categoryScores,
          maxPossibleScore,
          maxCategoryScores,
          questions:          openEndedQuestions,
          userInfo,
          responses,
        },
      });
    } catch (error) {
      console.error('Error scoring open-ended responses:', error);
      alert('Something went wrong while evaluating your answers. Please try again.');
    }
  };

  return (
    <div className="open-ended-container">
      <h1 className="title">Final Reflection: 3 Open Questions</h1>
      <p className="intro-text">
        These are the most important questions in the assessment. Take your time. Write as much
        or as little as feels honest.
      </p>

      {openEndedQuestions.map((q, index) => (
        <div className="question-block" key={index}>
          <label className="question-label">
            Question {index + 1} of {openEndedQuestions.length}
          </label>
          <p className="question-text">{q.question}</p>
          <textarea
            name={`q${index + 1}`}
            value={responses[`q${index + 1}`] || ''}
            onChange={handleChange}
            placeholder="Share your thoughts here... (minimum 10 words required)"
          />
        </div>
      ))}

      {openEndedQuestions.length > 0 && (
        <div className="submit-section">
          <button onClick={handleSubmitClick} className="submit-button" disabled={submitting}>
            {submitting ? (
              <><span className="spinner"></span> Submitting...</>
            ) : (
              '✓ Complete Assessment'
            )}
          </button>
        </div>
      )}
    </div>
  );
}

export default OpenEndedQuestions;
