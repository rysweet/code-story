import React, { useState, useEffect } from 'react';
import { Box, Title, Stack, Alert, Button, Group } from '@mantine/core';
import { useDispatch } from 'react-redux';
import { setActivePage } from '../store/slices/uiSlice';
import { useAskQuestionMutation } from '../store';
import { QueryInput, AnswerDisplay } from '../components/ask';
import { IconBrain, IconHistory } from '@tabler/icons-react';

interface QueryHistory {
  id: string;
  question: string;
  answer: string;
  timestamp: string;
}

/**
 * AskPage component for natural language queries about the codebase
 */
const AskPage: React.FC = () => {
  const dispatch = useDispatch();
  const [askQuestion, { isLoading, error }] = useAskQuestionMutation();
  
  const [currentQuestion, setCurrentQuestion] = useState<string>('');
  const [currentAnswer, setCurrentAnswer] = useState<string | null>(null);
  const [queryHistory, setQueryHistory] = useState<QueryHistory[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  
  // Set active page when component mounts
  useEffect(() => {
    dispatch(setActivePage('ask'));
    
    // Load query history from localStorage
    const savedHistory = localStorage.getItem('askQueryHistory');
    if (savedHistory) {
      try {
        setQueryHistory(JSON.parse(savedHistory));
      } catch (e) {
        console.error('Failed to parse query history:', e);
      }
    }
  }, [dispatch]);
  
  // Handle question submission
  const handleSubmitQuestion = async (question: string) => {
    setCurrentQuestion(question);
    setCurrentAnswer(null);
    
    try {
      const response = await askQuestion({ question }).unwrap();
      setCurrentAnswer(response.answer);
      
      // Save to history
      const newHistoryItem: QueryHistory = {
        id: `query_${Date.now()}`,
        question,
        answer: response.answer,
        timestamp: new Date().toISOString(),
      };
      
      const updatedHistory = [newHistoryItem, ...queryHistory].slice(0, 50); // Keep last 50 items
      setQueryHistory(updatedHistory);
      
      // Save to localStorage
      localStorage.setItem('askQueryHistory', JSON.stringify(updatedHistory));
    } catch (e) {
      console.error('Failed to ask question:', e);
    }
  };
  
  // Save query to history without submitting
  const handleSaveQuery = (query: string) => {
    if (!query.trim()) return;
    
    // Add to saved queries
    const savedQueries = JSON.parse(localStorage.getItem('savedQueries') || '[]');
    const updatedQueries = [...new Set([query, ...savedQueries])].slice(0, 20);
    localStorage.setItem('savedQueries', JSON.stringify(updatedQueries));
  };
  
  // Clear query history
  const handleClearHistory = () => {
    setQueryHistory([]);
    localStorage.removeItem('askQueryHistory');
  };
  
  // Load a history item
  const handleLoadHistoryItem = (historyItem: QueryHistory) => {
    setCurrentQuestion(historyItem.question);
    setCurrentAnswer(historyItem.answer);
  };
  
  return (
    <Box p="md">
      <Stack spacing="md">
        <Title order={2}>Ask Questions About Your Code</Title>
        
        <QueryInput 
          onSubmit={handleSubmitQuestion}
          isLoading={isLoading}
          onSaveQuery={handleSaveQuery}
          onClearHistory={handleClearHistory}
        />
        
        {currentQuestion && (
          <AnswerDisplay
            question={currentQuestion}
            answer={currentAnswer}
            isLoading={isLoading}
            error={error ? 'Failed to process your question. Please try again.' : null}
            timestamp={new Date().toISOString()}
          />
        )}
        
        {queryHistory.length > 0 && (
          <Alert 
            icon={<IconHistory size={16} />} 
            color="gray" 
            title={
              <Group position="apart">
                <span>Query History ({queryHistory.length})</span>
                <Button 
                  variant="subtle" 
                  size="xs" 
                  onClick={() => setShowHistory(!showHistory)}
                >
                  {showHistory ? 'Hide' : 'Show'} History
                </Button>
              </Group>
            }
          >
            {showHistory && (
              <Stack spacing="xs" mt="md">
                {queryHistory.map((item) => (
                  <Alert
                    key={item.id}
                    icon={<IconBrain size={16} />}
                    color="blue"
                    variant="light"
                    withCloseButton
                    closeButtonLabel="Remove from history"
                    onClose={() => {
                      const filtered = queryHistory.filter(q => q.id !== item.id);
                      setQueryHistory(filtered);
                      localStorage.setItem('askQueryHistory', JSON.stringify(filtered));
                    }}
                    styles={{ root: { cursor: 'pointer' } }}
                    onClick={() => handleLoadHistoryItem(item)}
                  >
                    {item.question}
                  </Alert>
                ))}
              </Stack>
            )}
          </Alert>
        )}
      </Stack>
    </Box>
  );
};

export default AskPage;