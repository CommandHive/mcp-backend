-- Add new fields to chat_messages table for LLM response parsing
ALTER TABLE chat_messages 
ADD COLUMN IF NOT EXISTS code TEXT,
ADD COLUMN IF NOT EXISTS next_steps TEXT,
ADD COLUMN IF NOT EXISTS is_deployable BOOLEAN;

-- Add indexes for the new fields
CREATE INDEX IF NOT EXISTS idx_chat_messages_is_deployable ON chat_messages(is_deployable) WHERE is_deployable IS NOT NULL;
