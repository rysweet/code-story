import React, { useState } from 'react';
import {
  Paper,
  Button,
  Group,
  Text,
  Stack,
  Alert,
  Modal,
  Checkbox,
  Box,
  Card,
  Title,
} from '@mantine/core';
import { IconDatabase, IconTrash, IconAlertTriangle, IconCheck, IconX } from '@tabler/icons-react';
import { useClearDatabaseMutation } from '../../store/api/configApi';

/**
 * DatabaseManager component for database management operations
 */
const DatabaseManager: React.FC = () => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [confirmText, setConfirmText] = useState('');
  const [preserveSchema, setPreserveSchema] = useState(true);
  
  // RTK Query hook for the clear database operation
  const [clearDatabase, { isLoading, error, isSuccess, reset }] = useClearDatabaseMutation();
  
  // Open the confirmation modal
  const handleOpenModal = () => {
    setIsModalOpen(true);
    setConfirmText('');
    reset(); // Reset any previous mutation state
  };
  
  // Close the confirmation modal
  const handleCloseModal = () => {
    setIsModalOpen(false);
  };
  
  // Execute the database clear operation
  const handleClearDatabase = async () => {
    try {
      await clearDatabase({
        confirm: true,
        preserve_schema: preserveSchema
      }).unwrap();
      
      // Success will be handled by the isSuccess state
    } catch (err) {
      // Error will be handled by the error state
      console.error('Failed to clear database:', err);
    }
  };
  
  return (
    <>
      <Card withBorder radius="md" p="md">
        <Title order={3} mb="md">Database Management</Title>
        
        <Stack spacing="md">
          <Text>
            Perform database maintenance operations. These operations require admin privileges
            and can affect the entire system.
          </Text>
          
          <Box
            sx={(theme) => ({
              backgroundColor: theme.colorScheme === 'dark' 
                ? theme.colors.dark[6] 
                : theme.colors.gray[0],
              padding: theme.spacing.md,
              borderRadius: theme.radius.md,
            })}
          >
            <Stack spacing="xs">
              <Group position="apart">
                <Group>
                  <IconDatabase size={24} />
                  <div>
                    <Text weight={500}>Clear Database</Text>
                    <Text size="sm" color="dimmed">
                      Delete all data from the database. This cannot be undone.
                    </Text>
                  </div>
                </Group>
                
                <Button 
                  color="red" 
                  leftIcon={<IconTrash size={16} />} 
                  onClick={handleOpenModal}
                >
                  Clear Database
                </Button>
              </Group>
            </Stack>
          </Box>
        </Stack>
      </Card>
      
      {/* Confirmation Modal */}
      <Modal
        opened={isModalOpen}
        onClose={handleCloseModal}
        title={
          <Group>
            <IconAlertTriangle color="red" size={24} />
            <Text size="lg" weight={700}>Clear Database Confirmation</Text>
          </Group>
        }
        size="lg"
      >
        <Stack spacing="md">
          {isSuccess ? (
            <Alert 
              icon={<IconCheck size={16} />} 
              title="Database Cleared Successfully" 
              color="green"
            >
              All data has been removed from the database.
              {preserveSchema && " Schema constraints and indexes have been preserved."}
            </Alert>
          ) : error ? (
            <Alert 
              icon={<IconX size={16} />} 
              title="Error Clearing Database" 
              color="red"
            >
              {JSON.stringify(error)}
            </Alert>
          ) : (
            <>
              <Alert 
                icon={<IconAlertTriangle size={16} />}
                title="Warning: This Operation Cannot Be Undone" 
                color="red"
              >
                You are about to delete ALL data from the database. This includes all nodes, 
                relationships, and properties. This operation cannot be undone.
              </Alert>
              
              <Checkbox
                label="Preserve schema (constraints and indexes)"
                checked={preserveSchema}
                onChange={(e) => setPreserveSchema(e.currentTarget.checked)}
              />
              
              <Text size="sm">
                To confirm, please type <strong>CLEAR DATABASE</strong> in the field below:
              </Text>
              
              <input
                value={confirmText}
                onChange={(e) => setConfirmText(e.target.value)}
                placeholder="Type CLEAR DATABASE to confirm"
                style={{
                  width: '100%',
                  padding: '10px',
                  borderRadius: '4px',
                  border: '1px solid #ccc',
                }}
              />
              
              <Group position="right">
                <Button variant="outline" onClick={handleCloseModal}>
                  Cancel
                </Button>
                <Button
                  color="red"
                  leftIcon={<IconTrash size={16} />}
                  onClick={handleClearDatabase}
                  loading={isLoading}
                  disabled={confirmText !== 'CLEAR DATABASE'}
                >
                  Clear Database
                </Button>
              </Group>
            </>
          )}
          
          {isSuccess && (
            <Group position="right">
              <Button onClick={handleCloseModal}>
                Close
              </Button>
            </Group>
          )}
        </Stack>
      </Modal>
    </>
  );
};

export default DatabaseManager;