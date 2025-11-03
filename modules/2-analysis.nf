// modules/2-analysis.nf

process COMPUTE_PRS_PERCENTILES {
    cpus 1
    tag "${prs_name}"
    publishDir "${params.paths.output_dir}/percentiles", mode: 'copy', pattern: "*.csv"
    publishDir "${params.paths.output_dir}/log", mode: 'copy', pattern: "*.log"
    conda "${params.paths.envs_dir}/polygenie-pipeline.yml"

    input:
    tuple path(prs_file), path(prs_metadata), val(prs_name), path(phenotype_file), path(covariates_file), val(percentiles), val(normalize)

    output:
    path "*.csv", emit: prs_percentiles
    path "*.log", emit: prs_percentiles_log

    script:
    def normalize_flag = normalize ? "--normalize" : ""
    """
    python ${file("bin/compute_percentiles.py")} \
        --prs-file ${prs_file} \
        --prs-name ${prs_name} \
        --prs-metadata ${prs_metadata} \
        --covariates ${covariates_file} \
        --percentiles ${percentiles} \
        --phenotype-metadata ${phenotype_file} \
        --output ${prs_name}_percentiles.csv \
        ${normalize_flag}
    """
}

process COMPUTE_PRS_REGRESSIONS {
    cpus 4
    tag "${prs_name}"
    publishDir "${params.paths.output_dir}/regressions", mode: 'copy', pattern: "*.csv"
    publishDir "${params.paths.output_dir}/log", mode: 'copy', pattern: "*.log"
    conda "${params.paths.envs_dir}/polygenie-pipeline.yml"

    input:
    tuple path(prs_file), path(prs_metadata), val(prs_name), path(phenotype_file), path(covariates_file), val(n_groups), val(include_intermediates), val(normalize), val(label)

    output:
    path "*.csv", emit: prs_regressions
    path "*.log", emit: prs_regressions_log

    script:
    def include_inter_flag = include_intermediates ? "--include-intermediates" : ""
    def normalize_flag = normalize ? "--normalize" : ""
    def base_covariates = params.covariates?.base ?: "age,sex,PC1,PC2,PC3,PC4,PC5,PC6,PC7,PC8,PC9,PC10"
    // Construct descriptive filenames
    def inter_label = include_intermediates ? "withInter" : "noInter"
    def out_file = "${prs_name}_regression_${label}_${n_groups}groups_${inter_label}.csv"
    def log_file = "${prs_name}_regression_${label}_${n_groups}groups_${inter_label}.log"
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
        ${include_inter_flag} \
        --output ${out_file} \
        --n-jobs ${task.cpus} \
        > ${log_file} 2>&1
    """
}