import sqlite3
import pandas as pd
from pathlib import Path
import logging
import os

logger = logging.getLogger(__name__)

class DBHandler:
    def __init__(self, db_file: str):
        self.db = db_file

    def _query(self, sql: str, params=()):
        # Log the query at debug level (compacted)
        try:
            logger.debug("SQL Query: %s -- params=%s", " ".join(sql.split()), params)
        except Exception:
            # Protect against logging issues
            pass
        try:
            con = sqlite3.connect(self.db)
            df = pd.read_sql(sql, con, params=params)
            con.close()
            logger.debug("Query returned %d rows", len(df))
            return df
        except Exception as e:
            logger.exception("Query failed: %s", e)
            raise

    def list_tables(self):
        """Return sqlite_master rows for tables and views."""
        return self._query("SELECT name, type, sql FROM sqlite_master WHERE type IN ('table','view') ORDER BY name")

    def table_count(self, table):
        """Return row count for given table or None if unavailable.

        This first checks sqlite_master to see if the table exists and avoids
        raising exceptions when legacy cohort tables are not present.
        """
        try:
            exists = self._query("SELECT name FROM sqlite_master WHERE type='table' AND name = ?", (table,))
            if exists.empty:
                logger.debug("Table does not exist: %s", table)
                return 0
            df = self._query(f"SELECT COUNT(*) AS cnt FROM {table}")
            return int(df.iloc[0]['cnt']) if not df.empty else 0
        except Exception as e:
            logger.debug("Could not get count for table %s: %s", table, e)
            return None

    def sample_table(self, table, limit=5):
        """Return up to `limit` rows from `table` as a DataFrame."""
        try:
            exists = self._query("SELECT name FROM sqlite_master WHERE type='table' AND name = ?", (table,))
            if exists.empty:
                logger.debug("Sample requested for missing table: %s", table)
                return pd.DataFrame()
            return self._query(f"SELECT * FROM {table} LIMIT ?", (limit,))
        except Exception as e:
            logger.debug("Could not sample table: %s (%s)", table, e)
            return pd.DataFrame()

    def get_db_summary(self, tables=None):
        """Return a dict of table -> count for common tables to help debugging."""
        tbls = tables or ['gwas_metadata', 'target', 'phewas_result', 'percentile_result', 'prevalence', 'individuals', 'phenotypes']
        summary = {}
        for t in tbls:
            summary[t] = self.table_count(t)
        return summary

    def get_gwas_names(self):
        """Return a list of GWAS labels for the dropdown."""
        df = self._query("SELECT COALESCE(label, name) AS label FROM gwas_metadata ORDER BY label")
        return df['label'].tolist()

    def get_gwas_code_from_name(self, display_name):
        """Map a human label back to the internal GWAS code (name)."""
        df = self._query("SELECT name FROM gwas_metadata WHERE label = ? OR name = ? LIMIT 1", (display_name, display_name))
        if df.empty:
            return display_name
        return df.iloc[0]['name']

    def get_gwas_metadata(self, display_name):
        """Return metadata row(s) for a GWAS (searching both name and label)."""
        return self._query("SELECT * FROM gwas_metadata WHERE label = ? OR name = ? LIMIT 1", (display_name, display_name))

    def get_prs_n_groups(self, prs_name):
        """Return sorted unique n_groups available for a given PRS name."""
        logger.debug("get_prs_n_groups called with prs_name=%s", prs_name)
        try:
            df = self._query("SELECT DISTINCT n_groups FROM phewas_result WHERE prs_name = ? AND n_groups IS NOT NULL ORDER BY n_groups", (prs_name,))
            if df.empty:
                logger.debug("No n_groups found for PRS: %s", prs_name)
                return []
            groups = [int(x) for x in df['n_groups'].tolist()]
            logger.debug("Found n_groups for %s: %s", prs_name, groups)
            return groups
        except Exception:
            logger.exception("Could not get n_groups for PRS: %s", prs_name)
            return []

    def get_prs_include_intermediates(self, prs_name):
        """Return True if any run for the PRS has include_intermediates set.

        This allows the UI to offer the "low + intermediate" reference option when applicable.
        """
        logger.debug("get_prs_include_intermediates called with prs_name=%s", prs_name)
        try:
            df = self._query("SELECT DISTINCT include_intermediates FROM phewas_result WHERE prs_name = ? AND include_intermediates IS NOT NULL", (prs_name,))
            if df.empty:
                logger.debug("No include_intermediates rows for PRS: %s", prs_name)
                return False
            # Values may be stored as 0/1 or '0'/'1' or boolean
            vals = set()
            for v in df['include_intermediates'].tolist():
                try:
                    vals.add(int(v))
                except Exception:
                    if isinstance(v, str) and v.lower() in ('true','t','yes'):
                        vals.add(1)
                    elif isinstance(v, str) and v.lower() in ('false','f','no'):
                        vals.add(0)
            result = 1 in vals
            logger.debug("include_intermediates values for %s: %s -> %s", prs_name, df['include_intermediates'].tolist(), result)
            return result
        except Exception:
            logger.exception("Could not get include_intermediates for PRS: %s", prs_name)
            return False

    def get_correlations(self, prs_name, reference, division, target_type):
        """Return a table of correlations (phewas_result joined with target metadata).
        The returned DataFrame has the columns expected by the app before it renames them.
        """
        logger.debug("get_correlations called prs_name=%s reference=%s division=%s target_type=%s", prs_name, reference, division, target_type)
        # Log distinct classes available for this PRS to help diagnose empty results
        try:
            classes_df = self._query("SELECT DISTINCT t.target_class FROM target t JOIN phewas_result p ON p.target_code = t.target_code WHERE p.prs_name = ?", (prs_name,))
            logger.debug("Available target_class values for %s: %s", prs_name, classes_df['target_class'].tolist() if not classes_df.empty else [])
        except Exception:
            logger.debug("Could not fetch distinct target_class values for %s", prs_name)

        sql = """
            SELECT
                p.prs_name AS GWAS,
                p.target_code AS Code,
                ? AS Reference,
                ? AS Division,
                p.odds_ratio AS odds_ratio,
                p.ci_low AS CI_5,
                p.ci_high AS CI_95,
                p.p_value AS P,
                NULL AS R2,
                t.description AS description,
                t.domain AS domain,
                t.target_class AS class,
                t.target_type AS type
            FROM phewas_result p
            LEFT JOIN target t ON t.target_code = p.target_code
            WHERE p.prs_name = ?
            -- Case-insensitive substring match on target_class (tolerates 'ICD_codes', 'ICD10', etc.)
            AND LOWER(COALESCE(t.target_class, '')) LIKE ('%' || LOWER(TRIM(?)) || '%')
            -- Optionally filter by number of groups (n_groups) if provided as Division
            AND (p.n_groups = ? OR ? IS NULL)
            -- Respect the reference selection using robust include_intermediates normalization
            AND (
                (? = 'rest' AND LOWER(COALESCE(CAST(p.include_intermediates AS TEXT), '0')) IN ('1','true','t','yes'))
                OR (? = 'low' AND LOWER(COALESCE(CAST(p.include_intermediates AS TEXT), '0')) NOT IN ('1','true','t','yes'))
                OR (? IS NULL)
            )
        """
        # Normalize division (n_groups) to an integer or None so SQLite binding works correctly
        try:
            groups_param = int(division) if division is not None and str(division) != '' else None
        except Exception:
            groups_param = None
        params = (reference, division, prs_name, target_type, groups_param, groups_param, reference, reference, reference)
        logger.debug("get_correlations executing SQL with params=%s", params)
        df = self._query(sql, params)
        logger.debug("get_correlations query returned %d rows", len(df))
        if df.empty:
            logger.debug("get_correlations: empty DataFrame for prs=%s target_type=%s", prs_name, target_type)
            return df
        # keep old alias for back-compat with app code
        df['OR'] = df['odds_ratio']
        logger.debug("get_correlations sample rows:\n%s", df.head().to_string(index=False))
        # compute logpxdir: -log10(p) * sign(effect)
        import numpy as np
        def effect_sign(row):
            # prefer beta if available
            if 'beta' in row and pd.notnull(row['beta']):
                return np.sign(row['beta'])
            if 'odds_ratio' in row and pd.notnull(row['odds_ratio']):
                try:
                    return np.sign(row['odds_ratio'] - 1.0)
                except Exception:
                    return 0
            return 0
        df['logpxdir'] = df.apply(lambda r: (-np.log10(r['P']) * effect_sign(r)) if pd.notnull(r['P']) and r['P']>0 else None, axis=1)
        # Keep ordering consistent with app expectations
        cols = ['GWAS','Code','Reference','Division','OR','CI_5','CI_95','P','R2','logpxdir','description','domain','class','type']
        # ensure domain column exists even if NULL
        if 'domain' not in df.columns:
            df['domain'] = None
        return df[cols]

    def get_prevalences(self, prs_name, target_code):
        sql = """
            SELECT percentile, sex, prevalence
            FROM prevalence
            WHERE prs_name = ?
            AND target_code = ?
            ORDER BY percentile
        """
        df = self._query(sql, (prs_name, target_code))
        if df.empty:
            return df
        # pivot to columns for All/Female/Male
        df['sex_norm'] = df['sex'].str.lower()
        pivot = df.pivot(index='percentile', columns='sex_norm', values='prevalence').reset_index()
        # Normalize column names to expected ones
        pivot.rename(columns={'both':'prevalence_all','female':'prevalence_female','male':'prevalence_male'}, inplace=True)
        # ensure columns exist
        for c in ['prevalence_all','prevalence_female','prevalence_male']:
            if c not in pivot.columns:
                pivot[c] = None
        return pivot[['percentile','prevalence_all','prevalence_female','prevalence_male']]

    def get_target_code(self, description, target_type):
        if not description:
            return None
        df = self._query("SELECT target_code FROM target WHERE description = ? AND target_type = ? LIMIT 1", (description, target_type))
        if df.empty:
            return None
        return df.iloc[0]['target_code']

    def get_target_stats(self):
        """Return per-target statistics suitable for the UI.

        Tries to produce a table with columns: ['target_id','target_description','target_type',
        'gender','age','bmi','self_perceived_hs','count'] by joining `phenotypes` and `individuals` if
        those tables exist. If not present, returns a fallback DataFrame with the required column names
        populated from the `target` table so the UI doesn't break.
        """
        try:
            sql = """
                SELECT
                    t.target_code AS target_id,
                    t.description AS target_description,
                    t.target_type AS target_type,
                    i.gender AS gender,
                    i.age AS age,
                    i.bmi AS bmi,
                    i.self_perceived_hs AS self_perceived_hs,
                    COUNT(*) AS count
                FROM phenotypes p
                JOIN individuals i ON i.entity_id = p.indiv_id
                JOIN target t ON p.target_id = t.target_code
                GROUP BY t.target_code, t.description, t.target_type, i.gender, i.age, i.bmi, i.self_perceived_hs
                ORDER BY t.target_code, i.gender, i.age
            """
            df = self._query(sql)
            return df
        except Exception:
            # Fallback to returning the list of targets with the expected column names
            df = self._query("SELECT target_code AS target_id, description AS target_description, target_type FROM target ORDER BY target_code")
            for c in ['gender', 'age', 'bmi', 'self_perceived_hs', 'count']:
                df[c] = None
            return df[['target_id', 'target_description', 'target_type', 'gender', 'age', 'bmi', 'self_perceived_hs', 'count']]

    def get_indiv_stats(self):
        # Read the covariates file to compute totals
        covar = Path('data/covars.csv')
        if not covar.exists():
            return pd.DataFrame()
        df = pd.read_csv(covar, sep=';', engine='python')
        total = len(df)
        males = len(df[df['sex'].str.lower() == 'male'])
        females = len(df[df['sex'].str.lower() == 'female'])
        return pd.DataFrame([{
            'total_individuals': total,
            'total_males': males,
            'total_females': females
        }])

    def get_indiv_stats_for_target(self, target_desc):
        """Return aggregated counts for individuals having the supplied target description.

        If the legacy cohort tables exist (individuals + phenotypes + target), query the DB; otherwise
        return an empty DataFrame so callers can show a friendly fallback message.
        """
        try:
            sql = """
            SELECT
                COUNT(DISTINCT i.entity_id) AS individuals_with_target,
                SUM(CASE WHEN i.gender = 'Male' THEN 1 ELSE 0 END) AS males_with_target,
                SUM(CASE WHEN i.gender = 'Female' THEN 1 ELSE 0 END) AS females_with_target
            FROM individuals i
            LEFT JOIN phenotypes p ON i.entity_id = p.indiv_id
            LEFT JOIN target t ON p.target_id = t.target_code
            WHERE t.description = ?
            """
            df = self._query(sql, (target_desc,))
            return df
        except Exception:
            return pd.DataFrame()
