// src/App.js
// Place this file at: src/App.js

import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { GoogleOAuthProvider } from '@react-oauth/google';

import Home               from './pages/Home';
import Assessment         from './pages/Assessment';
import MCQCompletion      from './pages/MCQCompletion';
import OpenEndedQuestions from './pages/OpenEndedQuestions';
import Results            from './pages/Results';
import Login              from './pages/Login';
import Signup             from './pages/Signup';
import VerifyOtp          from './pages/VerifyOtp';

import Buddy               from './components/Buddy';
import Projects            from './components/Projects';
import CounsellorDashboard from './components/CounsellorDashboard';
import PrivacySettings     from './components/PrivacySettings';

import { getToken, getRole } from './api';

// Redirect to /login if there is no session token.
function RequireAuth({ children }) {
  return getToken() ? children : <Navigate to="/login" replace />;
}

// Redirect students away from counsellor pages.
function RequireStaff({ children }) {
  if (!getToken()) return <Navigate to="/login" replace />;
  return ['counsellor', 'admin'].includes(getRole())
    ? children
    : <Navigate to="/" replace />;
}

const GOOGLE_CLIENT_ID = process.env.REACT_APP_GOOGLE_CLIENT_ID || '';

function App() {
  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <BrowserRouter>
        <Routes>
          {/* Public */}
          <Route path="/login"      element={<Login />} />
          <Route path="/signup"     element={<Signup />} />
          <Route path="/verify-otp" element={<VerifyOtp />} />

          {/* Student */}
          <Route path="/" element={<RequireAuth><Home /></RequireAuth>} />
          <Route path="/assessment" element={<RequireAuth><Assessment /></RequireAuth>} />
          <Route path="/mcq-completion" element={<RequireAuth><MCQCompletion /></RequireAuth>} />
          <Route path="/open-ended-questions" element={<RequireAuth><OpenEndedQuestions /></RequireAuth>} />
          <Route path="/results" element={<RequireAuth><Results /></RequireAuth>} />
          <Route path="/buddy"   element={<RequireAuth><Buddy /></RequireAuth>} />
          <Route path="/projects" element={<RequireAuth><Projects /></RequireAuth>} />
          <Route path="/privacy"       element={<RequireAuth><PrivacySettings /></RequireAuth>} />
          <Route path="/privacy-setup" element={<RequireAuth><PrivacySettings gate /></RequireAuth>} />

          {/* Staff only */}
          <Route path="/counsellor" element={<RequireStaff><CounsellorDashboard /></RequireStaff>} />

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </GoogleOAuthProvider>
  );
}

export default App;
