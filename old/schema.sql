-- Enable foreign keys in SQLite (useful for enforcing foreign key constraints)
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS populations (
    population TEXT PRIMARY KEY NOT NULL
);

CREATE TABLE IF NOT EXISTS cohorts (
    cohort_name TEXT PRIMARY KEY NOT NULL,
    population TEXT,
    CONSTRAINT fk_population FOREIGN KEY (population) REFERENCES populations(population)
);

-- Table to store GWAS studies
CREATE TABLE IF NOT EXISTS gwas (
    code TEXT PRIMARY KEY NOT NULL, -- SQLite does not enforce the NOT NULL constraint in PK, that's why it needs to be added
    name TEXT UNIQUE NOT NULL,  -- All strings are stored as TEXT as it is the SQLite standard (VARCHAR is treated like TEXT)
    date TEXT,    
    link_paper TEXT,
    link_sumstats TEXT,
    link_prevalence_mean TEXT,
    n INTEGER,
    population TEXT,
    CONSTRAINT fk_population FOREIGN KEY (population) REFERENCES populations(population)
);

-- Table to store targets such as metabolites, ICD codes, or phecodes
CREATE TABLE IF NOT EXISTS targets (
    code TEXT PRIMARY KEY NOT NULL,
    description TEXT,
    class TEXT,
    type TEXT,
    scope TEXT,
    phenotype_count INTEGER DEFAULT 0
);

CREATE INDEX idx_targets_type ON targets (type); -- Allows for quicker searches by type

-- Table to store the phenotypes associated with individuals and targets
CREATE TABLE IF NOT EXISTS phenotypes (
    indiv_id TEXT NOT NULL,
    target_id  TEXT NOT NULL, 
    CONSTRAINT pk_phenotypes PRIMARY KEY (indiv_id, target_id),
    CONSTRAINT fk_indiv_phe FOREIGN KEY (indiv_id) REFERENCES individuals(iid) ON DELETE CASCADE,
    CONSTRAINT fk_targets_phe FOREIGN KEY (target_id) REFERENCES targets(code) ON DELETE CASCADE
);

CREATE TRIGGER trg_phenotypes_insert
AFTER INSERT ON phenotypes
FOR EACH ROW
BEGIN
    UPDATE targets
    SET phenotype_count = phenotype_count + 1
    WHERE code = NEW.target_id;
END;

CREATE TRIGGER trg_phenotypes_delete
AFTER DELETE ON phenotypes
FOR EACH ROW
BEGIN
    UPDATE targets
    SET phenotype_count = phenotype_count - 1
    WHERE code = OLD.target_id;
END;

CREATE TRIGGER trg_phenotypes_update
AFTER UPDATE OF target_id ON phenotypes
FOR EACH ROW
BEGIN
    UPDATE targets
    SET phenotype_count = phenotype_count - 1
    WHERE code = OLD.target_id;

    UPDATE targets
    SET phenotype_count = phenotype_count + 1
    WHERE code = NEW.target_id;
END;

-- Table to store correlations between GWAS and targets
CREATE TABLE IF NOT EXISTS correlations (
    gwas TEXT NOT NULL,
    target TEXT NOT NULL,
    reference TEXT NOT NULL,
    division TEXT NOT NULL,
    odds_ratio REAL,
    CI_5 REAL,
    CI_95 REAL,
    P REAL,
    R2 REAL,
    logpxdir REAL,
    CONSTRAINT pk_correlations PRIMARY KEY (gwas, target, reference, division),
    CONSTRAINT fk_gwas_corr FOREIGN KEY (gwas) REFERENCES gwas(code) ON DELETE CASCADE,
    CONSTRAINT fk_target_corr FOREIGN KEY (target) REFERENCES targets(code) ON DELETE CASCADE,
    CONSTRAINT chk_reference CHECK (reference IN ('low', 'rest')),
    CONSTRAINT chk_division CHECK (division IN ('quartile', 'decile'))
);

CREATE INDEX idx_correlations_gwas_ref_div ON correlations (gwas, reference, division); -- Allows for quicker searches for a set gwas, reference and division

-- Table to store information about individuals
CREATE TABLE IF NOT EXISTS individuals (
    iid  TEXT PRIMARY KEY NOT NULL, 
    entity_id TEXT UNIQUE,
    cohort TEXT NOT NULL,
    gender TEXT,
    age INTEGER,
    bmi REAL,
    self_perceived_hs TEXT,
    CONSTRAINT fk_cohort FOREIGN KEY (cohort) REFERENCES cohorts(cohort_name),
    CONSTRAINT chk_gender CHECK (gender IN ('Male', 'Female')),
    CONSTRAINT chk_age CHECK (age BETWEEN 0 AND 120),
    CONSTRAINT chk_bmi CHECK (bmi >= 0)
);

-- Table to store risk scores for individuals based on GWAS
CREATE TABLE IF NOT EXISTS risk_scores (
    indiv_id TEXT NOT NULL,
    gwas_id TEXT NOT NULL,
    prs_score REAL,
    prs_percentile_all INTEGER,
    prs_percentile_female INTEGER,
    prs_percentile_male INTEGER,
    CONSTRAINT pk_risk PRIMARY KEY (indiv_id, gwas_id),
    CONSTRAINT fk_indiv_risk FOREIGN KEY (indiv_id) REFERENCES individuals(iid) ON DELETE CASCADE,
    CONSTRAINT fk_gwas_risk FOREIGN KEY (gwas_id) REFERENCES gwas(code) ON DELETE CASCADE
);

-- Table to store prevalence of a trait within different percentiles for GWAS and targets
CREATE TABLE IF NOT EXISTS prevalences (
    gwas_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    percentile INTEGER NOT NULL,
    prevalence_all REAL,
    prevalence_female REAL,
    prevalence_male REAL,
    CONSTRAINT pk_prevalences PRIMARY KEY (gwas_id, target_id, percentile),
    CONSTRAINT fk_gwas_prev FOREIGN KEY (gwas_id) REFERENCES gwas(code) ON DELETE CASCADE,
    CONSTRAINT fk_target_prev FOREIGN KEY (target_id) REFERENCES targets(code) ON DELETE CASCADE,
    CONSTRAINT chk_prevalence CHECK (prevalence_all BETWEEN 0 AND 100),
    CONSTRAINT chk_prev_fem CHECK (prevalence_female BETWEEN 0 AND 100),
    CONSTRAINT chk_prev_masc CHECK (prevalence_male BETWEEN 0 AND 100),
    CONSTRAINT chk_percentile CHECK (percentile BETWEEN 0 AND 99)
);
