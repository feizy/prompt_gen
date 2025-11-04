import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { Provider } from 'react-redux';
import { useSelector } from 'react-redux';

import ErrorBoundary from './components/ErrorBoundary';
import CreateSessionModal from './components/CreateSessionModal';
import Dashboard from './pages/Dashboard';
import ActiveSession from './pages/ActiveSession';
import History from './pages/History';
import { store } from './store';
import { RootState } from './store';

// Create a theme instance
const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
  },
});

function AppContent() {
  const createSessionModalOpen = useSelector((state: RootState) => state.ui.modals.createSession);

  return (
    <div className="App">
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/session/:sessionId" element={<ActiveSession />} />
        <Route path="/history" element={<History />} />
      </Routes>

      <CreateSessionModal
        open={createSessionModalOpen}
        onClose={() => store.dispatch({ type: 'ui/closeModal', payload: 'createSession' })}
      />
    </div>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <Provider store={store}>
        <ThemeProvider theme={theme}>
          <CssBaseline />
          <Router>
            <AppContent />
          </Router>
        </ThemeProvider>
      </Provider>
    </ErrorBoundary>
  );
}

export default App;