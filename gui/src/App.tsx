import { useState } from 'react';
import { Container, Title, Text, Button, Box } from '@mantine/core';

function App() {
  const [count, setCount] = useState(0);

  return (
    <Container size="md" py="xl">
      <Title order={1} mb="md">Code Story</Title>
      <Text mb="lg">
        A system to convert codebases into richly-linked knowledge graphs with natural-language summaries.
      </Text>
      <Box my="xl" p="md" style={{ textAlign: 'center' }}>
        <Button onClick={() => setCount((count) => count + 1)}>
          count is {count}
        </Button>
      </Box>
    </Container>
  );
}

export default App;