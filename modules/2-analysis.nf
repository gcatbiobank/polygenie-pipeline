// modules/2-analysis.nf

process COMPUTE_PRS_PERCENTILES {
    tag "${prs_name}"
    publishDir "${params.paths.output_dir}/percentiles", mode: 'copy', pattern: "*.csv"
    publishDir "${params.paths.output_dir}/log", mode: 'copy', pattern: "*.log"
    conda "${params.paths.envs_dir}/polygenie-pipeline.yml"

    input:
    tuple path(prs_file), path(prs_metadata), val(prs_name), path(phenotype_file), path(covariates_file), val(percentiles)

    output:
    path "*.csv", emit: prs_percentiles
    path "*.log", emit: prs_percentiles_log

    script:
    """
    python ${file("bin/compute_percentiles.py")} \
        --prs-file ${prs_file} \
        --prs-name ${prs_name} \
        --prs-metadata ${prs_metadata} \
        --covariates ${covariates_file} \
        --percentiles ${percentiles} \
        --phenotype-metadata ${phenotype_file} \
        --output ${prs_name}_percentiles.csv \
        ${params.prs.normalize ? "--normalize" : ""}
    """
}

process COMPUTE_PRS_REGRESSIONS {
    tag "${prs_name}"
    publishDir "${params.paths.output_dir}/regressions", mode: 'copy', pattern: "*.csv"
    publishDir "${params.paths.output_dir}/log", mode: 'copy', pattern: "*.log"
    conda "${params.paths.envs_dir}/polygenie-pipeline.yml"

    input:
    tuple path(prs_file), path(prs_metadata), val(prs_name), path(phenotype_file), path(covariates_file), val(percentiles)

    output:
    path "*.csv", emit: prs_regressions
    path "*.log", emit: prs_regressions_log

    script:
    def n_groups = params.prevalence?.groups ?: 10
    def include_intermediates = params.prevalence?.include_intermediates ? "--include-intermediates" : ""
    def normalize_flag = params.prevalence?.normalize ? "--normalize" : ""
    def base_covariates = params.covariates?.base ?: "CURRENT_AGE,GENDER,PC1,PC2,PC3,PC4,PC5,PC6,PC7,PC8,PC9,PC10"

    """
    python ${file("bin/compute_regressions.py")} \
        --prs-file ${prs_file} \
        --prs-name ${prs_name} \
        --prs-metadata ${prs_metadata} \
        --phenotype-metadata ${phenotype_file} \
        --covariates ${covariates_file} \
        --base-covariates "${base_covariates}" \
        --n-groups ${n_groups} \
        ${normalize_flag} \
        ${include_intermediates} \
        --output ${prs_name}_regressions.csv \
        --n-jobs ${task.cpus} \
        > ${prs_name}.log 2>&1
    """
}