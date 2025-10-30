// modules/1-preprocessing.nf

process CHECK_PRS_FILES {
    tag "check_prs_files"
    publishDir "${params.paths.output_dir}/preprocessing", mode: 'copy', pattern: "*.csv"
    publishDir "${params.paths.output_dir}/log", mode: 'copy', pattern: "*.log"
    conda "${params.paths.envs_dir}/polygenie-pipeline.yml"

    input:
    path prs_metadata

    output:
    path "prs_present.csv", emit: prs_present
    path "prs_check.log", emit: prs_log

    script:
    """
    python ${file("bin/check_prs_files.py")} \
        --metadata ${prs_metadata} \
        --log prs_check.log \
        --prs-dir ${workflow.projectDir} \
        --output prs_present.csv \
        --check-columns ${params.prs.check_columns.join(' ')}
    """
}

process CHECK_PHENOTYPE_FILES {
    tag "check_phenotypes"
    publishDir "${params.paths.output_dir}/preprocessing", mode: 'copy', pattern: "*.csv"
    publishDir "${params.paths.output_dir}/log", mode: 'copy', pattern: "*.log"
    conda "${params.paths.envs_dir}/polygenie-pipeline.yml"

    input:
    path phenotype_metadata

    output:
    path "phenotypes_valid.csv", emit: phenotypes_valid
    path "phenotypes_check.log", emit: phenotypes_log

    script:
    """
    python ${file("bin/check_phenotype_files.py")} \
        --metadata ${phenotype_metadata} \
        --project-dir ${workflow.projectDir} \
        --log phenotypes_check.log \
        --output phenotypes_valid.csv \
        --min-cases ${params.thresholds.min_cases}
    """
}