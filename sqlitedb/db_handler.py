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
 
    def get_target_classes(self):
        """
        Return all distinct non-empty target_class values from the target table.

        Returns
        -------
        pandas.DataFrame
            Single-column DataFrame with column 'target_class'.
            Empty DataFrame if table does not exist or no valid classes found.
        """
        try:
            # Check table existence first
            exists = self._query(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='target'"
            )
            if exists.empty:
                logger.debug("Table does not exist: target")
                return pd.DataFrame(columns=['target_class'])

            df = self._query("""
                SELECT DISTINCT target_class
                FROM target
                WHERE target_class IS NOT NULL
                AND TRIM(target_class) != ''
                ORDER BY target_class
            """)

            if df.empty:
                logger.debug("No target_class values found in target table")

            return df

        except Exception as e:
            logger.debug("Could not fetch target classes: %s", e)
            return pd.DataFrame(columns=['target_class'])


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
                p.beta AS beta,
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
            if row['type'] == 'continuous' and pd.notnull(row['beta']):
                return np.sign(row['beta'])
            if row['type'] == 'binary' and pd.notnull(row['odds_ratio']):
                try:
                    return np.sign(row['odds_ratio'] - 1.0)
                except Exception:
                    return 0
            return 0
        df['logpxdir'] = df.apply(lambda r: (-np.log10(r['P']) * effect_sign(r)) if pd.notnull(r['P']) and r['P']>0 else None, axis=1)
        # Keep ordering consistent with app expectations
        cols = ['GWAS','Code','Reference','Division','beta', 'odds_ratio','CI_5','CI_95','P','R2','logpxdir','description','domain','class','type']
        # ensure domain column exists even if NULL
        if 'domain' not in df.columns:
            df['domain'] = None
        return df[cols]

    def get_prevalences(self, prs_name, target_code):
        """
        Return prevalence by PRS percentile for a given PRS and target.

        Returns
        -------
        pandas.DataFrame
            Columns: ['percentile', 'prs_column', 'sex', 'prevalence']
            Empty DataFrame if table does not exist or no data found.
        """
        logger.debug(
            "get_prevalences called prs_name=%s target_code=%s",
            prs_name, target_code
        )

        try:
            # Check table existence first
            exists = self._query(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='prevalence'"
            )
            if exists.empty:
                logger.debug("Table does not exist: prevalence")
                return pd.DataFrame(columns=['percentile', 'prs_column', 'sex', 'prevalence'])

            sql = """
                SELECT
                    percentile,
                    prs_column,
                    sex,
                    prevalence
                FROM prevalence
                WHERE prs_name = ?
                AND target_code = ?
                ORDER BY percentile, prs_column
            """

            df = self._query(sql, (prs_name, target_code))
            logger.debug("get_prevalences returned %d rows", len(df))

            return df

        except Exception as e:
            logger.debug(
                "Could not fetch prevalences for prs=%s target=%s: %s",
                prs_name, target_code, e
            )
            return pd.DataFrame(columns=['percentile', 'prs_column', 'sex', 'prevalence'])



    def get_target_code(self, description, target_type):
        """
        Return the internal target_code for a given target description and type.

        Parameters
        ----------
        description : str
            Human-readable target description.
        target_type : str
            Target type / class (e.g. 'Phecodes', 'ICD_codes', etc.)

        Returns
        -------
        str or None
            target_code if found, otherwise None.
        """
        logger.debug(
            "get_target_code called description=%s target_type=%s",
            description, target_type
        )

        if not description:
            logger.debug("get_target_code: empty description provided")
            return None

        try:
            # Check table existence first
            exists = self._query(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='target'"
            )
            if exists.empty:
                logger.debug("Table does not exist: target")
                return None

            sql = """
                SELECT target_code
                FROM target
                WHERE description = ?
                AND target_type = ?
                LIMIT 1
            """

            df = self._query(sql, (description, target_type))

            if df.empty:
                logger.debug(
                    "get_target_code: no match for description=%s target_type=%s",
                    description, target_type
                )
                return None

            code = df.iloc[0]['target_code']
            logger.debug(
                "get_target_code: found target_code=%s for description=%s target_type=%s",
                code, description, target_type
            )
            return code

        except Exception as e:
            logger.debug(
                "Could not fetch target_code for description=%s target_type=%s: %s",
                description, target_type, e
            )
            return None

    def get_target_type(self, target_code):
        """
        Return the target_type for a given target_code.

        Parameters
        ----------
        target_code : str
            Internal code identifying the target (e.g., ICD code, Phecode).

        Returns
        -------
        str or None
            The target_type if found, otherwise None.
        """
        logger.debug("get_target_type called with target_code=%s", target_code)

        if not target_code:
            logger.debug("get_target_type: empty target_code provided")
            return None

        try:
            # Check table existence first
            exists = self._query(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='target'"
            )
            if exists.empty:
                logger.debug("Table does not exist: target")
                return None

            sql = """
                SELECT target_type
                FROM target
                WHERE target_code = ?
                LIMIT 1
            """
            df = self._query(sql, (target_code,))

            if df.empty:
                logger.debug("get_target_type: no match for target_code=%s", target_code)
                return None

            target_type = df.iloc[0]['target_type']
            logger.debug("get_target_type: found target_type=%s for target_code=%s", target_type, target_code)
            return target_type

        except Exception as e:
            logger.debug("Could not fetch target_type for target_code=%s: %s", target_code, e)
            return None


