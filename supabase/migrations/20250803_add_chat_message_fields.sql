-- Add new fields to chat_messages table for LLM response parsing
ALTER TABLE chat_messages 
ADD COLUMN code TEXT,
ADD COLUMN next_steps TEXT,
ADD COLUMN is_deployable BOOLEAN;

-- Add indexes for the new fields
CREATE INDEX idx_chat_messages_is_deployable ON chat_messages(is_deployable) WHERE is_deployable IS NOT NULL;