-- Fix existing table conflicts by using IF NOT EXISTS for columns
-- Add new fields to chat_messages table for LLM response parsing (only if they don't exist)
ALTER TABLE chat_messages 
ADD COLUMN IF NOT EXISTS code TEXT,
ADD COLUMN IF NOT EXISTS next_steps TEXT,
ADD COLUMN IF NOT EXISTS is_deployable BOOLEAN;

-- Add indexes for the new fields (only if they don't exist)
CREATE INDEX IF NOT EXISTS idx_chat_messages_is_deployable ON chat_messages(is_deployable) WHERE is_deployable IS NOT NULL;