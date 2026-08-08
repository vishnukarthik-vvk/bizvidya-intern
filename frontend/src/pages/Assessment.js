// src/pages/Assessment.js
// Place this file at: src/pages/Assessment.js
//
// Bug fixes applied:
//   B1  – replaced every hardcoded localhost URL with api.js calls
//   B2  – last question can now be submitted (read newProgress, not stale state)
//   B5  – database writes debounced (was once per second for 20 min)
//   B12 – setSelectedAnswer reads newAnswers not old answers map
//   B13 – categoryProgress updates clone nested objects instead of mutating
//   B14 – assessmentComplete is actually set to true so the timer can't re-fire
//   B15 – removed answersRef (was written but never read)

import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import './Assessment.css';
import Papa from 'papaparse';
import { post, get, del, debounce } from '../api';

const STORAGE_KEY = 'skillAssessmentProgress';

const saveProgressToStorage = data => {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(data)); } catch {}
};
const loadProgressFromStorage = () => {
  try { const r = localStorage.getItem(STORAGE_KEY); return r ? JSON.parse(r) : null; } catch { return null; }
};
const clearProgressFromStorage = () => {
  try { localStorage.removeItem(STORAGE_KEY); } catch {}
};

// B5: debounced – fires at most once every 3 s instead of once per second.
const saveProgressToDB = debounce(async (data) => {
  try {
    const userId = localStorage.getItem('user_id');
    if (!userId) return;
    await post('/save_progress', { user_id: parseInt(userId, 10), stage: 'mcq', data });
  } catch (e) {
    console.error('Failed to save MCQ progress to database:', e);
  }
}, 3000);

const loadQuestions = async ({ setQuestions, setCategories, setCategoryProgress, setCurrentCategory, setLoading, setError }) => {
  try {
    const response = await fetch('/mcq_questions.csv');
    if (!response.ok) throw new Error('Failed to load questions');
    const csvText = await response.text();
    const parsedData = Papa.parse(csvText, { header: true, skipEmptyLines: true });

    const parsedQuestions = parsedData.data.map(row => ({
      id:           row['ID']?.trim(),
      category:     row['category']?.trim(),
      questionText: row['Question Text']?.trim(),
      optionA:      row['Option A']?.trim(),
      optionB:      row['Option B']?.trim(),
      optionC:      row['Option C']?.trim(),
      optionD:      row['Option D']?.trim(),
      optionE:      row['Option E']?.trim(),
      scoreA:       parseInt(row['Score A']) || 0,
      scoreB:       parseInt(row['Score B']) || 0,
      scoreC:       parseInt(row['Score C']) || 0,
      scoreD:       parseInt(row['Score D']) || 0,
      scoreE:       parseInt(row['Score E']) || 0,
    }));

    setQuestions(parsedQuestions);

    const uniqueCategories = [...new Set(parsedQuestions.map(q => q.category))].filter(Boolean);
    setCategories(uniqueCategories);

    const progress = {};
    uniqueCategories.forEach(category => {
      const categoryQuestions = parsedQuestions.filter(q => q.category === category);
      progress[category] = { total: categoryQuestions.length, answered: 0, questions: categoryQuestions };
    });
    setCategoryProgress(progress);

    if (uniqueCategories.length > 0) setCurrentCategory(uniqueCategories[0]);
    setLoading(false);
  } catch (err) {
    console.error('Error loading questions:', err);
    setError('Failed to load questions. Please make sure mcq_questions.csv is in the public folder.');
    setLoading(false);
  }
};

function Assessment() {
  const location  = useLocation();
  const navigate  = useNavigate();

  const [hasRestoredState, setHasRestoredState] = useState(false);
  const [userInfo, setUserInfo] = useState(() => {
    if (location.state?.userInfo) return location.state.userInfo;
    const saved = loadProgressFromStorage();
    return saved?.userInfo || {};
  });

  const [questions,            setQuestions]            = useState([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [selectedAnswer,       setSelectedAnswer]       = useState('');
  const [answers,              setAnswers]              = useState({});
  const [categories,           setCategories]           = useState([]);
  const [currentCategory,      setCurrentCategory]      = useState('');
  const [categoryProgress,     setCategoryProgress]     = useState({});
  const [loading,              setLoading]              = useState(true);
  const [error,                setError]                = useState('');
  const [remainingTime,        setRemainingTime]        = useState(20 * 60);
  const [assessmentComplete,   setAssessmentComplete]   = useState(false); // B14

  // Timer
  useEffect(() => {
    const timer = setInterval(() => {
      setRemainingTime(prev => {
        if (prev <= 1) { clearInterval(timer); return 0; }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // B14: timer fires completion; flag prevents double-fire
  useEffect(() => {
    if (remainingTime === 0 && !assessmentComplete) handleMCQCompletion();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [remainingTime, assessmentComplete]);

  useEffect(() => {
    loadQuestions({ setQuestions, setCategories, setCategoryProgress, setCurrentCategory, setLoading, setError });
  }, []);

  // Flush the debounced save on unmount so a mid-question exit isn't lost
  useEffect(() => () => saveProgressToDB.flush(), []);

  const {
    previousAnswers       = {},
    previousCategory      = '',
    previousIndex         = 0,
    previousRemainingTime = 20 * 60,
    previousProgress      = {},
  } = location.state || {};

  // Restore progress from navigation state → localStorage → DB (in that order)
  useEffect(() => {
    if (hasRestoredState || loading || questions.length === 0) return;

    (async () => {
      let restored = null;

      if (location.state && Object.keys(previousAnswers).length > 0) {
        restored = {
          userInfo:            location.state.userInfo || userInfo,
          answers:             previousAnswers,
          currentCategory:     previousCategory,
          currentQuestionIndex: previousIndex,
          remainingTime:       previousRemainingTime,
          categoryProgress:    previousProgress,
        };
      } else {
        const saved = loadProgressFromStorage();
        if (saved && saved.answers && Object.keys(saved.answers).length > 0) {
          restored = saved;
        } else {
          const userId = localStorage.getItem('user_id');
          if (userId) {
            try {
              const { data } = await get(`/get_progress/${userId}/mcq`);
              if (data?.answers && Object.keys(data.answers).length > 0) restored = data;
            } catch (err) {
              if (err.status !== 404) console.error('Failed to restore MCQ progress:', err);
            }
          }
        }
      }

      if (restored) {
        if (restored.userInfo) setUserInfo(restored.userInfo);
        setAnswers(restored.answers);
        setCurrentCategory(restored.currentCategory || categories[0]);
        setCurrentQuestionIndex(restored.currentQuestionIndex || 0);
        setRemainingTime(restored.remainingTime ?? 20 * 60);

        if (restored.categoryProgress && Object.keys(restored.categoryProgress).length > 0) {
          const recalculated = {};
          Object.entries(restored.categoryProgress).forEach(([category, data]) => {
            recalculated[category] = {
              ...data,
              answered: (data.questions || []).filter(q => restored.answers[q.id]).length,
            };
          });
          setCategoryProgress(recalculated);
          setCategories(Object.keys(restored.categoryProgress));
        } else {
          const progress = {};
          categories.forEach(category => {
            const cqs = questions.filter(q => q.category === category);
            progress[category] = {
              total:    cqs.length,
              answered: cqs.filter(q => restored.answers[q.id]).length,
              questions: cqs,
            };
          });
          setCategoryProgress(progress);
        }

        const firstQ = questions.find(q => q.category === restored.currentCategory) || questions[0];
        setSelectedAnswer(restored.answers[firstQ?.id] || '');
      } else {
        // Fresh start – clear any stale downstream progress
        try { localStorage.removeItem('openEndedProgress'); localStorage.removeItem('assessmentResultsData'); } catch {}
      }

      setHasRestoredState(true);
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loading, questions, hasRestoredState]);

  // B5: keep localStorage in sync immediately; DB write is debounced.
  useEffect(() => {
    if (!hasRestoredState) return;
    const payload = { userInfo, answers, currentCategory, currentQuestionIndex, remainingTime, categoryProgress };
    saveProgressToStorage(payload);
    saveProgressToDB(payload);           // debounced – not per second
  }, [hasRestoredState, userInfo, answers, currentCategory, currentQuestionIndex, categoryProgress]);
  // remainingTime intentionally omitted from DB dependency to avoid one write/sec

  // ---------------------------------------------------------------------------
  // MCQ completion
  // ---------------------------------------------------------------------------
  const handleMCQCompletion = async (finalAnswers = answers) => {
    if (assessmentComplete) return;        // B14: prevent double-fire
    setAssessmentComplete(true);

    const totalQuestions = questions.length;
    let totalScore = 0;
    const categoryScores    = {};
    let maxPossibleScore    = 0;
    const maxCategoryScores = {};

    for (const question of questions) {
      const selected = finalAnswers[question.id];
      let score = 0;
      switch (selected) {
        case 'A': score = question.scoreA || 0; break;
        case 'B': score = question.scoreB || 0; break;
        case 'C': score = question.scoreC || 0; break;
        case 'D': score = question.scoreD || 0; break;
        case 'E': score = question.scoreE || 0; break;
        default: break;
      }
      totalScore += score;

      const maxForQuestion = Math.max(
        question.scoreA || 0, question.scoreB || 0, question.scoreC || 0,
        question.scoreD || 0, question.scoreE || 0
      );
      maxPossibleScore += maxForQuestion;

      if (question.category) {
        if (!categoryScores[question.category]) {
          categoryScores[question.category]    = 0;
          maxCategoryScores[question.category] = 0;
        }
        categoryScores[question.category]    += score;
        maxCategoryScores[question.category] += maxForQuestion;
      }
    }

    const userId = localStorage.getItem('user_id');
    let savedToDB = false;
    if (userId) {
      try {
        await post('/save_mcq_results', {
          user_id:           parseInt(userId, 10),
          answers:           finalAnswers,
          total_score:       totalScore,
          max_possible_score: maxPossibleScore,
          category_scores:   categoryScores,
          max_category_scores: maxCategoryScores,
        });
        savedToDB = true;
      } catch (e) {
        console.error('Failed to save MCQ results:', e);
      }
    }

    if (savedToDB) {
      clearProgressFromStorage();
      try { await del(`/clear_progress/${userId}/mcq`); } catch {}
    }

    navigate('/mcq-completion', {
      state: {
        answers:       finalAnswers,
        totalQuestions,
        currentCategory,
        currentQuestionIndex,
        remainingTime,
        questions,
        categoryProgress,
        totalScore,
        categoryScores,
        maxPossibleScore,
        maxCategoryScores,
        userInfo,
      },
    });
  };

  // ---------------------------------------------------------------------------
  // Navigation helpers
  // ---------------------------------------------------------------------------
  const getCurrentCategoryQuestions = () => questions.filter(q => q.category === currentCategory);
  const getCurrentQuestion          = () => getCurrentCategoryQuestions()[currentQuestionIndex] || null;

  const handleAnswerSelect = option => setSelectedAnswer(option);

  const handleNext = () => {
    const currentQuestion = getCurrentQuestion();
    if (!currentQuestion) return;

    // Build the new answers map
    const newAnswers = { ...answers, [currentQuestion.id]: selectedAnswer };
    setAnswers(newAnswers);

    // B13: rebuild nested objects, never mutate
    const newProgress = {};
    Object.entries(categoryProgress).forEach(([cat, data]) => {
      newProgress[cat] = {
        ...data,
        answered: (data.questions || []).filter(q => newAnswers[q.id]).length,
      };
    });
    setCategoryProgress(newProgress);

    const categoryQuestions    = getCurrentCategoryQuestions();
    const currentCategoryIndex = categories.indexOf(currentCategory);

    if (currentQuestionIndex < categoryQuestions.length - 1) {
      setCurrentQuestionIndex(currentQuestionIndex + 1);
      // B12: read from newAnswers, not stale answers
      setSelectedAnswer(newAnswers[categoryQuestions[currentQuestionIndex + 1]?.id] || '');
    } else if (currentCategoryIndex < categories.length - 1) {
      const nextCategory          = categories[currentCategoryIndex + 1];
      const nextCategoryQuestions = questions.filter(q => q.category === nextCategory);
      setCurrentCategory(nextCategory);
      setCurrentQuestionIndex(0);
      setSelectedAnswer(newAnswers[nextCategoryQuestions[0]?.id] || '');
    } else {
      // B2: count from newProgress, not the just-updated-but-not-yet-rendered categoryProgress
      const { answered, total } = Object.values(newProgress).reduce(
        (acc, cat) => ({ answered: acc.answered + cat.answered, total: acc.total + cat.total }),
        { answered: 0, total: 0 }
      );
      if (total > 0 && answered === total) {
        handleMCQCompletion(newAnswers);
      } else {
        alert(`You still have ${total - answered} question(s) unanswered.`);
      }
    }
  };

  const handlePrevious = () => {
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(currentQuestionIndex - 1);
      const cqs = getCurrentCategoryQuestions();
      setSelectedAnswer(answers[cqs[currentQuestionIndex - 1]?.id] || '');
    } else {
      const currentCategoryIndex = categories.indexOf(currentCategory);
      if (currentCategoryIndex > 0) {
        const prevCategory          = categories[currentCategoryIndex - 1];
        const prevCategoryQuestions = questions.filter(q => q.category === prevCategory);
        setCurrentCategory(prevCategory);
        setCurrentQuestionIndex(prevCategoryQuestions.length - 1);
        setSelectedAnswer(answers[prevCategoryQuestions[prevCategoryQuestions.length - 1]?.id] || '');
      }
    }
  };

  const handleQuestionJump = questionNum => {
    const cqs = getCurrentCategoryQuestions();
    if (questionNum >= 1 && questionNum <= cqs.length) {
      setCurrentQuestionIndex(questionNum - 1);
      setSelectedAnswer(answers[cqs[questionNum - 1]?.id] || '');
    }
  };

  const getTotalProgress = () => {
    const total    = Object.values(categoryProgress).reduce((s, c) => s + c.total, 0);
    const answered = Object.values(categoryProgress).reduce((s, c) => s + c.answered, 0);
    return { total, answered };
  };

  const formatTime = totalSeconds => {
    const m = Math.floor(totalSeconds / 60).toString().padStart(2, '0');
    const s = (totalSeconds % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  // ---------------------------------------------------------------------------
  // Compute scores for the sidebar (needed for MCQ score calculation on display)
  // ---------------------------------------------------------------------------
  let totalScore = 0;
  const categoryScores    = {};
  let maxPossibleScore    = 0;
  const maxCategoryScores = {};

  for (const question of questions) {
    const selected = answers[question.id];
    let score = 0;
    switch (selected) {
      case 'A': score = question.scoreA || 0; break;
      case 'B': score = question.scoreB || 0; break;
      case 'C': score = question.scoreC || 0; break;
      case 'D': score = question.scoreD || 0; break;
      case 'E': score = question.scoreE || 0; break;
      default: break;
    }
    totalScore += score;
    const maxForQuestion = Math.max(
      question.scoreA || 0, question.scoreB || 0, question.scoreC || 0,
      question.scoreD || 0, question.scoreE || 0
    );
    maxPossibleScore += maxForQuestion;
    if (question.category) {
      if (!categoryScores[question.category]) {
        categoryScores[question.category]    = 0;
        maxCategoryScores[question.category] = 0;
      }
      categoryScores[question.category]    += score;
      maxCategoryScores[question.category] += maxForQuestion;
    }
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  if (loading) return <div className="loading-container">Loading questions...</div>;
  if (error)   return (
    <div className="error-container">
      <h2>Error Loading Questions</h2>
      <p>{error}</p>
    </div>
  );

  const currentQuestion      = getCurrentQuestion();
  const categoryQuestionsArr = getCurrentCategoryQuestions();
  const totalProgress        = getTotalProgress();
  const currentCategoryIndex = categories.indexOf(currentCategory);

  return (
    <div className="assessment-app">
      <div className="header">
        <h1 className="header-title">Skill Assessment</h1>
        <div className="timer">
          <span className="timer-icon">🕐</span>
          {formatTime(remainingTime)}
        </div>
      </div>

      <div className="main-content">
        <div className="sidebar">
          <div className="progress-section">
            <h3 className="progress-title">Categories</h3>
            <div className="progress-text">
              {totalProgress.answered} of {totalProgress.total} completed
            </div>
            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{ width: `${totalProgress.total > 0 ? (totalProgress.answered / totalProgress.total) * 100 : 0}%` }}
              />
            </div>
          </div>

          {categories.map(category => (
            <div
              key={category}
              onClick={() => {
                setCurrentCategory(category);
                setCurrentQuestionIndex(0);
                const cqs = questions.filter(q => q.category === category);
                setSelectedAnswer(answers[cqs[0]?.id] || '');
              }}
              className={`category-item ${category === currentCategory ? 'active' : ''}`}
            >
              <div className="category-name">{category}</div>
              <div className="category-progress">
                {categoryProgress[category]?.answered || 0}/{categoryProgress[category]?.total || 0} answered
              </div>

              {category === currentCategory && (
                <div className="question-numbers">
                  {Array.from({ length: categoryProgress[category]?.questions.length || 0 }, (_, i) => i + 1).map(num => (
                    <button
                      key={num}
                      onClick={e => { e.stopPropagation(); handleQuestionJump(num); }}
                      className={`question-number ${num === currentQuestionIndex + 1 ? 'current' : ''} ${
                        answers[categoryProgress[category]?.questions[num - 1]?.id] ? 'answered' : ''
                      }`}
                    >
                      {num}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>

        <div className="question-area">
          {currentQuestion && (
            <div className="question-card">
              <div className="question-header">
                <h2 className="question-category">{currentCategory}</h2>
                <div className="question-counter">
                  Question {currentQuestionIndex + 1} of {categoryQuestionsArr.length}
                </div>
              </div>

              <div className="question-content">
                <h3 className="question-text">{currentQuestion.questionText}</h3>

                <div className="options-container">
                  {[
                    { key: 'A', text: currentQuestion.optionA },
                    { key: 'B', text: currentQuestion.optionB },
                    { key: 'C', text: currentQuestion.optionC },
                    { key: 'D', text: currentQuestion.optionD },
                    { key: 'E', text: currentQuestion.optionE },
                  ].filter(o => o.text).map(option => (
                    <label
                      key={option.key}
                      className={`option-label ${selectedAnswer === option.key ? 'selected' : ''}`}
                    >
                      <input
                        type="radio"
                        name="answer"
                        value={option.key}
                        checked={selectedAnswer === option.key}
                        onChange={() => handleAnswerSelect(option.key)}
                        className="option-radio"
                      />
                      <span className="option-text">{option.text}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="navigation">
                <button
                  onClick={handlePrevious}
                  disabled={currentQuestionIndex === 0 && currentCategoryIndex === 0}
                  className="nav-button prev-button"
                >
                  ← Previous
                </button>
                <div className="category-indicator">
                  Category {currentCategoryIndex + 1} of {categories.length}
                </div>
                <button
                  onClick={handleNext}
                  disabled={!selectedAnswer}
                  className="nav-button next-button"
                >
                  Next →
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default Assessment;
