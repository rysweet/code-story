import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import React from 'react';
import { MantineProvider } from '@mantine/core';
import QueryInput from '../QueryInput';

// Create test wrapper with MantineProvider
const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <MantineProvider>
    {children}
  </MantineProvider>
);

describe('QueryInput', () => {
  it('renders the component correctly', () => {
    render(
      <TestWrapper>
        <QueryInput onSubmit={() => {}} />
      </TestWrapper>
    );

    expect(screen.getByText('Ask about your codebase')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Ask a question about your code...')).toBeInTheDocument();
    expect(screen.getByText('Ask Question')).toBeInTheDocument();
    expect(screen.getByText('Try an example...')).toBeInTheDocument();
  });

  it('submits the query when form is submitted', async () => {
    const mockSubmit = vi.fn();
    const user = userEvent.setup();

    render(
      <TestWrapper>
        <QueryInput onSubmit={mockSubmit} />
      </TestWrapper>
    );

    const textarea = screen.getByPlaceholderText('Ask a question about your code...');
    await user.type(textarea, 'What are the main classes?');

    const submitButton = screen.getByText('Ask Question');
    await user.click(submitButton);

    expect(mockSubmit).toHaveBeenCalledWith('What are the main classes?');
  });

  it('does not submit when query is empty', async () => {
    const mockSubmit = vi.fn();
    const user = userEvent.setup();

    render(
      <TestWrapper>
        <QueryInput onSubmit={mockSubmit} />
      </TestWrapper>
    );

    const submitButton = screen.getByText('Ask Question');
    await user.click(submitButton);

    expect(mockSubmit).not.toHaveBeenCalled();
  });

  it('clears the input when clear button is clicked', async () => {
    const user = userEvent.setup();

    render(
      <TestWrapper>
        <QueryInput onSubmit={() => {}} />
      </TestWrapper>
    );

    const textarea = screen.getByPlaceholderText('Ask a question about your code...');
    await user.type(textarea, 'What are the main classes?');

    expect(textarea).toHaveValue('What are the main classes?');

    const clearButton = screen.getByLabelText('Clear input');
    await user.click(clearButton);

    expect(textarea).toHaveValue('');
  });

  it('fills the textarea with selected example', async () => {
    const user = userEvent.setup();

    render(
      <TestWrapper>
        <QueryInput onSubmit={() => {}} />
      </TestWrapper>
    );

    const textarea = screen.getByPlaceholderText('Ask a question about your code...');
    const selectExample = screen.getByText('Try an example...');

    await user.click(selectExample);

    // This would normally show a dropdown, but in test environment we need to simulate selection
    // Since we're not using MSW to mock API, this gets tricky
    // Get the first example and click it
    const exampleOption = await screen.findByRole('option', { name: /What are the main classes in the auth module\?/i });
    await user.click(exampleOption);

    expect(textarea).toHaveValue('What are the main classes in the auth module?');
  });

  it('calls save query handler when save button is clicked', async () => {
    const mockSave = vi.fn();
    const user = userEvent.setup();

    render(
      <TestWrapper>
        <QueryInput onSubmit={() => {}} onSaveQuery={mockSave} />
      </TestWrapper>
    );

    const textarea = screen.getByPlaceholderText('Ask a question about your code...');
    await user.type(textarea, 'What are the main classes?');

    const saveButton = screen.getByLabelText('Save query for later');
    await user.click(saveButton);

    expect(mockSave).toHaveBeenCalledWith('What are the main classes?');
  });

  it('calls clear history handler when clear history button is clicked', async () => {
    const mockClearHistory = vi.fn();
    const user = userEvent.setup();

    render(
      <TestWrapper>
        <QueryInput onSubmit={() => {}} onClearHistory={mockClearHistory} />
      </TestWrapper>
    );

    const clearHistoryButton = screen.getByLabelText('Clear history');
    await user.click(clearHistoryButton);

    expect(mockClearHistory).toHaveBeenCalled();
  });

  it('shows loading state when isLoading is true', () => {
    render(
      <TestWrapper>
        <QueryInput onSubmit={() => {}} isLoading />
      </TestWrapper>
    );

    const submitButton = screen.getByText('Ask Question');
    expect(submitButton).toHaveAttribute('data-loading');
  });
});