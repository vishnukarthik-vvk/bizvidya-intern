import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import Home from './pages/Home';
import Assessment from './pages/Assessment';
import MCQCompletion from './pages/MCQCompletion';
import OpenEndedQuestions from './pages/OpenEndedQuestions';
import Results from './pages/Results';
import Login from './pages/Login';
import Signup from './pages/Signup';
import VerifyOtp from './pages/VerifyOtp';

function App() { 
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/verify-otp" element={<VerifyOtp />} />
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