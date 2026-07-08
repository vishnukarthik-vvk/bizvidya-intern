import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import Home from './pages/Home';
import Assessment from './pages/Assessment';
import MCQCompletion from './pages/MCQCompletion';
import OpenEndedQuestions from './pages/OpenEndedQuestions';
import Results from './pages/Results';

function App() { 
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/assessment" element={<Assessment />} />
        <Route path="/mcq-completion" element={<MCQCompletion />} />
        <Route path='/open-ended-questions' element={<OpenEndedQuestions/>}/>
        <Route path="/results" element={<Results/>}/>
      </Routes>
    </Router>
  );
}
export default App;