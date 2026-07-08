import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import './Assessment.css';
import Papa from 'papaparse';
 
const STORAGE_KEY = "skillAssessmentProgress";

const saveProgressToStorage = (data) =>{
  try{
    localStorage.setItem(STORAGE_KEY ,JSON.stringify(data));
  } catch (e) {
      console.error("failed to save assessment progress",e);
  }

};

const loadProgressFromStorage = () =>{
  try{
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (e){
    console.error("failed to load saved assessment progress", e);
    return null;
  }
};

const clearProgressFromStorage = () =>{
  try{
    localStorage.removeItem(STORAGE_KEY);
  } catch (e) {
    console.error("failed to clear saved progress",e);
  }
};

const loadQuestions = async ({
  setQuestions,
  setCategories,
  setCategoryProgress,
  setCurrentCategory,
  setLoading,
  setError
}) => {  
              
  try {
    const response = await fetch('/mcq_questions.csv');
    if (!response.ok) throw new Error('Failed to load questions');
    const csvText = await response.text();
    const parsedData = Papa.parse(csvText, {
      header: true,
      skipEmptyLines: true,
    });

    const parsedQuestions = parsedData.data.map((row) => ({
      id: row['ID']?.trim(),
      //pillar: row['Pillar']?.trim(),
      //subDomain: row['Sub-domain']?.trim(),
      category: row['category']?.trim(),
      //difficulty: row['Difficulty']?.trim(),
      questionText: row['Question Text']?.trim(),
      optionA: row['Option A']?.trim(),
      optionB: row['Option B']?.trim(),
      optionC: row['Option C']?.trim(),
      optionD: row['Option D']?.trim(),
      optionE: row['Option E']?.trim(),
      scoreA: parseInt(row['Score A']) || 0,
      scoreB: parseInt(row['Score B']) || 0,
      scoreC: parseInt(row['Score C']) || 0,
      scoreD: parseInt(row['Score D']) || 0,
      scoreE: parseInt(row['Score E']) || 0,
      //branchingLogic: row['Branching Logic']?.trim(),
      //branchOptionA: row['Branch_OptionA']?.trim(),
      //branchOptionB: row['Branch_OptionB']?.trim(),
      //branchOptionC: row['Branch_OptionC']?.trim(),
      //branchOptionD: row['Branch_OptionD']?.trim()
    }));

    setQuestions(parsedQuestions);

    const uniqueCategories = [...new Set(parsedQuestions.map(q => q.category))].filter(Boolean);
    setCategories(uniqueCategories);

    const progress = {};
    uniqueCategories.forEach(category => {
      const categoryQuestions = parsedQuestions.filter(q => q.category === category);
      progress[category] = {
        total: categoryQuestions.length,
        answered: 0,
        questions: categoryQuestions
      };
    });
    setCategoryProgress(progress);

    if (uniqueCategories.length > 0) {
      setCurrentCategory(uniqueCategories[0]);
    }

    setLoading(false);
  } catch (err) {
    console.error('Error loading questions:', err);
    setError('Failed to load questions. Please make sure questions.csv is in the public folder and formatted correctly.');
    setLoading(false);
  }
};

function Assessment() {
  const location = useLocation();
  const navigate = useNavigate();
  const [hasRestoredState, setHasRestoredState] = useState(false);
  const [userInfo ,setUserInfo] = useState(() =>{
    if (location.state?.userInfo) return location.state.userInfo;
    const saved = loadProgressFromStorage();
    return saved?.userInfo || {};
  });
  const [questions, setQuestions] = useState([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [selectedAnswer, setSelectedAnswer] = useState('');
  const [answers, setAnswers] = useState({});
  const answersRef = React.useRef({});
  const [categories, setCategories] = useState([]);
  const [currentCategory, setCurrentCategory] = useState('');
  const [categoryProgress, setCategoryProgress] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [startTime] = useState(Date.now());
  const [remainingTime, setRemainingTime] = useState(20 * 60); 
  const [assessmentComplete, setAssessmentComplete] = useState(false);

 
useEffect(() => {
  const timer = setInterval(() => {
    setRemainingTime(prevTime => {
      if (prevTime <= 1) {
        clearInterval(timer);
        return 0;
      }
      return prevTime - 1;
    });
  }, 1000);
  return () => clearInterval(timer);
}, []);

// Add a separate effect that watches remainingTime and fires completion:
useEffect(() => {
  if (remainingTime === 0 && !assessmentComplete) {
    handleMCQCompletion();
  }
}, [remainingTime]);

  useEffect(() => {
  loadQuestions({
    setQuestions,
    setCategories,
    setCategoryProgress,
    setCurrentCategory,
    setLoading,
    setError
  });
}, []);
const {
  previousAnswers = {},
  previousCategory = '',
  previousIndex = 0,
  previousRemainingTime = 20 * 60,
  previousQuestions = [],
  previousProgress = {}
} = location.state || {};
useEffect(() => {
if (!hasRestoredState && !loading && questions.length > 0 ) {
  let restored = null;
  if(location.state && Object.keys(previousAnswers).length > 0){
    restored = {
      userInfo: location.state.userInfo || userInfo,
      answers : previousAnswers,
      currentCategory : previousCategory,
      currentQuestionIndex : previousIndex,
      remainingTime : previousRemainingTime,
      categoryProgress : previousProgress
    };
  } else {
    const saved = loadProgressFromStorage();
    if(saved && saved.answers && Object.keys(saved.answers).length > 0){
      restored = saved;
    }
  }

  if(restored){
    if (restored.userInfo) setUserInfo(restored.userInfo);
    setAnswers(restored.answers);
    setCurrentCategory(restored.currentCategory || categories[0]);
    setCurrentQuestionIndex(restored.currentQuestionIndex || 0);
    setRemainingTime(restored.remaninigTime ?? 20*60);

    if (restored.categoryProgress && Object.keys(restored.categoryProgress).length > 0){
        const recalculated = {};
  Object.entries(restored.categoryProgress).forEach(([category, data]) => {
    recalculated[category] = {
      ...data,
      answered: (data.questions || []).filter(q => restored.answers[q.id]).length
    };
  });
      setCategoryProgress(restored.categoryProgress);
      setCategories(Object.keys(restored.categoryProgress));
    }else{
      const progress = {}
      categories.forEach(category => {
        const categoryQuestions = questions.filter(q => q.category ===category);
        progress[category] = {
          total: categoryQuestions.length,
          answered: categoryQuestions.filter(q => restored.answers[q.id]).length,
          questions: categoryQuestions
        };
      });
      setCategoryProgress(progress);
    }
 

    const firstQuestion = questions.find(q => q.category === restored.currentCategory) || questions[0];
    setSelectedAnswer(restored.answers[firstQuestion?.id] || '');
  }else{  
   try {
      localStorage.removeItem('openEndedProgress');
      localStorage.removeItem('assessmentResultsData');
    } catch (e) {
      console.error('Failed to clear stale downstream progress:', e);
    }
  }

  setHasRestoredState(true);
  }
}, [loading, questions, hasRestoredState]);

// Keep localStorage in sync as the user progresses, so a refresh (F5) or
// closed tab doesn't wipe their answers. Skipped until the restore effect
// above has run once, so we don't overwrite saved data with blank initial
// state.
useEffect(() => {
  if (!hasRestoredState) return;
  saveProgressToStorage({
    userInfo,
    answers,
    currentCategory,
    currentQuestionIndex,
    remainingTime,
    categoryProgress
  });
}, [hasRestoredState, userInfo, answers, currentCategory, currentQuestionIndex, remainingTime, categoryProgress]);


const handleMCQCompletion = () => {
  console.log("called handlemcq");
  const totalQuestions = questions.length;
  console.log("total questions :",totalQuestions);
  let totalScore = 0;
  const categoryScores = {};
  console.log("category scores:", categoryScores);
  let maxPossibleScore = 0;
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
    }

    totalScore += score;

    const maxForQuestion = Math.max( 
      question.scoreA || 0,
      question.scoreB || 0,
      question.scoreC || 0,
      question.scoreD || 0,
      question.scoreE || 0,
      
    );
    maxPossibleScore += maxForQuestion
if (question.category) {
  if (!categoryScores[question.category]) {
    categoryScores[question.category] = 0;
    maxCategoryScores[question.category] = 0;
  }
  categoryScores[question.category] += score;
  maxCategoryScores[question.category] += maxForQuestion;
}
  }

  clearProgressFromStorage();
  navigate('/mcq-completion', {
    state: {
      answers,
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
      userInfo     
    }
  });
};

  const getCurrentCategoryQuestions = () => {
    return questions.filter(q => q.category === currentCategory);
  };

  const getCurrentQuestion = () => {
    const categoryQuestions = getCurrentCategoryQuestions();
    return categoryQuestions[currentQuestionIndex] || null;
  };

  const handleAnswerSelect = (option) => {
    setSelectedAnswer(option);
  };

  const handleNext = () => {
    const currentQuestion = getCurrentQuestion();
    if (!currentQuestion) return;

   const newAnswers = {
  ...answers,
  [currentQuestion.id]: selectedAnswer
};
setAnswers(newAnswers);
answersRef.current = newAnswers;

const newProgress = { ...categoryProgress };
Object.keys(newProgress).forEach(cat => {
  const answeredCount = newProgress[cat].questions.filter(q => newAnswers[q.id]).length;
  newProgress[cat].answered = answeredCount;
});
setCategoryProgress(newProgress);
    const categoryQuestions = getCurrentCategoryQuestions();
    
    if (currentQuestionIndex < categoryQuestions.length - 1) {
      setCurrentQuestionIndex(currentQuestionIndex + 1);
      setSelectedAnswer(answers[categoryQuestions[currentQuestionIndex + 1]?.id] || '');
    } else {
      const currentCategoryIndex = categories.indexOf(currentCategory);
      if (currentCategoryIndex < categories.length - 1) {
        const nextCategory = categories[currentCategoryIndex + 1];
        setCurrentCategory(nextCategory);
        setCurrentQuestionIndex(0);
        const nextCategoryQuestions = questions.filter(q => q.category === nextCategory);
        setSelectedAnswer(answers[nextCategoryQuestions[0]?.id] || '');
      } else {
        
        const categories = Object.values(categoryProgress);
        let answered = 0;
        for(const cat of categories){
          answered = answered + cat.answered
        }
        if (answered===48){  

        handleMCQCompletion();}
        else{
          alert("please answer all the questions")
        }
      }
    }
  };

  const handlePrevious = () => {
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(currentQuestionIndex - 1);
      const categoryQuestions = getCurrentCategoryQuestions();
      setSelectedAnswer(answers[categoryQuestions[currentQuestionIndex - 1]?.id] || '');
    } else {
      const currentCategoryIndex = categories.indexOf(currentCategory);
      if (currentCategoryIndex > 0) {
        const prevCategory = categories[currentCategoryIndex - 1];
        setCurrentCategory(prevCategory);
        const prevCategoryQuestions = questions.filter(q => q.category === prevCategory);
        setCurrentQuestionIndex(prevCategoryQuestions.length - 1);
        setSelectedAnswer(answers[prevCategoryQuestions[prevCategoryQuestions.length - 1]?.id] || '');
      }
    }
  };

  const handleQuestionJump = (questionNum) => {
    const categoryQuestions = getCurrentCategoryQuestions();
    if (questionNum >= 1 && questionNum <= categoryQuestions.length) {
      setCurrentQuestionIndex(questionNum - 1);
      setSelectedAnswer(answers[categoryQuestions[questionNum - 1]?.id] || '');
    }
  };

  const getTotalProgress = () => {
    const total = Object.values(categoryProgress).reduce((sum, cat) => sum + cat.total, 0);
    const answered = Object.values(categoryProgress).reduce((sum, cat) => sum + cat.answered, 0);
    return { total, answered };
  };

  const formatTime = (totalSeconds) => {
    const minutes = Math.floor(totalSeconds / 60).toString().padStart(2, '0');
    const seconds = (totalSeconds % 60).toString().padStart(2, '0');
    return `${minutes}:${seconds}`;
  };

  if (loading) {
    return (
      <div className="loading-container">
        Loading questions...
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-container">
        <div>
          <h2>Error Loading Questions</h2>
          <p>{error}</p>
          <p>Please ensure your questions.csv file is in the public folder with the correct format.</p>
        </div>
      </div>
    );
  }
let totalScore = 0;
const categoryScores = {};
let maxPossibleScore = 0;
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
  }

  totalScore += score;

  const maxForQuestion = Math.max(
    question.scoreA || 0,
    question.scoreB || 0,
    question.scoreC || 0,
    question.scoreD || 0,
    question.scoreE || 0
  );

  maxPossibleScore += maxForQuestion;

  if (question.category) {
    if (!categoryScores[question.category]) {
      categoryScores[question.category] = 0;
      maxCategoryScores[question.category] = 0;
    }

    categoryScores[question.category] += score;
    maxCategoryScores[question.category] += maxForQuestion;
  }
}
console.log("Current Category:", currentCategory);
console.log(categoryScores[currentCategory]);
console.log(maxCategoryScores[currentCategory]);
  const currentQuestion = getCurrentQuestion();
  const categoryQuestions = getCurrentCategoryQuestions();
  const totalProgress = getTotalProgress();
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
                style={{
                  width: `${totalProgress.total > 0 ? (totalProgress.answered / totalProgress.total) * 100 : 0}%`
                }}
              />
            </div>
          </div>

          {categories.map((category) => (
            <div
              key={category}
              onClick={() => {
                setCurrentCategory(category);
                setCurrentQuestionIndex(0);
                const categoryQuestions = questions.filter(q => q.category === category);
                setSelectedAnswer(answers[categoryQuestions[0]?.id] || '');
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
                      onClick={(e) => {
                        e.stopPropagation();
                        handleQuestionJump(num);
                      }}
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
                  Question {currentQuestionIndex + 1} of {categoryQuestions.length}
                </div>
              </div>

              <div className="question-content">
                <h3 className="question-text">
                  {currentQuestion.questionText}
                </h3>
                
                <div className="options-container">
                  {[
                    { key: 'A', text: currentQuestion.optionA },
                    { key: 'B', text: currentQuestion.optionB },
                    { key: 'C', text: currentQuestion.optionC },
                    { key: 'D', text: currentQuestion.optionD },
                    { key: 'E', text: currentQuestion.optionE }
                  ].filter(option => option.text).map(option => (
                    <label key={option.key} className={`option-label ${selectedAnswer === option.key ? 'selected' : ''}`}>
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