import logging
import pandas as pd
import sys
import os
import warnings
import subprocess
from statsmodels.tools.sm_exceptions import PerfectSeparationWarning

warnings.filterwarnings('ignore', category=PerfectSeparationWarning)

# Get the root directory
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the root directory to sys.path
sys.path.append(root_dir)

from pipeline.correlation_calculator import CorrelationCalculatorFactory
from pipeline.genopred_adapter import AdapterFactory

# Get the root directory
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the root directory to sys.path
sys.path.append(root_dir)

from pipeline.prevalence_calculator import PrevalenceCalculator

# Logger for db_loader messages
db_logger = logging.getLogger('db_logger')
db_logger.setLevel(logging.INFO)
db_handler = logging.FileHandler('logs/db_loader.log')
db_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
db_logger.addHandler(db_handler)

class DBLoader:

    def __init__(self, db_handler, data_paths):
        self.db_handler = db_handler
        self.paths = data_paths
        self.prevalence_calculator = PrevalenceCalculator()

    def load_targets_data(self):
        # Metabolites
        met_dict = pd.read_csv(self.paths.metab_file, delimiter='\t')
        met_mapping = met_dict[['Variable', 'Description', 'Class']]
        met_mapping = met_mapping.rename(columns={'Variable':'code', 'Description':'description', 'Class':'class'})
        met_mapping['type'] = 'Metabolite'
        met_mapping['scope'] = 'both'
        self.db_handler.set_targets(met_mapping)

        # ICD codes
        icd_dict = pd.read_csv(self.paths.icd_file, sep='\t')
        icd_mapping = icd_dict[['three_digit', 'major', 'chapter']].drop_duplicates()
        icd_mapping = icd_mapping.rename(columns={'three_digit':'code', 'major':'description', 'chapter':'class'})
        #icd_mapping = icd_mapping[~icd_mapping['code'].str.startswith(('U', 'Z'))]  # Filter out codes starting with U or Z
        icd_mapping['type'] = 'ICD code'
        icd_mapping['scope'] = 'both'
        self.db_handler.set_targets(icd_mapping)

        # Phecodes
        phe_dict = pd.read_csv(self.paths.phecodes_file, sep='\t')
        phe_mapping = phe_dict[['phecode', 'phenotype', 'category']].drop_duplicates()
        phe_mapping = phe_mapping.rename(columns={'phenotype':'description', 'category':'class', 'phecode':'code'})
        phe_mapping['type'] = 'Phecode'
        phe_mapping['scope'] = 'both'
        self.db_handler.set_targets(phe_mapping)

        # Questionaire targets
        quest_dict = pd.read_csv(self.paths.quest_meta, sep='\t')
        quest_mapping = quest_dict[['Variable', 'Description', 'Domain', 'Type', 'sex']]
        quest_mapping = quest_mapping.rename(columns={'Variable': 'code', 'Description': 'description', 'Domain': 'class', 'sex': 'scope', 'Type': 'type'})
        self.db_handler.set_targets(quest_mapping)
            
    def load_individuals_data(self):
        data = pd.read_csv(self.paths.indiv_file, sep='\t')
        data['gender'] = data['gender'].str.capitalize()
        cohorts = self.db_handler.get_cohorts()
        if (~data['cohort'].isin(cohorts)).any():
            self.load_cohorts_data()

        self.db_handler.set_individuals(data)

    def load_cohorts_data(self):
        data = pd.read_csv(self.paths.cohorts_file, sep='\t')
        self.db_handler.set_cohorts(data)

    def load_populations_data(self):
        data = pd.read_csv(self.paths.population_file, sep='\t')
        self.db_handler.set_populations(data)

    def load_phenotypes(self):
        
        # Read Diseases
        phenotype_data = pd.read_csv(self.paths.phenotypes_file, sep='\t')
        #phenotype_data = phenotype_data[~phenotype_data['icd'].str.startswith(('Z', 'U'))]
        # Fetch mapping from entity_id to iid
        entity_to_iid = self.db_handler.get_indiv_ids()

        # Merge the entity_to_iid with phenotype_data to get iid and code
        phenotype_data = pd.merge(phenotype_data, entity_to_iid, on='entity_id')
        phenotype_icd_data = phenotype_data[phenotype_data['code'] == 'ICD10'][['iid', 'disease']].dropna()
        phenotype_phe_data = phenotype_data[phenotype_data['code'] == 'PHECODE'][['iid', 'disease']].dropna()

        # Get existing targets
        existing_targets = self.db_handler.get_target_codes('ICD code')
        phenotype_icd_data = phenotype_icd_data[phenotype_icd_data['disease'].isin(existing_targets)]
        phenotype_icd_data = phenotype_icd_data.drop_duplicates()

        existing_targets = self.db_handler.get_target_codes('Phecode')
        phenotype_phe_data['disease'] = phenotype_phe_data['disease'].astype(str)
        phenotype_phe_data = phenotype_phe_data[phenotype_phe_data['disease'].isin(existing_targets)]
        phenotype_phe_data = phenotype_phe_data.drop_duplicates()

        # Set ICD codes and Phecodes data
        self.db_handler.set_phenotypes(phenotype_icd_data)
        self.db_handler.set_phenotypes(phenotype_phe_data)

    def load_metadata(self, df):
        df = df[['name', 'label', 'source', 'sumstats_source', 'prevalence_mean_source', 'n', 'population']]

        # Rename columns to match the database schema
        df.rename(columns={
            'name': 'code',
            'label': 'name',
            'source': 'link_paper',
            'sumstats_source': 'link_sumstats',
            'prevalence_mean_source': 'link_prevalence_mean'
        }, inplace=True)

        # Insert data into the 'gwas' table
        self.db_handler.set_gwas(df)

    def load_correlation_data(self, file_path, file_name):

        gwas_code = file_name[:~7]

        # Load the mixed data file
        df = pd.read_csv(file_path, sep='\t')
        columns = ["gwas", "target", "reference", "division", "odds_ratio", "CI_5", "CI_95", "P", "R2", "logpxdir"]
        df.columns = columns
        
        # Load gwas name
        df['gwas'] = gwas_code

        # Insert data into the 'correlations' table
        self.db_handler.set_correlations(df)

    def load_prs(self, data, gwas_code):
        data = data.iloc[:, -2:]
        data.columns = ['iid', 'prs_score']
        data['gwas_id'] = gwas_code

        gender_table = self.db_handler.get_iid_gender()
        data = data.merge(gender_table, on='iid', how='left')

        data_sorted = data.sort_values(by='prs_score')

        # Compute percentiles
        for sex in ['all', 'Male', 'Female']:
            if sex in ['Male', 'Female']:
                tmp = data_sorted[data_sorted['gender']== sex].copy()
            else:
                tmp = data_sorted.copy()

            # Normalize the star_column (Z-score normalization)
            tmp['prs_score'] = (tmp['prs_score'] - tmp['prs_score'].mean()) / tmp['prs_score'].std()
            
            # Compute percentiles based on normalized values
            tmp['prs_percentile'] = pd.qcut(tmp['prs_score'], q=100, labels=False)
            percentile_mapping = tmp.set_index('iid')['prs_percentile']

            # Map the percentile data to `data_sorted`
            if (sex != 'all'):
                sex = 'male' if sex == 'Male' else 'female'
            data_sorted[f'prs_percentile_{sex}'] = data_sorted['iid'].map(percentile_mapping)


        data_sorted = data_sorted.rename(columns={'iid':'indiv_id'})

        # Insert data into the 'prs' table
        self.db_handler.set_prs(data_sorted)
        
    def load_pipeline_data(self, ori):
        db_logger.info(f"Loading pipeline data...") 

        # Load metadata
        df = pd.read_csv(self.paths.metadata_file)
        self.load_metadata(df)
        new_gwas_list = df['name'].to_list()
        db_logger.info(f"Stored new metadata.")

        profiles_dir = 'profiles_data'
        
        # List all files in the profiles directory
        for file in os.listdir(profiles_dir):
            if file.endswith('.profiles'):
                file_path = os.path.join(profiles_dir, file)
                gwas_name = file.split('-')[1]
                
                #if we are computing new gwas data, only process the new prs files
                if ori == 0 or gwas_name in new_gwas_list:  
                    adapter = AdapterFactory.create_general_adapter(file_path, self.db_handler, gwas_name, self.paths)
                    self.load_prs(adapter.get_prs(), gwas_name) # Load risk scores
                    db_logger.info(f"Stored new prs: {gwas_name}")
                    
                    # Mapping of target types to regression types
                    target_to_regression_map = {
                        #'Metabolite': 'linear',
                        'Phecode': 'logistic',                    
                        'ICD code': 'logistic',
                        #'Questionaire_log': 'logistic',
                        #'Questionaire_lin': 'linear'
                    }
                    
                    # Compute correlations
                    for target_type, regression_type in target_to_regression_map.items():
                        
                        # Adapt data
                        specific_adapter = AdapterFactory.get_specific_adapter(adapter, target_type)
                        df1, df2 = specific_adapter.get_adapted_data(target_type)
                        # Get specific calculator and compute correlations

                        if not df1.empty and not df2.empty:
                            specific_calculator = CorrelationCalculatorFactory.get_calculator(regression_type)
                            
                            result = specific_calculator.compute_correlations(df1, df2, gwas_name, target_type, self.db_handler)
                            
                            # Store the result in the database
                            self.db_handler.set_correlations(result)
                            db_logger.info(f"Stored {target_type} correlations for {gwas_name}")
            
                    
                    # Compute prevalences
                    prevalences = self.prevalence_calculator.calculate_prevalences(self.db_handler, gwas_name)
                    db_logger.info("Calculated new prevalences")
                    self.db_handler.set_prevalences(prevalences)
                    db_logger.info(f"Stored new prevalences.")
                    
    def load_pipeline_data_sge(self, ori):
        db_logger.info("Loading pipeline data using SGE...")

        # Define the profiles directory
        profiles_dir = 'profiles_data'
        
        # Gather all .profiles files
        profiles_files = [f for f in os.listdir(profiles_dir) if f.endswith('.profiles')]
        
        # Create the job array submission script
        job_script = 'submit_jobs.sh'
        
        with open(job_script, 'w') as f:
            f.write('#!/bin/bash\n')
            f.write('#$ -S /bin/bash\n')
            f.write('#$ -N db_loader_array\n')
            f.write('#$ -q d12imppc\n')
            f.write(f'#$ -t 1-{len(profiles_files)}\n')
            f.write('#$ -o logs/job_output.$JOB_ID.$TASK_ID.log\n')
            f.write('#$ -e logs/job_error.$JOB_ID.$TASK_ID.log\n')
            f.write('#$ -cwd\n\n')

            # Write the code to process the file
            f.write('PROFILES_DIR="profiles_data"\n')
            f.write('FILES=($(ls $PROFILES_DIR/*.profiles))\n')
            f.write('FILE=${FILES[$SGE_TASK_ID - 1]}\n')
            f.write('GWAS_NAME=$(basename "$FILE" | cut -d"-" -f2)\n')
            f.write('source /imppc/labs/dnalab/xfarrer/miniforge3/etc/profile.d/conda.sh\n')
            f.write('conda activate dashboard_project_env\n')
            f.write('mkdir -p logs\n')
            f.write('python pipeline/process_profile.py "$FILE" "$GWAS_NAME"\n')

        # Make the script executable
        subprocess.call(['chmod', '+x', job_script])

        # Submit the job array
        db_logger.info(f"Submitting job array with {len(profiles_files)} tasks...")
        subprocess.call(['qsub', job_script])

