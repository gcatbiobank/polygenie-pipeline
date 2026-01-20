#!/usr/bin/env nextflow
nextflow.enable.dsl=2

/*
 * ---------------------------
 *   PolyGenie Correlation Pipeline
 *   PRS ↔ Phenotype Association Analysis
 *   Author: Xavier Farré
 * ---------------------------
 */

// Use SnakeYAML
import org.yaml.snakeyaml.Yaml

// Load configuration
params.config_file = params.config_file ?: "config/pipeline_config.yaml"
def configFile = file(params.config_file)
if (!configFile.exists()) {
    exit 1, "❌ Config file not found: ${params.config_file}"
}

def yaml = new Yaml().load(configFile.text)
println "DEBUG YAML regression_runs type: ${yaml.regression_runs?.getClass()?.name}"
println "DEBUG YAML regression_runs content: ${yaml.regression_runs}"

// Merge YAML sections into params
params.paths         = yaml.paths
params.thresholds    = yaml.thresholds
params.prs           = yaml.prs
params.prevalence    = yaml.prevalence
params.covariates    = yaml.covariates
params.regression_runs = yaml.regression_runs
params.percentile_plot = yaml.percentile_plot

// 🧬 Print pipeline header
def now = new Date().format("yyyy-MM-dd HH:mm:ss")
def divider = "-" * 70

log.info(divider)
log.info("🧬  POLYGENIE CORRELATION PIPELINE")
log.info(divider)
log.info("Date & Time           : ${now}")
log.info("Nextflow Version      : ${nextflow.version}")
log.info("Project Directory     : ${workflow.projectDir}")
log.info("Launch Directory      : ${workflow.launchDir}")
log.info("Work Directory        : ${workflow.workDir}")
log.info("Output Directory      : ${params.paths.output_dir}")
log.info("")
log.info("PRS metadata          : ${params.paths.prs_metadata}")
log.info("Phenotypes metadata   : ${params.paths.phenotype_metadata}")
log.info("Covariates File       : ${params.paths.covariates}")
log.info("")
log.info("Normalize PRS         : ${params.prs.normalize}")
log.info("Normalization Method  : ${params.prs.normalization_method}")
log.info("Default Covariates    : ${params.covariates}")
log.info("Number of percentiles : ${params.prevalence.percentiles}")
log.info("")
log.info("Container/Conda       : ${workflow.container ?: 'none'}")
log.info(divider)
log.info("👟  Starting analysis ...")
log.info(divider)

// Include modules
include { CHECK_PRS_FILES; CHECK_PHENOTYPE_FILES } from './modules/1-preprocessing.nf'

include { COMPUTE_PRS_PERCENTILES; COMPUTE_PRS_REGRESSIONS } from './modules/2-analysis.nf'

workflow {
    // -------------------------------
    // Step 1: Check PRS files
    // -------------------------------

    prs_meta_ch = Channel.fromPath(params.paths.prs_metadata)
    prs_checked = CHECK_PRS_FILES(prs_meta_ch)

    // -------------------------------
    // Step 2: Check phenotype files
    // -------------------------------

    pheno_meta_ch = Channel.fromPath(params.paths.phenotype_metadata)
    pheno_checked = CHECK_PHENOTYPE_FILES(pheno_meta_ch)

    // -------------------------------
    // Step 3 — Percentiles 
    // -------------------------------

    // Materialize PRS list once (safe fan-out in NF25)
    def prs_list_ch = prs_checked.prs_present.collect()

    // Percentile settings
    def percentile_groups = params.percentile_plot?.groups ?: 10
    def percentile_norm   = params.percentile_plot?.normalize ?: true

    // Build one PRS tuple per row (same pattern as Step 4)
    def prs_rows_percentile_ch = prs_list_ch
        .flatMap()
        .flatMap { csv_text -> csv_text.splitCsv(header:true, sep:';') }
        .map { row ->
            def prs_name  = row['"name"']?.replaceAll('"','')
            def full_path = row['"full_path"']?.replaceAll('"','')

            def prs_file        = full_path ? file(full_path) : null
            def prs_metadata    = file("${workflow.projectDir}/results/preprocessing/prs_present.csv")
            def phenotype_file = file("${workflow.projectDir}/results/preprocessing/phenotypes_valid.csv")
            def covariates_file = file("${workflow.projectDir}/${params.paths.covariates}")

            tuple(
                prs_file,
                prs_metadata,
                prs_name,
                phenotype_file,
                covariates_file,
                percentile_groups,
                percentile_norm
            )
        }

    // -------------------------------
    // Run percentiles (parallel per PRS)
    // -------------------------------
    COMPUTE_PRS_PERCENTILES(prs_rows_percentile_ch)


    // Convert regression_runs ArrayList into a proper channel emitting each map individually
    // Step 1: make prs_checked.prs_present a normal unicast channel
    def regression_runs = params.regression_runs ?: []
    def regression_runs_ch = Channel.fromList(regression_runs)

    // make a simple channel of PRS tuples (one per row)
    def prs_rows_ch = prs_checked.prs_present
        .flatMap { csv_text -> csv_text.splitCsv(header:true, sep:';') }
        .map { row ->
            def prs_name = row['"name"']?.replaceAll('"','')
            def full_path = row['"full_path"']?.replaceAll('"','')
            def prs_file = full_path ? file(full_path) : null
            def prs_metadata = file("${workflow.projectDir}/results/preprocessing/prs_present.csv")
            def phenotype_file = file("${workflow.projectDir}/results/preprocessing/phenotypes_valid.csv")
            def covariates_file = file("${workflow.projectDir}/${params.paths.covariates}")
            tuple(prs_file, prs_metadata, prs_name, phenotype_file, covariates_file)
        }

    // combine each PRS tuple with every regression run config
    def regressions_input_ch = prs_rows_ch
        .flatMap { prs_tuple ->
            regression_runs.collect { reg_params ->
                def (prs_file, prs_metadata, prs_name, phenotype_file, covariates_file) = prs_tuple
                tuple(
                    prs_file, prs_metadata, prs_name,
                    phenotype_file, covariates_file,
                    reg_params.groups ?: 10,
                    reg_params.include_intermediates ?: false,
                    reg_params.normalize ?: true,
                    reg_params.label ?: "regression"
                )
            }
        }

    // -------------------------------
    // Step 4. Run regressions
    // -------------------------------
    COMPUTE_PRS_REGRESSIONS(regressions_input_ch)
}