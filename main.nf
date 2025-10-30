#!/usr/bin/env nextflow
nextflow.enable.dsl=2

/*
 * ---------------------------
 *   PolyGenie Correlation Pipeline
 *   PRS ↔ Phenotype Association Analysis
 * ---------------------------
 */

// Use SnakeYAML
import org.yaml.snakeyaml.Yaml
//import groovy.csv.CsvParser

// Load configuration
params.config_file = params.config_file ?: "config/pipeline_config.yaml"
def configFile = file(params.config_file)
if (!configFile.exists()) {
    exit 1, "❌ Config file not found: ${params.config_file}"
}

def yaml = new Yaml().load(configFile.text)

// Merge YAML sections into params
params.paths         = yaml.paths
params.thresholds    = yaml.thresholds
params.prs           = yaml.prs
params.prevalence    = yaml.prevalence
params.covariates    = yaml.covariates

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
/*
include { PREPARE_INPUTS }  from './modules/prepare/prepare_inputs.nf'
include { NORMALIZE_PRS }   from './modules/normalize/normalize_prs.nf'
include { RUN_ASSOCIATIONS } from './modules/associations/run_associations.nf'
include { SUMMARIZE_RESULTS } from './modules/summarize/summarize_results.nf'
include { MERGE_TO_SQLITE } from './modules/merge/merge_to_sqlite.nf'
include { GENERATE_PLOTS }  from './modules/visualize/generate_plots.nf'
*/
/*
workflow {
    // -------------------------------------------------------------------------
    // Step 1: Check PRS files
    // -------------------------------------------------------------------------
    prs_meta_ch = Channel.fromPath(params.paths.prs_metadata)
    prs_checked = CHECK_PRS_FILES(prs_meta_ch)

    // -------------------------------------------------------------------------
    // Step 2: Check phenotype files
    // -------------------------------------------------------------------------
    pheno_meta_ch = Channel.fromPath(params.paths.phenotype_metadata)
    pheno_checked = CHECK_PHENOTYPE_FILES(pheno_meta_ch)

    // -------------------------------------------------------------------------
    // Step 3: Prepare channel for percentile computation
    // -------------------------------------------------------------------------
    // Wait for both checks to finish
    // PRS files channel
    // Canal con todos los archivos PRS en la carpeta
    prs_ch = prs_checked.prs_present
        .splitCsv(header: true)
        .map { row -> tuple(file(row.full_path), row.name) }

    // Paso 4: Obtener archivo filtrado de fenotipos
    pheno_meta_file_ch = pheno_checked.phenotypes_valid

    // Paso 5: Covariables
    cov_ch = Channel.value(file(params.paths.covariates))

    // Paso 6: Combinar cada PRS con los archivos constantes
    input_ch = prs_ch.map { prs_file, prs_name ->
        tuple(prs_file, prs_name, pheno_meta_file_ch.first(), cov_ch)
    }

    // -------------------------------------------------------------------------
    // Step 4: Compute PRS percentiles (parallel per PRS)
    // -------------------------------------------------------------------------
    COMPUTE_PRS_PERCENTILES(input_ch)

    /*if (params.normalize) {
        normalized_ch = NORMALIZE_PRS(manifest_ch)
    } else {
        normalized_ch = manifest_ch
    }

    assoc_ch  = RUN_ASSOCIATIONS(normalized_ch, params.phenotypes, params.covariates)
    summary_ch = SUMMARIZE_RESULTS(assoc_ch)
    db_ch      = MERGE_TO_SQLITE(summary_ch)
    GENERATE_PLOTS(db_ch)
    */
/*
    log.info "✅ Pipeline finished successfully!"
}*/
/*
workflow {

    // -------------------------------------------------------------------------
    // Step 1: Check PRS files
    // -------------------------------------------------------------------------
    prs_meta_ch = Channel.fromPath(params.paths.prs_metadata)
    prs_checked = CHECK_PRS_FILES(prs_meta_ch)

    // -------------------------------------------------------------------------
    // Step 2: Check phenotype files
    // -------------------------------------------------------------------------
    pheno_meta_ch = Channel.fromPath(params.paths.phenotype_metadata)
    pheno_checked = CHECK_PHENOTYPE_FILES(pheno_meta_ch)

    // -------------------------------------------------------------------------
    // Step 3: Compute PRS percentiles (parallel per PRS)
    // -------------------------------------------------------------------------
    prs_csv_files = prs_checked
    Channel
    .fromPath("${params.paths.output_dir}/preprocessing/prs_present.csv")
    .splitCsv(header:true)
    .map { row ->
    def prs_name = row.name
    def prs_file = file("${row.full_path}")   // only once
    def prs_metadata = file("${workflow.projectDir}/results/preprocessing/prs_present.csv")
    def phenotype_file = file("${workflow.projectDir}/results/preprocessing/phenotypes_valid.csv")
    def covariates_file = file("${workflow.projectDir}/${params.paths.covariates}")
    def percentiles = params.prevalence.percentiles

    println "DEBUG: ${prs_name}, ${prs_file}, ${phenotype_file}, ${covariates_file}"
    
    tuple(prs_file, prs_metadata, prs_name, phenotype_file, covariates_file, percentiles)
    }
    .set { prs_for_percentiles }  // store channel to feed process

    // Then, feed it into the process
    COMPUTE_PRS_PERCENTILES(prs_for_percentiles)
}
*/
workflow {

    // Step 1: Check PRS files
    prs_meta_ch = Channel.fromPath(params.paths.prs_metadata)
    prs_checked = CHECK_PRS_FILES(prs_meta_ch)

    // Step 2: Check phenotype files
    pheno_meta_ch = Channel.fromPath(params.paths.phenotype_metadata)
    pheno_checked = CHECK_PHENOTYPE_FILES(pheno_meta_ch)

    // Step 3: Compute PRS percentiles
    // Use outputs from the previous steps instead of reading the file from disk
    //prs_checked.prs_present
    //    .splitCsv(header:true, sep:';')
    //    .map { row ->
    //        println "DEBUG: name=${row['"name"']}, path=${row['"full_path"']}"
    //        row
    //    }

    
    
        // Step 3: Build channel for percentiles computation
    prs_checked.prs_present
        .splitCsv(header: true, sep: ';')
        .map { row ->
            // Extract fields safely
            def prs_name = row['"name"']?.replaceAll('"', '')
            def full_path = row['"full_path"']?.replaceAll('"', '')

            def prs_file = full_path ? file(full_path) : null
            def prs_metadata = file("${workflow.projectDir}/results/preprocessing/prs_present.csv")
            def phenotype_file = file("${workflow.projectDir}/results/preprocessing/phenotypes_valid.csv")
            def covariates_file = file("${workflow.projectDir}/${params.paths.covariates}")
            def percentiles = params.prevalence?.groups

            // 🔍 Debug print — show what's being emitted
            /*println """
            DEBUG:
            name            = ${prs_name}
            full_path       = ${full_path}
            prs_file exists = ${prs_file?.exists()}
            phenotype_file  = ${phenotype_file}
            covariates_file = ${covariates_file}
            percentiles     = ${percentiles}
            """.stripIndent()
            */

            // Return the tuple (will throw if any are null)
            tuple(prs_file, prs_metadata, prs_name, phenotype_file, covariates_file, percentiles)
        }
        // Optional: also inspect what the channel actually emits
        //.view { "EMITTING: ${it}" }
        .set { prs_for_percentiles }

    COMPUTE_PRS_PERCENTILES(prs_for_percentiles)


    COMPUTE_PRS_REGRESSIONS(prs_for_percentiles)
}