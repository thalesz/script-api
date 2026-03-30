-- Schema inicial do desafio (PostgreSQL)
-- Cria as tabelas e índices necessários do zero.

CREATE TABLE IF NOT EXISTS states (
    uf VARCHAR(2) PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS sncr_records (
    -- PRIMARY KEY cria automaticamente um indice B-tree unico em codigo_incra.
    -- Esse indice e o caminho principal para consultas por codigo dentro do SLA.
    codigo_incra TEXT PRIMARY KEY,
    matricula VARCHAR(20),
    municipio TEXT,
    denominacao TEXT,
    proprietario TEXT,
    pct_obtencao NUMERIC(12,4),
    uf VARCHAR(2) REFERENCES states(uf) ON DELETE RESTRICT,
    loaded_at TIMESTAMP DEFAULT now()
);

ALTER TABLE sncr_records
DROP COLUMN IF EXISTS source_file;

CREATE INDEX IF NOT EXISTS idx_sncr_uf ON sncr_records(uf);
CREATE INDEX IF NOT EXISTS idx_sncr_municipio ON sncr_records(municipio);
CREATE INDEX IF NOT EXISTS idx_sncr_proprietario ON sncr_records(proprietario);
