// src/pages/Results.js
// Place this file at: src/pages/Results.js
//
// Bug fixes applied:
//   B1 – all 12 hardcoded localhost / 127.0.0.1 URLs replaced with api.js post()
//   B5 – saveResultsToDB is debounced (was called on every section load = ~12 full-blob writes)
//   B24 – removed unused `open` object + stale console.log blocks

import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import './Results.css';
import { LuBrain } from "react-icons/lu";
import { IoPeopleOutline, IoInformationCircleOutline, IoChatbubbleOutline } from "react-icons/io5";
import { MdOutlineWorkOutline, MdFamilyRestroom, MdOutlineSchool, MdOutlineComputer, MdAttachMoney } from "react-icons/md";
import { GiHealthPotion, GiScales } from "react-icons/gi";
import { BsLightbulb, BsGraphUp } from "react-icons/bs";
import { post, debounce } from '../api';

const EDUCATION_LABELS = {
  highSchool:    "High School",
  undergraduate: "Undergraduate",
  bachelor:      "Bachelor's Degree",
  master:        "Master's Degree",
  phd:           "PhD",
};
const EXPERIENCE_LABELS = {
  noExperience: "No Experience",
  entryLevel:   "Entry Level (0-2 years)",
  midLevel:     "Mid Level (3-5 years)",
  seniorLevel:  "Senior Level (5+ years)",
};
const DOMAIN_LABELS = {
  dataScience:         "Data Science",
  finance:             "Finance",
  uxDesign:            "UX Design",
  marketing:           "Marketing",
  softwareEngineering: "Software Engineering",
};
const CAREER_GOAL_LABELS = {
  productManager: "Become a Product Manager",
  dataAnalyst:    "Become a Data Analyst",
  teamLead:       "Become a Team Lead",
  entrepreneur:   "Start My Own Business",
  researcher:     "Pursue Research",
};

const toLabel = (map, value) => (value ? (map[value] || value) : null);

const RESULTS_STORAGE_KEY = 'assessmentResultsData';

const saveResultsToStorage = data => {
  try { localStorage.setItem(RESULTS_STORAGE_KEY, JSON.stringify(data)); } catch {}
};
const loadResultsFromStorage = () => {
  try { const r = localStorage.getItem(RESULTS_STORAGE_KEY); return r ? JSON.parse(r) : null; } catch { return null; }
};

// B5: debounced – fires at most once every 4 s regardless of how many sections load.
const saveResultsToDB = debounce(async (data) => {
  try {
    const userId = localStorage.getItem('user_id');
    if (!userId) return;
    await post('/save_assessment_report', { user_id: parseInt(userId, 10), report: data });
  } catch (e) {
    console.error('Failed to save assessment report to database:', e);
  }
}, 4000);

function Results() {
  const location = useLocation();
  const navigate = useNavigate();

  const skillIcons = {
    "Subject Interest & Domain Curiosity":  <BsLightbulb />,
    "Cognitive & Creative Skills":          <LuBrain />,
    "Academic Aptitude & Learning Style":   <MdOutlineSchool />,
    "Digital & Technological Orientation":  <MdOutlineComputer />,
    "Values & Lifestyle Priorities":        <GiScales />,
    "Financial Awareness & Constraints":    <MdAttachMoney />,
    "Risk Appetite & Ambiguity Tolerance":  <BsGraphUp />,
    "Emotional & Social Competence":        <IoPeopleOutline />,
    "Communication & Language Preference":  <IoChatbubbleOutline />,
    "Personal Management & Wellness":       <GiHealthPotion />,
  };

  const dummyMarketScores = {
    "Subject Interest & Domain Curiosity":  62,
    "Cognitive & Creative Skills":          65,
    "Academic Aptitude & Learning Style":   68,
    "Digital & Technological Orientation":  70,
    "Values & Lifestyle Priorities":        60,
    "Financial Awareness & Constraints":    58,
    "Risk Appetite & Ambiguity Tolerance":  63,
    "Emotional & Social Competence":        60,
    "Communication & Language Preference":  65,
    "Personal Management & Wellness":       67,
  };

  const categorytotal = {
    "Subject Interest & Domain Curiosity":  0,
    "Cognitive & Creative Skills":          0,
    "Academic Aptitude & Learning Style":   0,
    "Digital & Technological Orientation":  0,
    "Values & Lifestyle Priorities":        0,
    "Financial Awareness & Constraints":    0,
    "Risk Appetite & Ambiguity Tolerance":  0,
    "Emotional & Social Competence":        0,
    "Communication & Language Preference":  0,
    "Personal Management & Wellness":       0,
  };

  const savedResults = !location.state ? loadResultsFromStorage() : null;
  const coreSource   = location.state || savedResults || {};

  const {
    mcqAnswers        = {},
    openEndedResponses = {},
    openEndedScores   = [],
    totalMCQs         = 0,
    totalScore        = 0,
    categoryScores    = {},
    questions         = [],
    maxPossibleScore  = 0,
    maxCategoryScores = {},
  } = coreSource;

  // B24: removed unused `open` object and the three console.logs that followed it

  const userInfo = coreSource.userInfo || {};

  const normalizedOpenEnded = useMemo(() => {
    const toEntry = (item, idx) => {
      if (!item) return null;
      if (typeof item === 'string') return { question: `Question ${idx + 1}`, answer: item };
      const question = item.question || item.q || item.prompt || `Question ${idx + 1}`;
      const answer   = item.answer   || item.a || item.response || item.text || '';
      return { question, answer };
    };
    let entries = [];
    if (Array.isArray(openEndedResponses)) {
      entries = openEndedResponses.map(toEntry);
    } else if (openEndedResponses && typeof openEndedResponses === 'object') {
      entries = Object.values(openEndedResponses).map(toEntry);
    }
    return entries.filter(e => e && e.answer && e.answer.trim().length > 0);
  }, [openEndedResponses]);

  const [barChartData, setBarChartData] = useState([]);
  const [skillsData,   setSkillsData]   = useState([]);

  const tooltipsFetched = useRef(!!(savedResults?.tooltips && Object.keys(savedResults.tooltips).length > 0));
  const [tooltips,        setTooltips]        = useState(() => savedResults?.tooltips || {});
  const [loadingTooltips, setLoadingTooltips] = useState(false);

  const growthFetched = useRef(!!savedResults?.growthProjection);
  const [growthProjection,    setGrowthProjection]    = useState(() => savedResults?.growthProjection || null);
  const [loadingGrowth,       setLoadingGrowth]       = useState(false);
  const [growthError,         setGrowthError]         = useState(null);

  const marketAnalysisFetched = useRef(!!savedResults?.marketAnalysis);
  const [marketAnalysis,      setMarketAnalysis]      = useState(() => savedResults?.marketAnalysis || null);
  const [loadingMarketAnalysis, setLoadingMarketAnalysis] = useState(false);
  const [marketAnalysisError, setMarketAnalysisError] = useState(null);

  const peerBenchmarkFetched = useRef(!!savedResults?.peerBenchmark);
  const [peerBenchmark,      setPeerBenchmark]      = useState(() => savedResults?.peerBenchmark || null);
  const [loadingPeerBenchmark, setLoadingPeerBenchmark] = useState(false);
  const [peerBenchmarkError, setPeerBenchmarkError] = useState(null);

  const actionPlanFetched = useRef(!!savedResults?.actionPlan);
  const [actionPlan,       setActionPlan]       = useState(() => savedResults?.actionPlan || null);
  const [loadingActionPlan, setLoadingActionPlan] = useState(false);
  const [actionPlanError,  setActionPlanError]  = useState(null);

  const growthSourcesFetched = useRef(!!savedResults?.growthSources);
  const [growthSources,      setGrowthSources]      = useState(() => savedResults?.growthSources || null);
  const [loadingGrowthSources, setLoadingGrowthSources] = useState(false);
  const [growthSourcesError, setGrowthSourcesError] = useState(null);

  const momentumFetched = useRef(!!(savedResults?.momentumToolkit && savedResults.momentumToolkit.length > 0));
  const [momentumToolkit,  setMomentumToolkit]  = useState(() => savedResults?.momentumToolkit || []);
  const [loadingMomentum,  setLoadingMomentum]  = useState(false);
  const [momentumError,    setMomentumError]    = useState(null);

  const growthOpportunitiesFetched = useRef(!!(savedResults?.growthOpportunities && savedResults.growthOpportunities.length > 0));
  const [growthOpportunities,      setGrowthOpportunities]      = useState(() => savedResults?.growthOpportunities || []);
  const [loadingGrowthOpportunities, setLoadingGrowthOpportunities] = useState(false);
  const [growthOpportunitiesError, setGrowthOpportunitiesError] = useState(null);

  const mentorInsightsFetched = useRef(false);
  const [mentorInsights,     setMentorInsights]     = useState(() => savedResults?.mentorInsights || {});
  const [loadingMentorInsights, setLoadingMentorInsights] = useState(false);
  const [mentorInsightsError, setMentorInsightsError] = useState(null);

  const assessmentSummaryFetched = useRef(!!savedResults?.assessmentSummary);
  const [assessmentSummary,      setAssessmentSummary]      = useState(() => savedResults?.assessmentSummary || null);
  const [loadingAssessmentSummary, setLoadingAssessmentSummary] = useState(false);
  const [assessmentSummaryError, setAssessmentSummaryError] = useState(null);

  const reflectionSummaryFetched = useRef(!!savedResults?.reflectionSummary);
  const [reflectionSummary,      setReflectionSummary]      = useState(() => savedResults?.reflectionSummary || null);
  const [loadingReflectionSummary, setLoadingReflectionSummary] = useState(false);
  const [reflectionSummaryError, setReflectionSummaryError] = useState(null);
  const [reflectionSummaryDone,  setReflectionSummaryDone]  = useState(!!savedResults?.reflectionSummary);

  const careerRecommendationsFetched = useRef(!!savedResults?.careerRecommendations);
  const [careerRecommendations,      setCareerRecommendations]      = useState(() => savedResults?.careerRecommendations || null);
  const [loadingCareerRecommendations, setLoadingCareerRecommendations] = useState(false);
  const [careerRecommendationsError, setCareerRecommendationsError] = useState(null);

  // B5: debounced sync to DB
  useEffect(() => {
    const fullReport = {
      mcqAnswers, openEndedResponses, openEndedScores, totalMCQs, totalScore,
      categoryScores, questions, maxPossibleScore, maxCategoryScores, userInfo,
      tooltips, growthProjection, marketAnalysis, peerBenchmark, actionPlan,
      growthSources, momentumToolkit, growthOpportunities, mentorInsights,
      assessmentSummary, reflectionSummary, careerRecommendations,
    };
    saveResultsToStorage(fullReport);
    saveResultsToDB(fullReport);
  }, [
    tooltips, growthProjection, marketAnalysis, peerBenchmark, actionPlan,
    growthSources, momentumToolkit, growthOpportunities, mentorInsights,
    assessmentSummary, reflectionSummary, careerRecommendations,
  ]);

  const OQ_WEIGHTS = {
    "Subject Interest & Domain Curiosity":  { 1: 12, 2: 15, 3: 3 },
    "Cognitive & Creative Skills":          { 1: 18, 2: 8,  3: 4 },
    "Academic Aptitude & Learning Style":   { 1: 16, 2: 10, 3: 4 },
    "Digital & Technological Orientation":  { 1: 13, 2: 13, 3: 4 },
    "Values & Lifestyle Priorities":        { 1: 5,  2: 10, 3: 15 },
    "Financial Awareness & Constraints":    { 1: 3,  2: 17, 3: 10 },
    "Risk Appetite & Ambiguity Tolerance":  { 1: 6,  2: 16, 3: 8 },
    "Emotional & Social Competence":        { 1: 8,  2: 4,  3: 18 },
    "Communication & Language Preference":  { 1: 10, 2: 10, 3: 10 },
    "Personal Management & Wellness":       { 1: 12, 2: 3,  3: 15 },
  };

  const calculatedData = useMemo(() => {
    const openEndedCategoryScores = {};
    openEndedScores.forEach(scoreObj => {
      const { category, score, question } = scoreObj;
      if (!openEndedCategoryScores[category]) openEndedCategoryScores[category] = {};
      openEndedCategoryScores[category][question] = score;
    });

    const openEndedCategoryAverages = {};
    Object.entries(openEndedCategoryScores).forEach(([category, scoresByQ]) => {
      const weights = OQ_WEIGHTS[category] || { 1: 10, 2: 10, 3: 10 };
      let weightedPercent = 0;
      Object.entries(scoresByQ).forEach(([q, score]) => {
        const w = weights[q] || 0;
        weightedPercent += (score / 100) * w;
      });
      openEndedCategoryAverages[category] = weightedPercent;
    });

    console.log("openEndedCategoryAverages", openEndedCategoryAverages);

    const totalOpenEndedScore    = openEndedScores.reduce((sum, { score }) => sum + score, 0);
    const totalOpenEndedPossible = openEndedScores.length * 100;

    const mcqpercentage        = maxPossibleScore > 0 ? (totalScore / maxPossibleScore) * 70 : 0;
    const open_ended_percentage = (totalOpenEndedScore / totalOpenEndedPossible) * 30;
    const percentage            = mcqpercentage + open_ended_percentage;

    const allCategories = new Set([
      ...Object.keys(categoryScores),
      ...Object.keys(openEndedCategoryAverages),
    ]);

    const chartData = [];
    allCategories.forEach(category => {
      const mcq   = categoryScores[category] || 0;
      const open  = openEndedCategoryAverages[category] || 0;
      console.log(mcq, open);
      const mcqPercent  = (maxCategoryScores[category] || 0) > 0 ? (mcq / maxCategoryScores[category]) * 70 : 0;
      const openPercent = open;
      const weightedScore = Math.round(mcqPercent + openPercent);
      chartData.push({ label: category, value: weightedScore, market: dummyMarketScores[category] || 65 });
    });
    console.log(chartData);

    const skills = chartData.map(item => ({ skill: item.label, percentage: item.value }));

    return { openEndedCategoryAverages, percentage, chartData, skills };
  }, [categoryScores, openEndedScores, totalMCQs, totalScore, maxPossibleScore, maxCategoryScores]);

  useEffect(() => {
    setBarChartData(calculatedData.chartData);
    setSkillsData(calculatedData.skills);
  }, []);

  // ---------------------------------------------------------------------------
  // Tooltip fetch (B1: was http://localhost:8000)
  // ---------------------------------------------------------------------------
  const fetchTooltip = useCallback(async (category, userScore, marketScore, userProfile) => {
    const payload = {
      category,
      user_score:      Number(userScore) || 0,
      benchmark_score: Number(marketScore) || 0,
      user_profile: {
        name:          userProfile.fullName || "Anonymous",
        age:           Number(userProfile.age) || 0,
        education_level: userProfile.educationLevel || "",
        field:         userProfile.field || "",
        domain:        userProfile.domain || userProfile.field || "General",
        exp_level:     userProfile.experienceLevel || "Beginner",
        interests:     userProfile.hobbies ? userProfile.hobbies.split(',').map(s => s.trim()) : (userProfile.interests || []),
        career_goal:   userProfile.careerGoals || userProfile.aspiration || "",
      },
    };
    const startTime = performance.now();
    try {
      const data = await post('/generate_tooltips', payload);
      const endTime = performance.now();
      console.log(`✅ [Tooltip] ${category} - Finished in ${(endTime - startTime).toFixed(2)} ms`);
      return data;
    } catch (err) {
      console.error(`Error fetching tooltip for ${category}:`, err);
      return { user_tooltip: "", benchmark_tooltip: "" };
    }
  }, []);

  useEffect(() => {
    const generateAllTooltips = async () => {
      if (tooltipsFetched.current || calculatedData.chartData.length === 0 || !userInfo?.fullName) return;
      tooltipsFetched.current = true;
      setLoadingTooltips(true);
      const newTooltips = {};
      try {
        const results = await Promise.all(
          calculatedData.chartData.map(async item => {
            try {
              const result = await fetchTooltip(item.label, item.value, item.market, userInfo);
              return { category: item.label, result };
            } catch {
              return { category: item.label, result: { user_tooltip: "", benchmark_tooltip: "" } };
            }
          })
        );
        results.forEach(({ category, result }) => { newTooltips[category] = result; });
        setTooltips(newTooltips);
      } catch (error) {
        console.error('Error generating tooltips:', error);
      } finally {
        setLoadingTooltips(false);
      }
    };
    generateAllTooltips();
  }, []);

  // ---------------------------------------------------------------------------
  // Growth Projection (B1: was https://127.0.0.1:8000)
  // ---------------------------------------------------------------------------
  useEffect(() => {
    const fetchGrowthProjection = async () => {
      if (growthFetched.current || !userInfo || skillsData.length === 0) return;

      const getTierLabel = score => {
        if (score >= 85) return "Top Talent";
        if (score >= 70) return "Emerging Leader";
        if (score >= 55) return "Skilled Contributor";
        return "Emerging Talent";
      };

      growthFetched.current = true;
      setLoadingGrowth(true);
      setGrowthError(null);

      const mapSkillName = name => ({
        "Cognitive & Creative Skills":        "Cognitive_and_Creative_Skills",
        "Work & Professional Behavior":       "Work_and_Professional_Behavior",
        "Emotional & Social Competence":      "Emotional_and_Social_Competence",
        "Personal Management & Wellness":     "Learning_and_Self_Management",
        "Family & Relationships":             "Family_and_Relationships",
      }[name] || name);

      const formattedScores     = {};
      const formattedBenchmarks = {};
      skillsData.forEach(skill => {
        const apiSkillName = mapSkillName(skill.skill);
        formattedScores[apiSkillName]     = skill.percentage || 0;
        formattedBenchmarks[apiSkillName] = dummyMarketScores[skill.skill] || 65;
      });

      const avgScore = Object.values(formattedScores).reduce((a, b) => a + b, 0) /
        Math.max(Object.keys(formattedScores).length, 1);

      const payload = {
        user_data: {
          name:          userInfo.fullName || "Anonymous",
          age:           Number(userInfo.age) || 0,
          education_level: userInfo.educationLevel || "",
          field:         userInfo.field || "",
          domain:        userInfo.domain || userInfo.field || "General",
          exp_level:     userInfo.experienceLevel || "Beginner",
          interests:     userInfo.hobbies ? userInfo.hobbies.split(',').map(s => s.trim()) : (userInfo.interests || []),
          career_goal:   userInfo.careerGoals || userInfo.aspiration || "",
        },
        user_scores:      formattedScores,
        benchmark_scores: formattedBenchmarks,
        tier:             getTierLabel(avgScore),
      };
      const startTime = performance.now();
      try {
        const data = await post('/generate_growth_projection', payload);
        const endTime = performance.now();
        console.log(`✅  Finished in ${(endTime - startTime).toFixed(2)} ms`);
        console.log("📈 Growth Projection:", data);
        setGrowthProjection(data);
      } catch (error) {
        console.error("Error fetching growth projection:", error);
        setGrowthError("Failed to load growth projection.");
      } finally {
        setLoadingGrowth(false);
      }
    };
    fetchGrowthProjection();
  }, [userInfo, skillsData]);

  // ---------------------------------------------------------------------------
  // Market Analysis (B1: was https://127.0.0.1:8000)
  // ---------------------------------------------------------------------------
  useEffect(() => {
    const fetchMarketAnalysis = async () => {
      if (marketAnalysisFetched.current || !userInfo || !calculatedData.percentage || barChartData.length === 0) return;

      const getTierLabel = score => {
        if (score >= 85) return "Top Talent";
        if (score >= 70) return "Emerging Leader";
        if (score >= 55) return "Skilled Contributor";
        return "Emerging Talent";
      };

      marketAnalysisFetched.current = true;
      setLoadingMarketAnalysis(true);
      setMarketAnalysisError(null);

      const benchmark_scores = {};
      barChartData.forEach(item => { benchmark_scores[item.label] = item.market; });

      const avgScore = barChartData.reduce((sum, s) => sum + (s.value || 0), 0) / Math.max(barChartData.length, 1);

      const payload = {
        user_profile: {
          name:          userInfo.fullName || "Anonymous",
          age:           Number(userInfo.age) || 0,
          education_level: userInfo.educationLevel || "",
          field:         userInfo.field || "",
          domain:        userInfo.domain || userInfo.field || "General",
          exp_level:     userInfo.experienceLevel || "Beginner",
          interests:     userInfo.hobbies ? userInfo.hobbies.split(',').map(s => s.trim()) : (userInfo.interests || []),
          career_goal:   userInfo.careerGoals || userInfo.aspiration || "",
        },
        final_score:         Number(totalScore || 0),
        overall_percentage:  calculatedData.percentage || 0,
        percentile:          growthProjection?.growth_projection?.peer_percentile || 50.0,
        strengths:           barChartData.filter(s => s.value >= 65).map(s => s.label),
        weaknesses:          barChartData.filter(s => s.value < 50).map(s => s.label),
        benchmark_scores,
        tier:                getTierLabel(avgScore),
      };
      const startTime = performance.now();
      try {
        const data = await post('/generate_market_analysis', payload);
        const endTime = performance.now();
        console.log(`✅  Finished in ${(endTime - startTime).toFixed(2)} ms`);
        console.log("📊 Market Analysis:", data);
        setMarketAnalysis(data);
      } catch (error) {
        console.error("Error fetching market analysis:", error);
        setMarketAnalysisError("Failed to load market analysis.");
      } finally {
        setLoadingMarketAnalysis(false);
      }
    };
    fetchMarketAnalysis();
  }, [userInfo, barChartData, calculatedData.percentage, totalScore, growthProjection]);

  // ---------------------------------------------------------------------------
  // Peer Benchmark (B1: was http://localhost:8000)
  // ---------------------------------------------------------------------------
  useEffect(() => {
    const fetchPeerBenchmark = async () => {
      if (peerBenchmarkFetched.current || !userInfo || barChartData.length === 0 || !calculatedData.percentage) return;

      peerBenchmarkFetched.current = true;
      setLoadingPeerBenchmark(true);
      setPeerBenchmarkError(null);

      const mcqScores = {};
      const openScores = {};
      const benchmarks = {};
      barChartData.forEach(item => {
        mcqScores[item.label]  = categoryScores[item.label] || 0;
        openScores[item.label] = calculatedData.openEndedCategoryAverages[item.label] || 0;
        benchmarks[item.label] = item.market;
      });

      const payload = {
        user_data: {
          name:          userInfo.fullName || "Anonymous",
          age:           Number(userInfo.age) || 0,
          education_level: userInfo.educationLevel || "",
          field:         userInfo.field || "",
          domain:        userInfo.domain || userInfo.field || "General",
          exp_level:     userInfo.experienceLevel || "Beginner",
          interests:     userInfo.hobbies ? userInfo.hobbies.split(',').map(s => s.trim()) : (userInfo.interests || []),
          career_goal:   userInfo.careerGoals || userInfo.aspiration || "",
        },
        combined_score:    calculatedData.percentage || 0,
        mcq_scores:        mcqScores,
        open_scores:       openScores,
        strong_categories: barChartData.filter(i => i.value >= 65).map(i => i.label),
        weak_categories:   barChartData.filter(i => i.value < 50).map(i => i.label),
        benchmarks,
      };
      const startTime = performance.now();
      try {
        const data = await post('/generate_peer_benchmark', payload);
        const endTime = performance.now();
        console.log(`✅  Finished in ${(endTime - startTime).toFixed(2)} ms`);
        console.log("peer benchmark", data);
        setPeerBenchmark(data);
      } catch (err) {
        console.error("Peer benchmark error:", err);
        setPeerBenchmarkError("Failed to fetch peer benchmark");
      } finally {
        setLoadingPeerBenchmark(false);
      }
    };
    fetchPeerBenchmark();
  }, [userInfo, barChartData, calculatedData.percentage, calculatedData.openEndedCategoryAverages]);

  // ---------------------------------------------------------------------------
  // Action Plan (B1: was http://localhost:8000)
  // ---------------------------------------------------------------------------
  const parseRoadmapText = roadmapText => {
    if (!roadmapText) return [];
    const phases = [];
    const phaseSections = roadmapText.split(/### PHASE \d+ \([^)]+\) – /);
    const titleMatches  = [...roadmapText.matchAll(/### PHASE \d+ \(([^)]+)\) – ([^\n]+)/g)];

    for (let i = 1; i < phaseSections.length; i++) {
      const phaseContent = phaseSections[i];
      const title = titleMatches[i - 1] ? titleMatches[i - 1][2].trim() : `Phase ${i}`;

      const focusMatch = phaseContent.match(/- \*\*Focus Areas:\*\*\s*(.*?)(?=\n- \*\*Weekly Actions:|\n- \*\*Milestone|$)/s);
      const focus = focusMatch ? focusMatch[1].trim().replace(/\n/g, ' ') : 'Not specified';

      const weeklyActionsMatch = phaseContent.match(/- \*\*Weekly Actions:\*\*\s*((?:\s*- Week \d+:.*\n*)+)/s);
      let weeklyActions = [];
      if (weeklyActionsMatch) {
        weeklyActions = weeklyActionsMatch[1].trim()
          .split(/\n\s*-\s*/).map(a => a.trim())
          .filter(a => a.startsWith("Week"))
          .map(a => a.replace(/^Week \d+:\s*/, '').trim());
      }

      const milestoneMatch = phaseContent.match(/- \*\*Milestone by Day \d+:\*\*\s*(.*)/);
      const milestone = milestoneMatch ? milestoneMatch[1].trim() : 'Not specified';

      phases.push({ title, focus, weekly_actions: weeklyActions, milestone });
    }
    return phases;
  };

  useEffect(() => {
    const fetchActionPlan = async () => {
      if (actionPlanFetched.current || !userInfo || barChartData.length === 0) return;

      actionPlanFetched.current = true;
      setLoadingActionPlan(true);
      setActionPlanError(null);

      const mcqScores        = {};
      const openScores       = {};
      const marketBenchmarks = {};
      const strongCategories  = [];
      const moderateCategories = [];
      const weakCategories   = [];

      barChartData.forEach(item => {
        mcqScores[item.label]        = categoryScores[item.label] || 0;
        openScores[item.label]       = calculatedData.openEndedCategoryAverages[item.label] || 0;
        marketBenchmarks[item.label] = item.market || 65;
        const score = item.value || 0;
        if (score >= 65)      strongCategories.push(item.label);
        else if (score >= 50) moderateCategories.push(item.label);
        else                  weakCategories.push(item.label);
      });

      const payload = {
        user_data: {
          name:          userInfo.fullName || "Anonymous",
          age:           Number(userInfo.age) || 0,
          education_level: userInfo.educationLevel || "",
          field:         userInfo.field || "",
          domain:        userInfo.domain || userInfo.field || "General",
          exp_level:     userInfo.experienceLevel || "Beginner",
          interests:     userInfo.hobbies ? userInfo.hobbies.split(',').map(s => s.trim()) : (userInfo.interests || []),
          career_goal:   userInfo.careerGoals || userInfo.aspiration || "",
        },
        mcq_scores:          mcqScores,
        open_scores:         openScores,
        strong_categories:   strongCategories,
        moderate_categories: moderateCategories,
        weak_categories:     weakCategories,
        market_benchmarks:   marketBenchmarks,
      };
      const startTime = performance.now();
      try {
        const data = await post('/generate_action_plan', payload);
        const endTime = performance.now();
        console.log(`✅  Finished in ${(endTime - startTime).toFixed(2)} ms`);
        const parsedActionPlan = parseRoadmapText(data.roadmap_text);
        setActionPlan(parsedActionPlan);
        console.log("action plan", parsedActionPlan);
      } catch (err) {
        console.error("Action plan error:", err);
        setActionPlanError("Failed to fetch action plan");
      } finally {
        setLoadingActionPlan(false);
      }
    };
    fetchActionPlan();
  }, [userInfo, barChartData]);

  // ---------------------------------------------------------------------------
  // Growth Sources (B1: was http://localhost:8000)
  // ---------------------------------------------------------------------------
  useEffect(() => {
    const fetchGrowthSources = async () => {
      if (growthSourcesFetched.current || !userInfo || !growthProjection || barChartData.length === 0) return;

      growthSourcesFetched.current = true;
      setLoadingGrowthSources(true);
      setGrowthSourcesError(null);

      const weakCategories     = [];
      const moderateCategories = [];
      const strongCategories   = [];
      const combinedScores     = {};

      barChartData.forEach(item => {
        const score1 = categoryScores[item.label] || 0;
        const score2 = calculatedData.openEndedCategoryAverages[item.label] || 0;
        combinedScores[item.label] = Number(((score1 + score2) / 2).toFixed(1));
        if (item.value < 50)      weakCategories.push(item.label);
        else if (item.value < 65) moderateCategories.push(item.label);
        else                      strongCategories.push(item.label);
      });

      const payload = {
        user_data: {
          name:          userInfo.fullName || "Anonymous",
          age:           Number(userInfo.age) || 0,
          education_level: userInfo.educationLevel || "",
          field:         userInfo.field || "",
          domain:        userInfo.domain || userInfo.field || "General",
          exp_level:     userInfo.experienceLevel || "Beginner",
          interests:     userInfo.hobbies ? userInfo.hobbies.split(',').map(s => s.trim()) : (userInfo.interests || []),
          career_goal:   userInfo.careerGoals || userInfo.aspiration || "",
        },
        weak_categories:     weakCategories,
        moderate_categories: moderateCategories,
        strong_categories:   strongCategories,
        combined_scores:     combinedScores,
        projection: {
          growth_projection: {
            current_score: growthProjection.current_score,
            "3_months":    growthProjection["3_months"],
            "6_months":    growthProjection["6_months"],
            "12_months":   growthProjection["12_months"],
          },
        },
      };
      const startTime = performance.now();
      try {
        const data = await post('/generate_growth_sources', payload);
        const endTime = performance.now();
        console.log(`✅  Finished in ${(endTime - startTime).toFixed(2)} ms`);
        console.log("growth resources", data);
        setGrowthSources(data.sources);
      } catch (err) {
        console.error("Growth sources error:", err);
        setGrowthSourcesError("Failed to fetch growth sources");
      } finally {
        setLoadingGrowthSources(false);
      }
    };
    fetchGrowthSources();
  }, [userInfo, growthProjection, barChartData]);

  // ---------------------------------------------------------------------------
  // Momentum Toolkit (B1: was http://localhost:8000)
  // ---------------------------------------------------------------------------
  useEffect(() => {
    const fetchMomentumToolkit = async () => {
      if (momentumFetched.current) return;
      momentumFetched.current = true;
      setLoadingMomentum(true);
      setMomentumError(null);
      const startTime = performance.now();
      try {
        const data = await post('/generate_momentum_toolkit', {});
        const endTime = performance.now();
        console.log(`✅  Finished in ${(endTime - startTime).toFixed(2)} ms`);
        console.log("tool kit", data);
        setMomentumToolkit(data.momentum_toolkit);
      } catch (err) {
        console.error("Momentum Toolkit fetch error:", err);
        setMomentumError("Failed to load quick actions");
      } finally {
        setLoadingMomentum(false);
      }
    };
    fetchMomentumToolkit();
  }, []);

  // ---------------------------------------------------------------------------
  // Growth Opportunities (B1: was http://localhost:8000)
  // ---------------------------------------------------------------------------
  useEffect(() => {
    const fetchGrowthOpportunities = async () => {
      if (growthOpportunitiesFetched.current || !userInfo || barChartData.length === 0) return;

      growthOpportunitiesFetched.current = true;
      setLoadingGrowthOpportunities(true);
      setGrowthOpportunitiesError(null);

      const scores     = {};
      const benchmarks = {};
      barChartData.forEach(item => {
        scores[item.label]     = categoryScores[item.label] || 0;
        benchmarks[item.label] = item.market || 65;
      });

      const payload = {
        user_profile: {
          name:          userInfo.fullName || "Anonymous",
          age:           Number(userInfo.age) || 0,
          education_level: userInfo.educationLevel || "",
          field:         userInfo.field || "",
          domain:        userInfo.domain || userInfo.field || "General",
          exp_level:     userInfo.experienceLevel || "Beginner",
          interests:     userInfo.hobbies ? userInfo.hobbies.split(',').map(s => s.trim()) : (userInfo.interests || []),
          career_goal:   userInfo.careerGoals || userInfo.aspiration || "",
        },
        scores,
        benchmarks,
      };
      const startTime = performance.now();
      try {
        const data = await post('/generate_growth_opportunities', payload);
        const endTime = performance.now();
        console.log(`✅  Finished in ${(endTime - startTime).toFixed(2)} ms`);
        console.log("opportunities", data);
        setGrowthOpportunities(data.opportunities);
      } catch (err) {
        console.error("Growth Opportunities error:", err);
        setGrowthOpportunitiesError("Failed to fetch personalized growth opportunities");
      } finally {
        setLoadingGrowthOpportunities(false);
      }
    };
    fetchGrowthOpportunities();
  }, [userInfo, barChartData]);

  // ---------------------------------------------------------------------------
  // Helper functions
  // ---------------------------------------------------------------------------
  const getPerformanceLevel = useCallback(score => {
    if (score >= 80) return 'Excellent';
    if (score >= 60) return 'Good';
    if (score >= 40) return 'Developing';
    return 'Needs Improvement';
  }, []);

  const getMarketPercentile = useCallback(score => {
    if (score >= 80) return 'Top 10%';
    if (score >= 60) return 'Top 25%';
    if (score >= 40) return 'Top 60%';
    return 'Bottom 20%';
  }, []);

  const getSalaryRangeINR = useCallback(score => {
    if (score >= 80) return '₹12L – ₹16L';
    if (score >= 60) return '₹9L – ₹12L';
    if (score >= 40) return '₹6L – ₹9L';
    return '₹3L – ₹6L';
  }, []);

  const getSalaryRangeUSD = useCallback(score => {
    if (score >= 80) return '$80k – $100k';
    if (score >= 60) return '$65k – $80k';
    if (score >= 40) return '$50k – $65k';
    return '$30k – $45k';
  }, []);

  const percentage       = calculatedData.percentage;
  const salaryRangeINR   = getSalaryRangeINR(percentage);
  const salaryRangeUSD   = getSalaryRangeUSD(percentage);
  const percentileText   = getMarketPercentile(percentage);

  const getPercentileNumber = useCallback(text => {
    const match = text.match(/(\d+)%/);
    return match ? parseInt(match[1], 10) : 0;
  }, []);

  const percentileNumber = getPercentileNumber(percentileText);

  const barMessageText = useCallback(score => {
    if (score >= 40) return `You are ahead of ${100 - percentileNumber}% of your peers`;
    return `You are ahead of ${percentileNumber}% of your peers`;
  }, [percentileNumber]);

  const barMessage = barMessageText(percentage);

  const getStrongestSkill = useCallback(() => {
    if (Object.keys(categoryScores).length === 0 || !calculatedData.openEndedCategoryAverages) return 'Strategic Thinking';
    let strongestSkill = '';
    let highestScore   = 0;
    Object.keys(categoryScores).forEach(category => {
      const mcq  = categoryScores[category] || 0;
      const open = calculatedData.openEndedCategoryAverages[category] || 0;
      const weightedScore = Math.round((mcq / 160) * 70 + (open / 50) * 30);
      if (weightedScore > highestScore) { highestScore = weightedScore; strongestSkill = category; }
    });
    return strongestSkill || 'Strategic Thinking';
  }, [categoryScores, calculatedData.openEndedCategoryAverages]);

  const strongestSkill     = getStrongestSkill();
  const normalizedSkill    = strongestSkill.trim();
  const strongestSkillIcon = skillIcons[normalizedSkill] || "💜";

  const buildUserProfilePayload = useCallback(profile => ({
    name:          profile.fullName || "Anonymous",
    age:           Number(profile.age) || 0,
    education_level: profile.educationLevel || "",
    field:         profile.field || "",
    domain:        profile.domain || profile.field || "General",
    exp_level:     profile.experienceLevel || "Beginner",
    interests:     profile.hobbies ? profile.hobbies.split(',').map(s => s.trim()) : (profile.interests || []),
    career_goal:   profile.careerGoals || profile.aspiration || "",
  }), []);

  // ---------------------------------------------------------------------------
  // Assessment Summary (B1: was http://localhost:8000)
  // ---------------------------------------------------------------------------
  useEffect(() => {
    const fetchAssessmentSummary = async () => {
      if (assessmentSummaryFetched.current || !userInfo?.fullName || barChartData.length === 0) return;
      assessmentSummaryFetched.current = true;
      setLoadingAssessmentSummary(true);
      setAssessmentSummaryError(null);

      const categoryScoresPayload = {};
      barChartData.forEach(item => { categoryScoresPayload[item.label] = item.value || 0; });

      const payload = {
        user_profile:        buildUserProfilePayload(userInfo),
        category_scores:     categoryScoresPayload,
        open_ended_answers:  normalizedOpenEnded.map(({ question, answer }) => ({ question, answer, categories: [] })),
        overall_score:       Number(percentage) || 0,
        performance_level:   getPerformanceLevel(percentage),
        strongest_skill:     strongestSkill,
      };
      const startTime = performance.now();
      try {
        const data = await post('/generate_assessment_summary', payload);
        const endTime = performance.now();
        console.log(`✅ [Assessment Summary] Finished in ${(endTime - startTime).toFixed(2)} ms`);
        setAssessmentSummary(data.assessment_summary);
      } catch (err) {
        console.error("Assessment summary error:", err);
        setAssessmentSummaryError("Failed to load assessment summary");
      } finally {
        setLoadingAssessmentSummary(false);
      }
    };
    fetchAssessmentSummary();
  }, [userInfo, barChartData, percentage, strongestSkill, normalizedOpenEnded, getPerformanceLevel, buildUserProfilePayload]);

  // ---------------------------------------------------------------------------
  // Reflection Summary (B1: was http://localhost:8000)
  // ---------------------------------------------------------------------------
  useEffect(() => {
    const fetchReflectionSummary = async () => {
      if (reflectionSummaryFetched.current || !userInfo?.fullName || normalizedOpenEnded.length === 0) return;
      reflectionSummaryFetched.current = true;
      setLoadingReflectionSummary(true);
      setReflectionSummaryError(null);

      const payload = {
        user_profile:       buildUserProfilePayload(userInfo),
        open_ended_answers: normalizedOpenEnded.map(({ question, answer }) => ({ question, answer, categories: [] })),
      };
      const startTime = performance.now();
      try {
        const data = await post('/generate_reflection_summary', payload);
        const endTime = performance.now();
        console.log(`✅ [Reflection Summary] Finished in ${(endTime - startTime).toFixed(2)} ms`);
        setReflectionSummary(data.reflection_summary);
      } catch (err) {
        console.error("Reflection summary error:", err);
        setReflectionSummaryError("Failed to load reflection summary");
      } finally {
        setLoadingReflectionSummary(false);
        setReflectionSummaryDone(true);
      }
    };
    fetchReflectionSummary();
  }, [userInfo, normalizedOpenEnded, buildUserProfilePayload]);

  // ---------------------------------------------------------------------------
  // Career Recommendations (B1: was http://localhost:8000)
  // ---------------------------------------------------------------------------
  useEffect(() => {
    const fetchCareerRecommendations = async () => {
      if (careerRecommendationsFetched.current || !userInfo?.fullName || barChartData.length === 0 || !reflectionSummaryDone) return;
      careerRecommendationsFetched.current = true;
      setLoadingCareerRecommendations(true);
      setCareerRecommendationsError(null);

      const categoryScoresPayload = {};
      barChartData.forEach(item => { categoryScoresPayload[item.label] = item.value || 0; });

      const payload = {
        user_profile:        buildUserProfilePayload(userInfo),
        category_scores:     categoryScoresPayload,
        reflection_summary:  reflectionSummary || "",
        strong_categories:   barChartData.filter(i => i.value >= 65).map(i => i.label),
        weak_categories:     barChartData.filter(i => i.value < 50).map(i => i.label),
      };
      const startTime = performance.now();
      try {
        const data = await post('/generate_career_recommendations', payload);
        const endTime = performance.now();
        console.log(`✅ [Career Recommendations] Finished in ${(endTime - startTime).toFixed(2)} ms`);
        setCareerRecommendations(data);
      } catch (err) {
        console.error("Career recommendations error:", err);
        setCareerRecommendationsError("Failed to load career recommendations");
      } finally {
        setLoadingCareerRecommendations(false);
      }
    };
    fetchCareerRecommendations();
  }, [userInfo, barChartData, reflectionSummaryDone, reflectionSummary, buildUserProfilePayload]);

  // ---------------------------------------------------------------------------
  // Download report
  // ---------------------------------------------------------------------------
  const handleRetakeAssessment = useCallback(() => navigate('/'), [navigate]);

  const handleDownloadReport = useCallback(() => {
    const reportHTML = generateReportHTML();
    const blob = new Blob([reportHTML], { type: 'text/html' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = 'Skill_Assessment_Report.html';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [percentage, strongestSkill, skillsData, percentileText, percentileNumber, salaryRangeINR, salaryRangeUSD, userInfo,
      totalMCQs, getPerformanceLevel, getMarketPercentile, growthProjection, actionPlan, growthSources,
      momentumToolkit, growthOpportunities, reflectionSummary, careerRecommendations]);

  const generateReportHTML = useCallback(() => {
    const currentDate = new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
    const safePeerBenchmark = peerBenchmark?.peer_benchmark || {
      percentile: "Top 70% among peers",
      narrative:  "Your skills are competitive in your domain with strengths in key areas.",
      in_demand_traits: [
        "Technical proficiency matches industry requirements",
        "Leadership skills align with management expectations",
        "Strategic thinking could be improved for senior roles",
      ],
    };
    console.log(safePeerBenchmark);
    const marketPercentile = getMarketPercentile(percentage);

    return `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Skill Assessment Report</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; color: #333; }
        .report-container { max-width: 800px; margin: 0 auto; background: white; border-radius: 15px; box-shadow: 0 20px 40px rgba(0,0,0,0.1); overflow: hidden; }
        .report-header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; }
        .report-header h1 { font-size: 28px; margin-bottom: 10px; display: flex; align-items: center; justify-content: center; gap: 10px; }
        .report-header .subtitle { font-size: 16px; opacity: 0.9; margin-bottom: 5px; }
        .report-header .date { font-size: 14px; opacity: 0.8; }
        .report-content { padding: 30px; }
        .section { margin-bottom: 30px; }
        .section-header { display: flex; align-items: center; gap: 10px; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 2px solid #e9ecef; }
        .section-header h2 { color: #667eea; font-size: 20px; font-weight: 600; }
        .overview-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
        .overview-item { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #f0f0f0; }
        .overview-item:last-child { border-bottom: none; }
        .overview-label { font-weight: 500; color: #666; }
        .overview-value { font-weight: 600; color: #333; }
        .performance-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 20px; }
        .performance-card { background: linear-gradient(135deg, #ff6b9d, #ff8e8e); color: white; padding: 25px; border-radius: 15px; text-align: center; }
        .performance-card.percentile { background: linear-gradient(135deg, #4ecdc4, #44a08d); }
        .performance-card.salary { background: linear-gradient(135deg, #f093fb, #f5576c); }
        .performance-card h3 { font-size: 14px; margin-bottom: 10px; opacity: 0.9; font-weight: 500; }
        .performance-card .value { font-size: 24px; font-weight: 700; margin-bottom: 5px; }
        .performance-card .label { font-size: 12px; opacity: 0.8; }
        .skills-list { display: flex; flex-direction: column; gap: 15px; }
        .skill-item-1 { display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid #e9ecef; }
        .skill-item-1:last-child { border-bottom: none; }
        .skill-name { font-weight: 500; color: #333; }
        .skill-percentage { font-weight: 600; color: #667eea; font-size: 16px; }
        .insights-section { background: #f8f9fa; padding: 20px; border-radius: 10px; margin-top: 20px; }
        .insight-card { background: white; padding: 15px; border-radius: 8px; margin-bottom: 15px; border-left: 4px solid #667eea; }
        .insight-card:last-child { margin-bottom: 0; }
        .insight-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
        .insight-header h4 { font-size: 16px; font-weight: 600; color: #333; }
        .insight-text { font-size: 14px; color: #666; line-height: 1.5; }
        .growth-metrics { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 15px; }
        .growth-metric { text-align: center; padding: 10px; background: #f8f9fa; border-radius: 8px; }
        .growth-metric .metric-label { display: block; font-size: 12px; color: #666; margin-bottom: 5px; }
        .growth-metric .metric-value { display: block; font-size: 18px; font-weight: 600; color: #667eea; }
        @media print { body { background: white; padding: 0; } .report-container { box-shadow: none; border-radius: 0; } }
        @media screen and (max-width: 768px) { .overview-grid { grid-template-columns: 1fr; } .performance-cards { display: flex; flex-direction: column; gap: 15px; } }
    </style>
</head>
<body>
    <div class="report-container">
        <div class="report-header">
            <h1>🎯 Skill Assessment Report</h1>
            <div class="subtitle">Comprehensive Analysis for ${userInfo?.fullName || 'Candidate'}</div>
            <div class="date">${currentDate}</div>
        </div>
        <div class="report-content">
            <div class="section">
                <div class="section-header"><span>📋</span><h2>Assessment Overview</h2></div>
                <div class="overview-grid">
                    <div>
                        <div class="overview-item"><span class="overview-label">Name:</span><span class="overview-value">${userInfo?.fullName || 'N/A'}</span></div>
                        <div class="overview-item"><span class="overview-label">Education:</span><span class="overview-value">${toLabel(EDUCATION_LABELS, userInfo?.educationLevel) || 'N/A'}</span></div>
                        <div class="overview-item"><span class="overview-label">Experience:</span><span class="overview-value">${toLabel(EXPERIENCE_LABELS, userInfo?.workExperience) || 'N/A'}</span></div>
                        <div class="overview-item"><span class="overview-label">Domain:</span><span class="overview-value">${toLabel(DOMAIN_LABELS, userInfo?.professionalDomain) || 'N/A'}</span></div>
                        <div class="overview-item"><span class="overview-label">Career Goals:</span><span class="overview-value">${toLabel(CAREER_GOAL_LABELS, userInfo?.careerGoals) || 'N/A'}</span></div>
                    </div>
                    <div>
                        <div class="overview-item"><span class="overview-label">Hobbies:</span><span class="overview-value">${userInfo?.hobbies || 'N/A'}</span></div>
                        <div class="overview-item"><span class="overview-label">Language:</span><span class="overview-value">${userInfo?.preferredLanguage || 'N/A'}</span></div>
                        <div class="overview-item"><span class="overview-label">Date:</span><span class="overview-value">${currentDate}</span></div>
                        <div class="overview-item"><span class="overview-label">Questions:</span><span class="overview-value">${totalMCQs} MCQ + 3 Open ended</span></div>
                    </div>
                </div>
            </div>
            <div class="section">
                <div class="section-header"><span>🏆</span><h2>Overall Performance</h2></div>
                <div class="performance-cards">
                    <div class="performance-card"><h3>Overall Score</h3><div class="value">${percentage.toFixed(2)}%</div><div class="label">${getPerformanceLevel(percentage)}</div></div>
                    <div class="performance-card percentile"><h3>Market Percentile</h3><div class="value">${marketPercentile}</div><div class="label">${getPerformanceLevel(percentage)}</div></div>
                    <div class="performance-card salary"><h3>Salary Range</h3><div class="value">${salaryRangeUSD} / ${salaryRangeINR}</div><div class="label">US / India Market Range</div></div>
                </div>
            </div>
            <div class="section">
                <div class="section-header"><span>🎯</span><h2>Skills Analysis</h2></div>
                <div class="skills-list">
                    ${skillsData.map(skill => `<div class="skill-item-1"><span class="skill-name">${skill.skill}</span><span class="skill-percentage">${skill.percentage}%</span></div>`).join('')}
                </div>
            </div>
            <div class="section">
                <div class="section-header"><span>📊</span><h2>Peer Benchmark</h2></div>
                <div class="insights-section">
                    ${peerBenchmark?.peer_benchmark ? `
                        <div class="insight-card"><div class="insight-header"><span>📈</span><h4>Benchmark Summary</h4></div><div class="insight-text"><p><strong>Percentile:</strong> ${peerBenchmark.peer_benchmark.percentile || 'Not available'}</p><p><strong>Narrative:</strong> ${peerBenchmark.peer_benchmark.narrative || 'Analysis not available'}</p></div></div>
                        ${peerBenchmark.peer_benchmark.in_demand_traits?.length > 0 ? `<div class="insight-card"><div class="insight-header"><span>🧠</span><h4>In-Demand Traits</h4></div><div class="insight-text"><ul>${peerBenchmark.peer_benchmark.in_demand_traits.map(t => `<li>✅ ${t}</li>`).join('')}</ul></div></div>` : ''}
                    ` : '<p>Peer benchmark data not available.</p>'}
                </div>
            </div>
            <div class="section">
                <div class="section-header"><span>🎯</span><h2>90-Day Personalized Roadmap</h2></div>
                ${actionPlan && actionPlan.length > 0 ? actionPlan.map((phase, i) => {
                    const dayMilestone  = (i + 1) * 30;
                    const startingWeek  = i * 4 + 1;
                    return `<div class="insight-card"><div class="insight-header"><span>📌</span><h4>PHASE ${i + 1} (${dayMilestone - 29}–${dayMilestone} Days) – ${phase.title || 'Phase ' + (i + 1)}</h4></div><div class="insight-text"><strong>Focus Areas:</strong> ${phase.focus || 'Not specified'}<br/><br/><strong>Weekly Actions:</strong><ul>${Array.isArray(phase.weekly_actions) ? phase.weekly_actions.map((a, j) => `<li>📅 Week ${startingWeek + j}: ${a}</li>`).join('') : '<li>No actions specified.</li>'}</ul><strong>Milestone by Day ${dayMilestone}:</strong> ${phase.milestone || 'Not specified'}</div></div>`;
                }).join('') : '<p>Action plan not available.</p>'}
            </div>
            <div class="section">
                <div class="section-header"><span>📚</span><h2>Recommended Resources</h2></div>
                <div class="insights-section">
                    ${growthSources && growthSources.length > 0 ? growthSources.map(s => `<div class="insight-card"><div class="insight-header"><span>📘</span><h4>${s.category || 'Resource'}</h4></div><div class="insight-text"><strong>${s.title || 'Title'}</strong><br/>${s.why || ''}<br/>⏱️ <em>${s.duration || ''}</em><br/>✅ <em>${s.outcome || ''}</em><br/>${s.link ? `🔗 <a href="${s.link}" target="_blank">${s.link}</a>` : ''}</div></div>`).join('') : '<p>Growth resources not available.</p>'}
                </div>
            </div>
            <div class="section">
                <div class="section-header"><span>🪞</span><h2>Reflection Summary</h2></div>
                <div class="insights-section">
                    ${reflectionSummary ? `<div class="insight-card"><div class="insight-text"><p>${reflectionSummary}</p></div></div>` : '<p>Reflection summary not available.</p>'}
                </div>
            </div>
            <div class="section">
                <div class="section-header"><span>🚀</span><h2>Recommended Career Path</h2></div>
                <div class="insights-section">
                    ${careerRecommendations && (careerRecommendations.streams?.length > 0 || careerRecommendations.careers?.length > 0) ? `
                        ${careerRecommendations.streams?.length > 0 ? `<h4 style="margin-bottom:10px;color:#667eea;">Academic Streams</h4>${careerRecommendations.streams.map(s => `<div class="insight-card"><div class="insight-header"><span>🎓</span><h4>${s.name}</h4></div><div class="insight-text"><p>${s.explanation}</p></div></div>`).join('')}` : ''}
                        ${careerRecommendations.careers?.length > 0 ? `<h4 style="margin:20px 0 10px;color:#667eea;">Career Domains</h4>${careerRecommendations.careers.map(c => `<div class="insight-card"><div class="insight-header"><span>💼</span><h4>${c.name}</h4></div><div class="insight-text"><p>${c.explanation}</p></div></div>`).join('')}` : ''}
                    ` : '<p>Career recommendations not available.</p>'}
                </div>
            </div>
        </div>
    </div>
</body>
</html>`;
  }, [percentage, strongestSkill, skillsData, percentileText, percentileNumber, salaryRangeINR, salaryRangeUSD,
      userInfo, totalMCQs, getPerformanceLevel, getMarketPercentile, growthProjection, peerBenchmark,
      actionPlan, growthSources, growthOpportunities, reflectionSummary, careerRecommendations]);

  // ---------------------------------------------------------------------------
  // Render — identical to original
  // ---------------------------------------------------------------------------
  return (
    <div className="results-container">
      <div className="results-header">
        <div className="trophy-icon">🏆</div>
        <h1>Congratulations, {userInfo.fullName}</h1>
        <p>Your skill assessment is complete. Here's your personalized performance analysis with market insights.</p>
      </div>

      <div className="summary-cards">
        <div className="summary-card">
          <div className="info-icon" style={{ fontSize: '26px' }}>
            <IoInformationCircleOutline />
            <div className="tooltip">
              This score combines your MCQ and open-ended results to show current readiness. With effort, this will grow quickly.
            </div>
          </div>
          <div className="score-display" style={{ position: 'relative' }}>
            <span className="score-number">{percentage.toFixed(2)}%</span>
            <span className="score-label">Overall Score</span>
            <span className="score-status">{getPerformanceLevel(percentage)}</span>
          </div>
        </div>

        <div className="summary-card">
          <div className="percentile-display">
            <div className="percentile-icon">👥</div>
            <span className="percentile-label">{percentileText}</span>
            <span className="percentile-desc">Market Percentile</span>
            <div className="percentile-text">{barMessage}</div>
            <div className="percentile-bar-container">
              <div className="percentile-bar-fill" style={{ width: `${percentileNumber}%` }}>
                <div className="you-are-here-label">You are here</div>
              </div>
              <div className="percentile-bar-bg"></div>
            </div>
          </div>
        </div>

        <div className="summary-card">
          <div className="tooltip-wrapper">
            <div className="tooltip-icon">
              <IoInformationCircleOutline />
              <span className="tooltip-text">You're great at breaking down complex problems and making thoughtful decisions.</span>
            </div>
          </div>
          <div className="skill-display">
            <div className="skill-icon">{strongestSkillIcon}</div>
            <span className="skill-label">{strongestSkill}</span>
            <span className="skill-desc">Strongest Skill</span>
          </div>
        </div>
      </div>

      <div className="analysis-grid">
        <div className="analysis-card">
          <div className="card-header">
            <span className="card-icon">📊</span>
            <h3>Your Performance vs Market Standards</h3>
            <p>Comparing your skills with advanced level professionals</p>
          </div>
          <div className="bar-chart-container">
            <div className="bar-chart">
              {barChartData.map((item, index) => (
                <div key={index} className="bar-chart-item">
                  <div className="bar-chart-bar">
                    <div className="tooltip-wrapper-2">
                      <div className="bar-chart-fill-user" style={{ height: `${item.value}%` }}></div>
                      <div className="tooltip-text-2">{tooltips[item.label]?.user_tooltip || "Loading..."}</div>
                    </div>
                    <div className="tooltip-wrapper-2">
                      <div className="bar-chart-fill-market" style={{ height: `${item.market || 60}%` }}></div>
                      <div className="tooltip-text-2">{tooltips[item.label]?.benchmark_tooltip || "Loading..."}</div>
                    </div>
                  </div>
                  <div className="bar-chart-label">{item.label.split(' ')[0]}</div>
                </div>
              ))}
            </div>
            <div className="chart-legend">
              <div className="legend-item"><div className="legend-color user-color"></div><span>Your Performance</span></div>
              <div className="legend-item"><div className="legend-color market-color"></div><span>Market Average</span></div>
            </div>
          </div>
        </div>

        <div className="analysis-card">
          <div className="card-header">
            <span className="card-icon">⚠️</span>
            <h3>Skills Distribution</h3>
            <p>Visual breakdown of your competencies</p>
          </div>
          <div className="skills-list-2">
            {skillsData.map((skill, index) => (
              <div key={index} className="skill-item-2">
                <div className="skill-info-2" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span className="skill-icon-2" style={{ fontSize: '20px' }}>{skillIcons[skill.skill] || '🎯'}</span>
                  <span className="skill-name-2">{skill.skill}</span>
                  <span className="percentage-text-2">{skill.percentage}%</span>
                </div>
                <div className="percentage-bar-2">
                  <div className="percentage-fill-2" style={{ width: `${skill.percentage}%` }}></div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="analysis-card">
          <div className="card-header"><span className="card-icon">🧠</span><h3>Assessment Summary</h3><p>A holistic view of personality, strengths, and growth areas</p></div>
          {assessmentSummary ? (<p className="summary-text">{assessmentSummary}</p>)
            : loadingAssessmentSummary ? (<div className="loading-spinner">Generating your assessment summary...</div>)
            : assessmentSummaryError ? (<p className="section-error-text">{assessmentSummaryError}</p>)
            : (<div className="loading-spinner">Preparing your assessment summary...</div>)}
        </div>

        <div className="analysis-card">
          <div className="card-header"><span className="card-icon">💭</span><h3>Reflection Summary</h3><p>Themes, interests, and values drawn from your open-ended answers</p></div>
          {reflectionSummary ? (<p className="summary-text">{reflectionSummary}</p>)
            : loadingReflectionSummary ? (<div className="loading-spinner">Synthesizing your reflections...</div>)
            : reflectionSummaryError ? (<p className="section-error-text">{reflectionSummaryError}</p>)
            : (<div className="loading-spinner">Preparing your reflection summary...</div>)}
        </div>

        <div className="analysis-card">
          <div className="card-header"><span className="card-icon">🎯</span><h3>Recommended Career Paths</h3><p>Academic streams and career domains matched to your profile</p></div>
          {careerRecommendations ? (
            <>
              {careerRecommendations.streams?.length > 0 && (
                <div className="recommendation-section">
                  <h4 className="recommendation-section-title">Recommended Academic Streams</h4>
                  <div className="recommendation-list">
                    {careerRecommendations.streams.map((stream, index) => (
                      <div key={index} className="recommendation-item">
                        <div className="recommendation-name">{stream.name}</div>
                        <div className="recommendation-explanation">{stream.explanation}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {careerRecommendations.careers?.length > 0 && (
                <div className="recommendation-section">
                  <h4 className="recommendation-section-title">Recommended Career Domains</h4>
                  <div className="recommendation-list">
                    {careerRecommendations.careers.map((career, index) => (
                      <div key={index} className="recommendation-item">
                        <div className="recommendation-name">{career.name}</div>
                        <div className="recommendation-explanation">{career.explanation}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : loadingCareerRecommendations ? (<div className="loading-spinner">Matching careers to your profile...</div>)
            : careerRecommendationsError ? (<p className="section-error-text">{careerRecommendationsError}</p>)
            : (<div className="loading-spinner">Preparing your career recommendations...</div>)}
        </div>

        {growthProjection && (
          <div className="analysis-card">
            <div className="card-header"><span className="card-icon">📈</span><h3>Growth Projection</h3><p>Estimated skill improvement over time</p></div>
            <div className="skills-list-2">
              <div className="growth-chart">
                <div className="chart-placeholder">
                  <div className="growth-line"></div>
                  <div className="growth-points">
                    <div className="point start-point"></div>
                    <div className="point-wrapper">
                      <span className="growth-label">+{Math.round(growthProjection.growth_projection["3_months"] - growthProjection.growth_projection.current_score)}</span>
                      <div className="point mid-point"></div>
                    </div>
                    <div className="point-wrapper">
                      <span className="growth-label">+{Math.round(growthProjection.growth_projection["6_months"] - growthProjection.growth_projection.current_score)}</span>
                      <div className="point mid-point"></div>
                    </div>
                    <div className="point-wrapper">
                      <span className="growth-label">+{Math.round(growthProjection.growth_projection["12_months"] - growthProjection.growth_projection.current_score)}</span>
                      <div className="point end-point"></div>
                    </div>
                  </div>
                </div>
                <div className="growth-timeline">
                  <span>Current</span><span>3 Months</span><span>6 Months</span><span>12 Months</span>
                </div>
              </div>
              <div className="growth-insight" style={{ marginTop: "1rem" }}>
                <span className="insight-icon">💡</span>
                <p>With focused development, you could improve by up to{' '}
                  <strong>{Math.round(growthProjection.growth_projection["12_months"] - growthProjection.growth_projection.current_score)} points</strong>{' '}
                  in the next year!
                </p>
                <p><strong>Peer Percentile:</strong> <strong>{barMessage}</strong></p>
              </div>
              <div className="action-steps" style={{ marginTop: "1rem" }}>
                <h4>🎯 Recommended Action Steps</h4>
                <ul style={{ paddingLeft: "1rem", marginTop: "0.5rem" }}>
                  {growthProjection.action_steps.map((step, index) => (
                    <li key={index} style={{ marginBottom: "0.5rem" }}>✅ {step}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}

        {marketAnalysis && (
          <div className="analysis-card">
            <div className="card-header"><span className="card-icon">📊</span><h3>Market Position Analysis</h3><p>Where you stand in the job market</p></div>
            <div className="market-position">
              <div className="position-badge">
                <span className="position-icon">📝</span>
                <div className="position-info">
                  <span className="position-title">{marketAnalysis.tier?.label || 'Position Pending'}</span>
                  <span className="position-desc">{marketAnalysis.tier?.bullets || 'Analysis in progress'}</span>
                </div>
              </div>
              <div className="market-metrics">
                <div className="metric">
                  <span className="metric-label">Industry Readiness</span>
                  <div className="metric-bar">
                    <div className="metric-fill" style={{ width: `${marketAnalysis.readiness_score || 0}%` }}></div>
                  </div>
                  <span className="metric-value">{marketAnalysis.readiness_score || 0}%</span>
                </div>
                <div className="salary-range">
                  <div className="salary-item">
                    <span className="salary-label">{marketAnalysis.experience?.label || 'Experience Level'}</span>
                    <span className="salary-desc">{marketAnalysis.experience?.bullets || 'Calculating...'}</span>
                  </div>
                  <div className="salary-item">
                    <span className="salary-label">{marketAnalysis.salary?.label || 'Salary Range'}</span>
                    <span className="salary-desc">{marketAnalysis.salary?.bullets || 'Estimating...'}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {loadingMarketAnalysis && (
          <div className="analysis-card">
            <div className="card-header"><span className="card-icon">📊</span><h3>Market Position Analysis</h3><p>Analyzing your market position...</p></div>
            <div className="loading-spinner">Loading market analysis...</div>
          </div>
        )}
      </div>

      <div className="action-buttons">
        <button className="retake-btn" onClick={handleRetakeAssessment}>🔄 Retake Assessment</button>
        {(() => {
          const pending =
            (loadingReflectionSummary || (!reflectionSummary && !reflectionSummaryError)) ||
            (loadingCareerRecommendations || (!careerRecommendations && !careerRecommendationsError));
          return (
            <button
              className={`download-btn ${pending ? 'disabled' : ''}`}
              onClick={handleDownloadReport}
              disabled={pending}
            >
              {pending ? '↓ Preparing Your Full Report...' : '↓ Download Complete Report'}
            </button>
          );
        })()}
      </div>
    </div>
  );
}

export default Results;
