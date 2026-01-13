import logging
import os
import sqlite3
import pandas as pd


# Logger for db_loader messages
db_logger = logging.getLogger('db_handler_logger')
db_logger.setLevel(logging.ERROR)
db_handler = logging.FileHandler('logs/db_handler.log')
db_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
db_logger.addHandler(db_handler)

class DBHandler:
    '''
    The `DBHandler` class provides methods to interact with an SQLite database, 
    handling the querying and manipulation of GWAS (Genome-Wide Association Studies) data, individuals, 
    targets, and phenotypes. It also supports inserting new data and performing basic statistics on the records.

    Attributes
    ----------
    db_path : str
        The file path to the SQLite database.
    
    Methods
    -------
    create_db(schema_file)
        Creates the database schema from a provided SQL file.
    connect()
        Establishes a connection to the SQLite database.
    get_gwas_names()
        Retrieves the list of all GWAS names from the database.
    get_correlations(gwas, quartile, reference, division, target_type)
        Fetches correlation data for a specific GWAS, quartile, reference, division, and target type.
    get_gwas_metadata(gwas)
        Retrieves metadata associated with a specific GWAS entry.
    get_indiv_ids()
        Fetches individual IDs and their corresponding entity IDs.
    get_indiv_stats()
        Returns a count of total individuals, male individuals, and female individuals.
    get_indiv_stats_for_target(target)
        Fetches the number of individuals with a specific target phenotype.
    get_target_code(desc, t_type)
        Retrieves the code for a target based on its description and type.
    get_phecodes()
        Returns all Phecodes from the database.
    get_icd_codes()
        Returns all ICD codes from the database.
    get_prevalences(gwas, target)
        Retrieves prevalence data for a given GWAS and target.
    get_indiv_count()
        Returns the total count of individuals, with counts for males and females.
    get_age_and_gender()
        Retrieves age, gender, BMI, and self-perceived health status for all individuals.
    get_target_stats()
        Retrieves statistical data about targets and their associated phenotypes.
    get_risk_scores(self, target, gwas, percentile)
        Retrieves the risk scores for a set target, gwas and percentile.
    set_targets(df)
        Inserts or updates target information in the database.
    set_individuals(df)
        Inserts or updates individual information in the database.
    set_phenotypes(df)
        Inserts or updates phenotypes for individuals in the database.
    set_gwas(df)
        Inserts or updates GWAS data from a pandas DataFrame.
    set_correlations(self, df)
        Inserts or updates correlations data from a pandas DataFrame.
    set_prs(self, df)
        Inserts or updates risk_scores data from a pandas DataFrame.
    db_writer_prevalences(self, result_queue)
        Inserts or updates prevalences data with the data from a queue. 
        Meant to use for inserting data that is being computed in parallel with several threads.
    _bulk_insert(self, batch, query, batch_size=1000)
        Inserts data to the DB from a given batch of information and using the specified query. 
        Meant for internal use only, it should not be called from methods outside this class.
    '''

    def __init__(self, db_path):
        """
        Initialises the `DBHandler` instance.

        Parameters
        ----------
        db_path : str
            The file path to the SQLite database.
        """
        self.db_path = db_path

    def create_db(self, schema_file, db_location):
        """
        Creates the database schema from the provided SQL file.

        Parameters
        ----------
        schema_file : str
            Path to the SQL file that contains the schema definition.
        """
        conn = self.connect(db_location)
        cursor = conn.cursor()

        with open(schema_file, 'r') as file:
            cursor.executescript(file.read())
        
        conn.close()

    def connect(self, db_path=0):
        """
        Establishes a connection to the SQLite database.

        Returns
        -------
        sqlite3.Connection
            A connection object to interact with the SQLite database.
        """
        if db_path == 0: return sqlite3.connect(self.db_path)
        else: return sqlite3.connect(db_path)
    
    #################################################################################################################################
    ############################################################  READS  ############################################################
    #################################################################################################################################

    def get_cohorts(self):
        """
        Fetches cohorts data.

        Returns
        -------
        pandas.DataFrame
            A DataFrame containing the cohorts data.
        """
        conn = self.connect()
        cursor = conn.cursor()

        query = 'SELECT * FROM cohorts'

        rows = cursor.execute(query).fetchall()
        gwas_list = [gwas[0] for gwas in rows]

        conn.close()

        return gwas_list

    def get_gwas_names(self):
        """
        Retrieves a list of all GWAS names from the database.

        Returns
        -------
        list of str
            List of GWAS names.

        Examples
        --------
        >>> handler = DBHandler('database.db')
        >>> gwas_names = handler.get_gwas_names()
        >>> print(gwas_names)
        ['GWAS1', 'GWAS2', 'GWAS3']
        """
        conn = self.connect()
        cursor = conn.cursor()
        rows = cursor.execute("SELECT name FROM gwas").fetchall()
        conn.close()

        gwas_list = [gwas[0] for gwas in rows]

        return gwas_list
    
    def get_gwas_codes(self):
        """
        Retrieves a list of all GWAS codes from the database.

        Returns
        -------
        list of str
            List of GWAS codes.
        """
        conn = self.connect()
        cursor = conn.cursor()
        rows = cursor.execute("SELECT code FROM gwas").fetchall()
        conn.close()

        gwas_list = [gwas[0] for gwas in rows]

        return gwas_list
    
    def get_gwas_name_from_code(self, code):
        """
        Retrieves the name of a GWAS with the given code.

        Returns
        -------
        str
            The name for the GWAS.

        """
        conn = self.connect()
        cursor = conn.cursor()
        query = '''
        SELECT name FROM gwas WHERE code = ?
        ''' 
        name = cursor.execute(query, (code,)).fetchall()
        conn.close()

        return name

    def get_gwas_code_from_name(self, name):
        """
        Retrieves the code of a GWAS with the given name.

        Returns
        -------
        str
            The code for the GWAS.

        """
        conn = self.connect()
        cursor = conn.cursor()
        query = '''
        SELECT code FROM gwas WHERE name = ?
        ''' 
        name = cursor.execute(query, (name,)).fetchone()
        if name:
            name = name[0]  # Extract the single value from the tuple
        else:
            name = None  # Handle the case where no result is returned
        conn.close()

        return name

    def get_correlations(self, gwas, reference, division, target_type):
        """
        Fetches correlation data for the specified GWAS, quartile, reference, division, and target type.

        Parameters
        ----------
        gwas : str
            The GWAS name.
        quartile : int
            The quartile value.
        reference : str
            The reference value.
        division : str
            The division value.
        target_type : str
            The type of target (e.g., 'Phecode', 'ICD code').

        Returns
        -------
        pandas.DataFrame
            A DataFrame containing the correlation data.
        """
        conn = self.connect()
        cursor = conn.cursor()

        query = '''
            SELECT
                c.gwas,
                c.target,
                c.reference,
                c.division,
                c.odds_ratio,
                c.CI_5,
                c.CI_95,
                c.P,
                c.R2,
                c.logpxdir,
                t.description,
                t.class,
                t.type,
                g.name
            FROM
                correlations c
            JOIN
                targets t ON c.target = t.code,
                gwas g ON c.gwas = g.code
            WHERE
                c.gwas = ?
                AND c.reference = ?
                AND c.division = ?
                AND t.type = ?;
            '''
        
        rows = cursor.execute(query, (gwas, reference, division, target_type,)).fetchall()
        column_names = [description[0] for description in cursor.description]
        data = pd.DataFrame(rows, columns=column_names)

        conn.close()

        return data

    def get_all_gwas_metadata(self):
        """
        Retrieves metadata for all GWAS.

        Returns
        -------
        pandas.DataFrame
            A DataFrame containing the GWAS metadata.
        """
        conn = self.connect()
        cursor = conn.cursor()

        query = '''
            SELECT *
            FROM gwas
            ''' 
        
        rows = cursor.execute(query).fetchall()
        column_names = [description[0] for description in cursor.description]
        data = pd.DataFrame(rows, columns=column_names)

        conn.close()

        return data

    def get_gwas_metadata(self, gwas):
        """
        Retrieves metadata associated with a specific GWAS entry.

        Parameters
        ----------
        gwas : str
            The name of the GWAS.

        Returns
        -------
        pandas.DataFrame
            A DataFrame containing the GWAS metadata.
        """
        conn = self.connect()
        cursor = conn.cursor()

        query = '''
            SELECT *
            FROM gwas
            WHERE name = ?;
            ''' 
        
        rows = cursor.execute(query, (gwas,)).fetchall()
        column_names = [description[0] for description in cursor.description]
        data = pd.DataFrame(rows, columns=column_names)

        conn.close()

        return data
    
    def get_indiv_ids(self):
        """
        Fetches individual IDs and their corresponding entity IDs.

        Returns
        -------
        pandas.DataFrame
            A DataFrame containing the individual IDs and entity IDs.
        """
        conn = self.connect()
        cursor = conn.cursor()

        query = 'SELECT entity_id, iid FROM individuals'

        rows = cursor.execute(query).fetchall()
        data = pd.DataFrame(rows, columns=['entity_id', 'iid'])

        conn.close()

        return data

    def get_all_indiv(self):
        """
        Fetches individuals data.

        Returns
        -------
        pandas.DataFrame
            A DataFrame containing the individuals data.
        """
        conn = self.connect()
        cursor = conn.cursor()

        query = 'SELECT * FROM individuals'

        rows = cursor.execute(query).fetchall()
        column_names = [description[0] for description in cursor.description]
        data = pd.DataFrame(rows, columns=column_names)

        conn.close()

        return data

    def get_indiv_stats(self):
        """
        Returns the count of total individuals, male individuals, and female individuals.

        Returns
        -------
        pandas.DataFrame
            A DataFrame containing the statistics of individuals.
        """
        conn = self.connect()
        cursor = conn.cursor()

        query = '''
        SELECT
            COUNT(DISTINCT i.entity_id) AS total_individuals,
            SUM(CASE WHEN i.gender = 'Male' THEN 1 ELSE 0 END) AS total_males,
            SUM(CASE WHEN i.gender = 'Female' THEN 1 ELSE 0 END) AS total_females
        FROM
            individuals i
        '''
        rows = cursor.execute(query).fetchall()
        column_names = [description[0] for description in cursor.description]
        data = pd.DataFrame(rows, columns=column_names)

        conn.close()

        return data

    def get_indiv_stats_for_target(self, target):
        """
        Fetches the number of individuals with a specific target phenotype.

        Parameters
        ----------
        target : str
            The description of the target phenotype.

        Returns
        -------
        pandas.DataFrame
            A DataFrame containing the count of individuals with the target phenotype, including males and females.
        """
        conn = self.connect()
        cursor = conn.cursor()

        query = '''
        SELECT
            COUNT(DISTINCT i.entity_id) AS individuals_with_target,
            SUM(CASE WHEN i.gender = 'Male' THEN 1 ELSE 0 END) AS males_with_target,
            SUM(CASE WHEN i.gender = 'Female' THEN 1 ELSE 0 END) AS females_with_target
        FROM
            individuals i
        LEFT JOIN
            phenotypes p ON i.entity_id = p.indiv_id
        LEFT JOIN
            targets t ON p.target_id = t.code
        WHERE
            t.description = ?
        '''
        rows = cursor.execute(query, (target,)).fetchall()
        column_names = [description[0] for description in cursor.description]
        data = pd.DataFrame(rows, columns=column_names)

        conn.close()

        return data
    
    def get_iid_gender(self):
        """
        Returns the iid and gender of all the individuals.

        Returns
        -------
        pandas.DataFrame
            A DataFrame containing the iid and gender of the individuals.
        """
        conn = self.connect()
        cursor = conn.cursor()
        query = 'SELECT iid, gender FROM individuals'

        rows = cursor.execute(query).fetchall()
        column_names = [description[0] for description in cursor.description]
        data = pd.DataFrame(rows, columns=column_names)
        conn.close()

        return data

    def get_target_code(self, desc, t_type):
        """
        Retrieves the code for a target based on its description and type.

        Parameters
        ----------
        desc : str
            The description of the target.
        t_type : str
            The type of the target (e.g., 'Phecode', 'ICD code').

        Returns
        -------
        str
            A string containing the code for the target
        """
        conn = self.connect()
        cursor = conn.cursor()
        query = 'SELECT code FROM targets WHERE description = ? AND type = ?'
        code = cursor.execute(query, (desc, t_type,)).fetchone()
        if code:
            code = code[0]  # Extract the single value from the tuple
        else:
            code = None  # Handle the case where no result is returned
        conn.close()

        return code

    def get_target_codes(self, t_type):
        """
        Returns all codes of a type from the database.

        Returns
        -------
        list of str
            List of codes values.
        """
        conn = self.connect()
        cursor = conn.cursor()

        query = '''
        SELECT code FROM targets
        WHERE type = ?
        '''

        rows = cursor.execute(query, (t_type,)).fetchall()
        phecodes = [code[0] for code in rows]

        conn.close()

        return phecodes

    def get_prevalences(self, gwas, target):
        """
        Retrieves prevalence data for a given GWAS and target.

        Parameters
        ----------
        gwas : str
            The GWAS ID.
        target : str
            The target ID.

        Returns
        -------
        pandas.DataFrame
            A DataFrame containing prevalence data.
        """
        conn = self.connect()
        cursor = conn.cursor()

        query = '''
        SELECT
            percentile,
            prevalence_all,
            prevalence_female,
            prevalence_male
        FROM
            prevalences
        WHERE
            gwas_id = ? AND target_id = ?
        '''

        rows = cursor.execute(query, (gwas, target,)).fetchall()    
        column_names = [description[0] for description in cursor.description]
        data = pd.DataFrame(rows, columns=column_names)

        conn.close()

        return data
    
    def get_indiv_count(self):
        """
        Returns the total count of individuals, with counts for males and females.

        Returns
        -------
        list
            A list containing total individuals, male count, and female count.

        Examples
        --------
        >>> handler = DBHandler('database.db')
        >>> count = handler.get_indiv_count()
        >>> print(count)
        [1000, 500, 500]
        """
        conn = self.connect()
        cursor = conn.cursor()

        query = '''
        SELECT 
            COUNT(iid) AS total_individuals,
            SUM(CASE WHEN gender = 'Male' THEN 1 ELSE 0 END) AS male_count,
            SUM(CASE WHEN gender = 'Female' THEN 1 ELSE 0 END) AS female_count
        FROM individuals
        '''

        rows = cursor.execute(query).fetchall()
        conn.close()

        return list(rows[0]) #return a list with the three items
    
    def get_age_and_gender(self):
        """
        Retrieves age, gender, BMI, and self-perceived health status for all individuals.

        Returns
        -------
        pandas.DataFrame
            A DataFrame containing age, gender, BMI, and self-perceived health status.
        """
        conn = self.connect()
        cursor = conn.cursor()

        query = "SELECT gender, age, bmi, self_perceived_hs FROM individuals"

        rows = cursor.execute(query).fetchall()
        df = pd.DataFrame(rows, columns=['gender', 'age', 'bmi', 'self_perceived_hs'])

        conn.close()

        return df
    
    def get_target_stats(self):
        """
        Retrieves statistical data about targets and their associated phenotypes.

        Returns
        -------
        pandas.DataFrame
            A DataFrame containing target statistics, including gender, age, BMI, and count.
        """
        conn = self.connect()
        cursor = conn.cursor()

        query = '''
            SELECT 
                t.code AS target_id,
                t.description AS target_description,
                t.type AS target_type,
                i.gender,
                i.age,
                i.bmi,
                i.self_perceived_hs,
                COUNT(*) AS count
            FROM 
                phenotypes p
            JOIN 
                individuals i ON p.indiv_id = i.entity_id
            JOIN 
                targets t ON p.target_id = t.code
            GROUP BY 
                t.code, t.description, t.type, i.gender, i.age, i.bmi, i.self_perceived_hs
            ORDER BY 
                t.code, i.gender, i.age;
            '''
        rows = cursor.execute(query).fetchall()
        data = pd.DataFrame(rows, columns=[
                'target_id', 'target_description', 'target_type', 'gender', 'age', 'bmi', 'self_perceived_hs', 'count'
            ])

        conn.close()

        return data
    
    def get_risk_scores(self, target, gwas, percentile):
        """
        Returns the risk scores for a specified target, gwas and percentile.

        Parameters
        ----------
        target : str
            The code of the target.
        gwas: str
            The code of the GWAS
        percentile: int
            The percentile (0 to 99) of interest

        Returns
        -------
        pandas.DataFrame
            A DataFrame containing the risk scores.
        """
        conn = self.connect()
        cursor = conn.cursor()

        query = '''
        SELECT
            i.iid AS individual_id,
            rs.prs_score AS risk_score,
            rs.prs_percentile_all AS percentile_all,
            rs.prs_percentile_female AS percentile_female,
            rs.prs_percentile_male AS percentile_male,
            p.phenotype AS has_target
        FROM individuals i
        JOIN risk_scores rs ON i.iid = rs.indiv_id
        LEFT JOIN phenotypes p ON i.iid = p.indiv_id AND p.target_id = ?
        WHERE rs.gwas_id = ?
        AND (
            (rs.prs_percentile_all = ?)
            OR (rs.prs_percentile_female = ? AND i.gender = 'Female')
            OR (rs.prs_percentile_male = ? AND i.gender = 'Male')
        );
        '''

        rows = cursor.execute(query, (target, gwas, percentile, percentile, percentile,)).fetchall()
        data = pd.DataFrame(rows)
        conn.close()

        return data

    def get_all_risk_scores(self):
        conn = self.connect()
        cursor = conn.cursor()
    
        query = '''SELECT * FROM risk_scores'''

        rows = cursor.execute(query).fetchall()
        column_names = [description[0] for description in cursor.description]
        data = pd.DataFrame(rows, columns=column_names)
        conn.close()

        return data
    
    def get_phenotypes(self, target_type):
        """
        Returns the phenotypes for a specified target type (ICD, phecode or metabolite).

        Parameters
        ----------
        target_type : str
            The type of the target.
        Returns
        -------
        pandas.DataFrame
            A DataFrame containing the phenotypes for the specified target type.
        """

        conn = self.connect()
        cursor = conn.cursor()

        query = '''
        SELECT p.indiv_id, p.target_id, t.type
        FROM phenotypes p
        JOIN targets t ON p.target_id = t.code
        WHERE t.type = ?;
        '''
        rows = cursor.execute(query, (target_type,)).fetchall()
        column_names = [description[0] for description in cursor.description]
        data = pd.DataFrame(rows, columns=column_names)
        conn.close()

        return data

    def get_target_scope(self, target):
        """
        Returns the scope for a specified target.
        """

        conn = self.connect()
        cursor = conn.cursor()

        query = '''
        SELECT scope FROM targets WHERE code = ?
        '''
        rows = cursor.execute(query, (target,)).fetchall()
        word = rows[0][0] if rows else None
        conn.close()

        return word
    
    def get_target_counts(self, t_type):
        """
        Returns a df with indicating the count for each target.

        Parameters
        ----------
        t_type : str
            The type of the target.

        Returns
        -------
        pandas.DataFrame
            A DataFrame containing the count for all targets.
        """

        conn = self.connect()
        cursor = conn.cursor()

        query = '''
            SELECT code AS target_id, phenotype_count
            FROM targets
            WHERE type = ?;
        '''
        rows = cursor.execute(query,  (t_type,)).fetchall()
        column_names = [description[0] for description in cursor.description]
        data = pd.DataFrame(rows, columns=column_names)
        conn.close()

        return data

    #################################################################################################################################
    ############################################################ INSERTS ############################################################
    #################################################################################################################################

    # All inserts are performed with INSERT OR REPLACE to avoid duplicates

    def _bulk_insert(self, batch, query, batch_size=100):
        """
        Method for internal use only.  Inserts the batch of data with the specified query.

        Parameters
        ----------
        batch: list of lists
            List where each entry is a list with the parameters needed for one insert.
        query: str
            SQL insert statement
        batch_size: int
            Maximum size of a transaction batch.  If the batch is longer, it will be split in smaller batches to fit this max.
        """
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")

        try:
            # Begin transaction manually to wrap all inserts in a single transaction (less commit overhead)
            conn.execute("BEGIN TRANSACTION")
            for i in range(0, len(batch), batch_size):
                conn.executemany(query, batch[i:i+batch_size])
            conn.commit()

        except sqlite3.IntegrityError as e:
            conn.execute("ROLLBACK")
            db_logger.error(f"Integrity error during insert: {e}")
        except Exception as e:
            conn.execute("ROLLBACK")
            db_logger.error(f"Error during insert: {e}")
        finally:
            cursor.close()
            conn.close()

    def set_targets(self, df):
        """
        Inserts the df data to the targets table of the DB.

        Parameters
        ----------
        df: pandas.DataFrame
            DataFrame with the information to be inserted.
        """
        query = f'''
        INSERT OR REPLACE INTO targets (code, description, class, type, scope) 
        VALUES (?, ?, ?, ?, ?)
        '''
        batch = df[['code', 'description', 'class', 'type', 'scope']].values.tolist()
        self._bulk_insert(batch=batch, query=query)

    def set_cohorts(self, df):
        """
        Inserts the df data to the cohorts table of the DB.

        Parameters
        ----------
        df: pandas.DataFrame
            DataFrame with the information to be inserted.
        """
        query = f'''
        INSERT OR REPLACE INTO cohorts (cohort_name, population) 
        VALUES (?, ?)
        '''
        batch = df[['cohort', 'population']].values.tolist()
        self._bulk_insert(batch=batch, query=query)

    def set_populations(self, df):
        """
        Inserts the df data to the populations table of the DB.

        Parameters
        ----------
        df: pandas.DataFrame
            DataFrame with the information to be inserted.
        """
        query = f'''
        INSERT OR REPLACE INTO populations (population) 
        VALUES (?)
        '''
        batch = df[['population']].values.tolist()
        self._bulk_insert(batch=batch, query=query)

    def set_individuals(self, df):
        """
        Inserts the df data to the individuals table of the DB.

        Parameters
        ----------
        df: pandas.DataFrame
            DataFrame with the information to be inserted.
        """
        query = '''
        INSERT OR REPLACE INTO individuals (iid, entity_id, gender, age, bmi, self_perceived_hs, cohort)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        '''
        batch = df[['iid', 'entity_id', 'gender', 'age', 'bmi', 'self_perceived_hs', 'cohort']].values.tolist()
        self._bulk_insert(batch=batch, query=query)

    def set_gwas(self, df):
        """
        Inserts the df data to the gwas table of the DB.

        Parameters
        ----------
        df: pandas.DataFrame
            DataFrame with the information to be inserted.
        """
        sql_query = '''
        INSERT OR REPLACE INTO gwas (code, name, link_paper, link_sumstats, link_prevalence_mean, n, population)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        '''
        batch = df[['code', 'name', 'link_paper', 'link_sumstats', 'link_prevalence_mean', 'n', 'population']].values.tolist()
        self._bulk_insert(batch=batch, query=sql_query)

    def set_phenotypes(self, df):
        """
        Inserts the df data to the phenotypes table of the DB.

        Parameters
        ----------
        df: pandas.DataFrame
            DataFrame with the information to be inserted.
        """
        insert_statement = '''
        INSERT OR REPLACE INTO phenotypes (indiv_id, target_id)
        VALUES (?, ?)
        '''
        df.columns = ['indiv_id', 'target_id']
        print(df)
        batch = df[['indiv_id', 'target_id']].values.tolist()
        self._bulk_insert(batch=batch, query=insert_statement)

    def set_correlations(self, df):
        """
        Inserts the df data to the correlations table of the DB.

        Parameters
        ----------
        df: pandas.DataFrame
            DataFrame with the information to be inserted.
        """
        query = """
            INSERT OR REPLACE INTO correlations 
            (gwas, target, reference, division, odds_ratio, CI_5, CI_95, P, R2, logpxdir)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        print(df)
        batch = df[['gwas', 'target', 'reference', 'division', 'OR', 'CI_5', 'CI_95', 'P', 'R2', 'logpxdir']].values.tolist()
        db_logger.info(f"Inserting {len(batch)} rows into correlations.")
        self._bulk_insert(batch, query)

    def set_prs(self, df):
        """
        Inserts the df data to the risk_score table of the DB.

        Parameters
        ----------
        df: pandas.DataFrame
            DataFrame with the information to be inserted.
        """
        query = f"""
        INSERT OR REPLACE INTO risk_scores (indiv_id, gwas_id, prs_score, prs_percentile_all, prs_percentile_female, prs_percentile_male)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        batch = df[['indiv_id', 'gwas_id', 'prs_score', 'prs_percentile_all', 'prs_percentile_female', 'prs_percentile_male']].values.tolist()
        self._bulk_insert(batch, query)

    def set_prevalences(self, prevalences_list):
        """
        Inserts the data stored in a list to the prevalences table of the DB.
        Parameters
        ----------
        result_list: list
            list with the information to be inserted.
        """
        
        query = '''
        INSERT OR REPLACE INTO prevalences (gwas_id, target_id, percentile, prevalence_all, prevalence_female, prevalence_male)
        VALUES (?, ?, ?, ?, ?, ?)
        '''
        self._bulk_insert(prevalences_list, query)
    
