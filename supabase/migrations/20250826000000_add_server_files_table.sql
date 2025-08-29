-- Add server_files table to support multiple files per server
CREATE TABLE server_files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    server_id UUID NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
    filename VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    file_type VARCHAR(50) DEFAULT 'python',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Prevent duplicate filenames per server
    UNIQUE(server_id, filename)
);

-- Create indexes for better performance
CREATE INDEX idx_server_files_server_id ON server_files(server_id);
CREATE INDEX idx_server_files_filename ON server_files(filename);
CREATE INDEX idx_server_files_file_type ON server_files(file_type);

-- Create trigger for updated_at
CREATE TRIGGER update_server_files_updated_at BEFORE UPDATE ON server_files 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add a comment to document the table purpose
COMMENT ON TABLE server_files IS 'Stores multiple files for each MCP server to support complex multi-file applications';
COMMENT ON COLUMN server_files.filename IS 'Relative path and filename within the server directory';
COMMENT ON COLUMN server_files.content IS 'File content as text';
COMMENT ON COLUMN server_files.file_type IS 'File type/language for syntax highlighting and processing';