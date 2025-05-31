-- V1__Create_Extensions.sql
-- Sets up PostgreSQL extensions required by the database
-- For multi-tenant property management chatbot database

-- Enable UUID extension for generating UUIDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pgcrypto for encryption functions (useful for security)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Enable unaccent for text search without accents (useful for search functionality)
CREATE EXTENSION IF NOT EXISTS "unaccent";

-- Enable pg_trgm for trigram matching (useful for fuzzy search)
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Add comments to explain the purpose of each extension
COMMENT ON EXTENSION "uuid-ossp" IS 'Provides functions to generate universally unique identifiers (UUIDs)';
COMMENT ON EXTENSION "pgcrypto" IS 'Provides cryptographic functions for secure data storage';
COMMENT ON EXTENSION "unaccent" IS 'Provides text search dictionary that removes accents';
COMMENT ON EXTENSION "pg_trgm" IS 'Provides functions and operators for determining the similarity of text based on trigram matching';
