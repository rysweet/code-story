import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import React from 'react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import AskPage from '../AskPage';
import { QueryInput, AnswerDisplay } from '../../components/ask';
import { baseApi } from '../../store/api/baseApi';
import uiReducer from '../../store/slices/uiSlice';

// Mock the ask components
vi.mock('../../components/ask', () => ({
  QueryInput: vi.fn(({ onSubmit }) => (
    <div data-testid="query-input">
      <input 
        data-testid="query-textarea" 
        onChange={(e) => e.target.value} 
      />
      <button 
        data-testid="submit-button" 
        onClick={() => onSubmit('What are the main classes?')}
      >
        Ask Question
      </button>
    </div>
  )),
  AnswerDisplay: vi.fn(({ question, answer }) => (
    <div data-testid="answer-display">
      <div data-testid="question">{question}</div>
      <div data-testid="answer">{answer}</div>
    </div>
  )),
}));

// Mock RTK Query hooks
vi.mock('../../store', () => ({
  useAskQuestionMutation: vi.fn(() => [
    vi.fn().mockImplementation((query) => 
      Promise.resolve({ answer: `Answer to: ${query.question}` })
    ),
    { isLoading: false, error: null },
  ]),
}));

// Create a test store
const createTestStore = () => {
  return configureStore({
    reducer: {
      ui: uiReducer,
      [baseApi.reducerPath]: baseApi.reducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().concat(baseApi.middleware),
  });
};

// Test wrapper component with providers
const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const store = createTestStore();
  return (
    <Provider store={store}>
      {children}
    </Provider>
  );
};

describe('AskPage', () => {
  let store;
  
  beforeEach(() => {
    // Create a fresh store for each test
    store = createTestStore();
    
    // Reset mocks
    vi.clearAllMocks();
    
    // Mock localStorage
    Storage.prototype.getItem = vi.fn().mockReturnValue(null);
    Storage.prototype.setItem = vi.fn();
    Storage.prototype.removeItem = vi.fn();
  });
  
  it('renders the component correctly', () => {
    render(
      <TestWrapper>
        <AskPage />
      </TestWrapper>
    );

    expect(screen.getByText('Ask Questions About Your Code')).toBeInTheDocument();
    expect(screen.getByTestId('query-input')).toBeInTheDocument();
  });

  it('handles question submission', async () => {
    render(
      <TestWrapper>
        <AskPage />
      </TestWrapper>
    );

    // Simulate query submission
    const submitButton = screen.getByTestId('submit-button');
    await userEvent.click(submitButton);

    // Should show the answer display with the question and answer
    await waitFor(() => {
      expect(screen.getByTestId('answer-display')).toBeInTheDocument();
      expect(screen.getByTestId('question')).toHaveTextContent('What are the main classes?');
      expect(screen.getByTestId('answer')).toHaveTextContent('Answer to: What are the main classes?');
    });

    // Should save to localStorage
    expect(localStorage.setItem).toHaveBeenCalled();
  });

  it('loads query history from localStorage on mount', async () => {
    // Mock localStorage to return some history
    const mockHistory = [
      {
        id: 'query_1',
        question: 'Previous question',
        answer: 'Previous answer',
        timestamp: '2025-05-11T12:00:00Z',
      },
    ];

    Storage.prototype.getItem = vi.fn().mockImplementation((key) => {
      if (key === 'askQueryHistory') {
        return JSON.stringify(mockHistory);
      }
      return null;
    });

    render(
      <TestWrapper>
        <AskPage />
      </TestWrapper>
    );

    // Should load history from localStorage
    expect(localStorage.getItem).toHaveBeenCalledWith('askQueryHistory');

    // Initially, history is not shown
    expect(screen.queryByText('Previous question')).not.toBeInTheDocument();

    // Show history by clicking the button
    const showHistoryButton = screen.getByText('Show History');
    await userEvent.click(showHistoryButton);

    // Should now show the query from history
    expect(screen.getByText('Previous question')).toBeInTheDocument();
  });

  it('saves query without submitting', async () => {
    render(
      <TestWrapper>
        <AskPage />
      </TestWrapper>
    );

    // Get the saveQuery handler that was passed to QueryInput
    const queryInput = QueryInput as unknown as ReturnType<typeof vi.fn>;
    const saveQueryHandler = queryInput.mock.calls[0][0].onSaveQuery;

    // Call the handler directly
    saveQueryHandler('Saved query');

    // Should save to localStorage
    expect(localStorage.setItem).toHaveBeenCalledWith(
      'savedQueries',
      JSON.stringify(['Saved query'])
    );
  });

  it('clears query history', async () => {
    // Mock localStorage to return some history
    const mockHistory = [
      {
        id: 'query_1',
        question: 'Previous question',
        answer: 'Previous answer',
        timestamp: '2025-05-11T12:00:00Z',
      },
    ];

    Storage.prototype.getItem = vi.fn().mockImplementation((key) => {
      if (key === 'askQueryHistory') {
        return JSON.stringify(mockHistory);
      }
      return null;
    });

    render(
      <TestWrapper>
        <AskPage />
      </TestWrapper>
    );

    // Get the clearHistory handler that was passed to QueryInput
    const queryInput = QueryInput as unknown as ReturnType<typeof vi.fn>;
    const clearHistoryHandler = queryInput.mock.calls[0][0].onClearHistory;

    // Call the handler directly
    clearHistoryHandler();

    // Should remove history from localStorage
    expect(localStorage.removeItem).toHaveBeenCalledWith('askQueryHistory');
  });
});