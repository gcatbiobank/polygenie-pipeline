# about.py
import dash_bootstrap_components as dbc
from dash import html

layout = dbc.Container(
    [
        # Title
        html.H2("About PolyGenie", className="mb-4"),
        html.Hr(),

        # Section 1: What is PolyGenie?
        html.H4("What is PolyGenie?"),
        html.P(
            "PolyGenie is an interactive platform designed to explore phenome-wide associations "
            "between polygenic risk scores (PRS) and a wide range of phenotypes in the GCAT cohort. "
            "It enables researchers to investigate pleiotropic effects and shared genetic architecture "
            "across diseases, metabolites, and lifestyle or environmental traits."
        ),

        html.P(
            "The tool provides intuitive visualizations and statistical summaries that allow users "
            "to stratify individuals by PRS percentiles and examine disease prevalence and association strength."
        ),

        html.Hr(),

        # Section 2: Methodology + Diagram
        html.H4("How It Works"),
        html.P(
            "PRS are computed from publicly available GWAS summary statistics using the MegaPRS method. "
            "Phenome-wide association scans are then conducted within the GCAT cohort, adjusting for demographic and genetic covariates. "
            "The platform supports dynamic comparisons between PRS groups and a wide range of phenotypic variables."
        ),
        html.P(
            "Results are visualized using PheWAS-style plots and PRS percentile vs. phenotype prevalence curves, "
            "and are backed by a MySQL database for fast interaction."
        ),


        html.Img(
            src="/assets/polygenie-schema.png",  # <- Your schematic image
            style={"maxWidth": "100%", "borderRadius": "8px", "boxShadow": "0 0 10px rgba(0,0,0,0.1)"}
        ),
            html.Small("Figure: PolyGenie data processing and analysis workflow.", className="text-muted"),

        html.Hr(),

        # Section 3: Contact & Citation
        html.H4("Contact and Citation"),
        html.P("PolyGenie is developed and maintained by researchers at GCAT | Genomes for Life, Institut Germans Trias i Pujol."),
        html.P([
            "For questions or feature suggestions, contact us at ",
            html.A("", href=""),
            "."
        ]),
        html.P([
            "GitHub: ",
            html.A("", href="", target="_blank")
        ]),
        html.P("If you use PolyGenie in your research, please cite our upcoming application note (in preparation)."),
    ],
    className="mt-4 mb-5"
)

