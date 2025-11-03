import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { Provider } from 'react-redux';

import Dashboard from '../pages/Dashboard';
import { store } from '../store';

// Mock Redux store
jest.mock('../store', () => ({
  store: {
    getState: () => ({
      ui: {
        theme: 'light',
        sidebarOpen: true,
        notifications: [],
        loading: { sessions: false, messages: false, userInputs: false },
        modals: { createSession: false, sessionSettings: false }
      }
    }),
    dispatch: jest.fn()
  }
}));

// Mock navigation
const MockNavigate = ({ children }: { children: React.ReactNode }) => {
  return <div>{children}</div>;
};

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => jest.fn(),
  BrowserRouter: ({ children }: { children: React.ReactNode }) => (
    <MockNavigate>{children}</MockNavigate>
  )
}));

const renderWithProviders = (ui: React.ReactElement) => {
  return render(
    <Provider store={store}>
      <BrowserRouter>
        {ui}
      </BrowserRouter>
    </Provider>
  );
};

describe('Dashboard Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders dashboard with title and description', () => {
    renderWithProviders(<Dashboard />);

    expect(screen.getByText('AI Agent Prompt Generator')).toBeInTheDocument();
    expect(
      screen.getByText('Create detailed LLM prompts through collaborative AI agents')
    ).toBeInTheDocument();
  });

  test('renders create session card', () => {
    renderWithProviders(<Dashboard />);

    expect(screen.getByText('Create New Session')).toBeInTheDocument();
    expect(
      screen.getByText('Start a new prompt generation session with our AI agents')
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /create session/i })).toBeInTheDocument();
  });

  test('renders view history card', () => {
    renderWithProviders(<Dashboard />);

    expect(screen.getByText('View History')).toBeInTheDocument();
    expect(
      screen.getByText('Browse and search previous prompt generation sessions')
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /view history/i })).toBeInTheDocument();
  });

  test('renders how it works section', () => {
    renderWithProviders(<Dashboard />);

    expect(screen.getByText('How It Works')).toBeInTheDocument();
    expect(screen.getByText('Our system uses three specialized AI agents working together:')).toBeInTheDocument();
    expect(screen.getByText(/Product Manager/)).toBeInTheDocument();
    expect(screen.getByText(/Technical Developer/)).toBeInTheDocument();
    expect(screen.getByText(/Team Lead/)).toBeInTheDocument();
  });

  test('handle create session button click', async () => {
    const mockDispatch = jest.fn();
    jest.mocked(store).dispatch = mockDispatch;

    renderWithProviders(<Dashboard />);

    const createButton = screen.getByRole('button', { name: /create session/i });
    fireEvent.click(createButton);

    await waitFor(() => {
      expect(mockDispatch).toHaveBeenCalled();
    });
  });

  test('renders responsive layout', () => {
    renderWithProviders(<Dashboard />);

    // Check that main container exists
    expect(screen.getByRole('main')).toBeInTheDocument();

    // Check that cards are rendered
    const cards = screen.getAllByRole('article');
    expect(cards.length).toBeGreaterThanOrEqual(2);
  });

  test('displays agent descriptions correctly', () => {
    renderWithProviders(<Dashboard />);

    // Check that each agent role is properly described
    expect(screen.getByText(/Analyzes your requirements and creates detailed product specifications/)).toBeInTheDocument();
    expect(screen.getByText(/Designs technical solutions and implementation approaches/)).toBeInTheDocument();
    expect(screen.getByText(/Reviews and approves the final prompt, ensuring quality and completeness/)).toBeInTheDocument();
  });

  test('has proper accessibility structure', () => {
    const { container } = renderWithProviders(<Dashboard />);

    // Check for proper heading hierarchy
    const mainHeading = screen.getByRole('heading', { level: 1 });
    expect(mainHeading).toBeInTheDocument();
    expect(mainHeading).toHaveTextContent('AI Agent Prompt Generator');

    // Check that buttons have accessible names
    const buttons = screen.getAllByRole('button');
    buttons.forEach(button => {
      expect(button).toHaveAccessibleName();
    });
  });
});