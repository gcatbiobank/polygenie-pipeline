import os
import sys
from pathlib import Path

import dash
from dash import Dash, html, dcc, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
import seaborn as sns
import matplotlib.colors as mcolors
import numpy as np

# Add project root to path so sqlitedb package is importable
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(root_dir)

try:
    from sqlitedb.db_handler import DBHandler
except Exception as e:
    raise RuntimeError("Failed to import DBHandler; ensure project root is on PYTHONPATH and sqlitedb exists") from e

import logging

# Instantiate DB handler
database_file = "sqlitedb/polygenie.db"
db_handler = DBHandler(database_file)

# Configure logging from environment variable VERBOSE or LOG_LEVEL
log_level = os.getenv('LOG_LEVEL') or ( 'DEBUG' if os.getenv('VERBOSE') else 'INFO')
logging.basicConfig(level=getattr(logging, log_level))
log = logging.getLogger(__name__)

log.info("Using DB file: %s", database_file)
if not os.path.exists(database_file):
    log.warning("DB file not found: %s", database_file)
else:
    try:
        gwas_names = db_handler.get_gwas_names()
        log.info("Found %d GWAS entries", len(gwas_names))
        log.debug("GWAS sample: %s", gwas_names[:10])
        log.debug("Tables present:\n%s", db_handler.list_tables().to_string(index=False))
        log.debug("DB summary counts: %s", db_handler.get_db_summary())
    except Exception:
        log.exception("Error while probing database")

# Minimal app (PRS visualization only)
app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
server = app.server

palette = sns.color_palette("colorblind")
colorblind_palette_hex = [mcolors.to_hex(c) for c in palette]

# Dropdown options
gwas_names = db_handler.get_gwas_names()
disease_options = [{'label': d, 'value': d} for d in gwas_names]

# Default (will be updated dynamically when a PRS is selected)
reference_options = [{'label': 'Bottom', 'value': 'low'}]

# We now expose the number of bins (n_groups) as a selectable option. Labels are friendly.
def format_bins_option(n):
    label = f"{n} bins"
    if n == 4:
        label = f"{n} (quartiles)"
    elif n == 10:
        label = f"{n} (deciles)"
    return {'label': label, 'value': str(n)}

division_options = [format_bins_option(4), format_bins_option(10)]

# Callback to refresh reference and bins options when a PRS is selected
@app.callback(
    [Output('reference-dropdown', 'options'), Output('reference-dropdown', 'value'),
     Output('division-dropdown', 'options'), Output('division-dropdown', 'value')],
    [Input('disease-dropdown', 'value')]
)
def update_reference_and_bins(disease_value):
    # default fallbacks
    ref_opts = [{'label': 'Bottom', 'value': 'low'}]
    ref_val = 'low'

    bins_opts = [format_bins_option(4), format_bins_option(10)]
    bins_val = '10'

    if not disease_value:
        return ref_opts, ref_val, bins_opts, bins_val

    gwas = db_handler.get_gwas_code_from_name(disease_value)
    try:
        includes = db_handler.get_prs_include_intermediates(gwas)
        if includes:
            ref_opts = [{'label': 'Bottom', 'value': 'low'}, {'label': 'Bottom and Middle', 'value': 'low + intermediate'}]
            # When include_intermediates is available, choose the 'low + intermediate' (rest) comparison by default
            ref_val = 'low + intermediate'
        else:
            ref_opts = [{'label': 'Bottom', 'value': 'low'}]
            ref_val = 'low'
    except Exception:
        ref_opts = [{'label': 'Bottom', 'value': 'low'}]
        ref_val = 'low'

    try:
        groups = db_handler.get_prs_n_groups(gwas)
        if groups:
            bins_opts = [format_bins_option(n) for n in sorted(groups)]
            bins_val = str(sorted(groups)[-1])
    except Exception:
        pass

    log.info("Updated reference options: %s, bins options: %s", ref_opts, bins_opts)
    return ref_opts, ref_val, bins_opts, bins_val

# Layout
app.layout = dbc.Container([
    html.H1("PolyGenie — Minimal PRS Visualization"),
    dbc.Row([
        dbc.Col([
            html.P('Select PRS:'),
            dcc.Dropdown(id='disease-dropdown', options=disease_options, placeholder='Select phenotype', value=(gwas_names[0] if gwas_names else None)),
            html.P('Reference Group:'),
            dcc.Dropdown(id='reference-dropdown', options=reference_options, value='low'),
            html.P('PRS Division:'),
            dcc.Dropdown(id='division-dropdown', options=division_options, value='10')
        ], width=3),
        dbc.Col([
            dcc.Tabs(id='tabs', value='icd', children=[
                dcc.Tab(label='ICD codes', value='icd'),
                dcc.Tab(label='Phecodes', value='phe'),
                dcc.Tab(label='Metabolites', value='met'),
                dcc.Tab(label='Other Variables', value='quest'),
            ]),
            dcc.Graph(id='correlations-graph'),
            html.H4('Prevalence by percentile'),
            dcc.Graph(id='prevalence-graph'),
            html.Hr(),
            html.H4('Top hits'),
            dash_table.DataTable(
                id='prs-table',
                columns=[
                    {'name': 'Code', 'id': 'Code'},
                    {'name': 'Description', 'id': 'description'},
                    {'name': 'Class', 'id': 'class'},
                    {'name': 'OR', 'id': 'OR', 'type': 'numeric', 'format': {'specifier': '.3f'}},
                    {'name': 'P', 'id': 'P', 'type': 'numeric', 'format': {'specifier': '.2e'}}
                ],
                page_size=10,
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left', 'padding': '5px'},
                style_header={'fontWeight': 'bold'},
            )
        ], width=9)
    ]),
    html.Hr(),
    dcc.Download(id='download-dataframe-excel'),
    dcc.Store(id='clicked-data-store')
], fluid=True)


def get_target_type(tab):
    # Map UI tabs to the database's target_class values. Use the exact
    # terminology present in the DB (e.g. 'ICD_codes') or fallbacks.
    if tab == 'met':
        return 'Metabolites'
    elif tab == 'icd':
        return 'ICD_codes'
    elif tab == 'phe':
        return 'Phecodes'
    elif tab == 'quest':
        return 'Other Variables'


@app.callback(
    Output('correlations-graph', 'figure'),
    [Input('disease-dropdown', 'value'), Input('reference-dropdown', 'value'), Input('division-dropdown', 'value'), Input('tabs', 'value')]
)
def update_graph(disease_value, reference_value, division_value, tab):
    """Render the canonical PRS plot from `app.py` but sourcing data from the SQL queries.

    This follows the visual and annotation choices in the full app (legend, FDR lines,
    outlier annotations, axis caps) while using `db_handler.get_correlations` as the
    data provider.
    """
    if not disease_value:
        return px.scatter(title='No GWAS selected')

    target_type = get_target_type(tab)
    if reference_value == 'low + intermediate':
        reference_value = 'rest'

    gwas = db_handler.get_gwas_code_from_name(disease_value)

    if isinstance(target_type, tuple):
        filtered_data = pd.concat([
            db_handler.get_correlations(gwas, reference_value, division_value, target_type[0]),
            db_handler.get_correlations(gwas, reference_value, division_value, target_type[1])
        ], ignore_index=True)
    else:
        filtered_data = db_handler.get_correlations(gwas, reference_value, division_value, target_type)

    # Ensure we have data
    if filtered_data.empty:
        return px.scatter(title='No data available')

    # Same filtering/ordering as the main app
    filtered_data = filtered_data.dropna(subset=['P', 'CI_5', 'CI_95'])
    filtered_data = filtered_data.sort_values(by=['class', 'logpxdir'], ascending=[True, True])

    x = 'description'
    y = 'logpxdir'
    title = ''
    color = 'class' if 'class' in filtered_data.columns else None

    unique_categories = filtered_data['class'].unique() if 'class' in filtered_data.columns else []
    color_map = {category: colorblind_palette_hex[i % len(colorblind_palette_hex)] for i, category in enumerate(unique_categories)}

    # Provide a lowercase code field for hover compatibility
    if 'Code' in filtered_data.columns and 'code' not in filtered_data.columns:
        filtered_data['code'] = filtered_data['Code']

    # Plot using the original app styling
    fig = px.scatter(filtered_data, x=x, y=y,
                     title=title,
                     color=color,
                     color_discrete_map=color_map,
                     template='plotly_white',
                     hover_data={
                         'code': True,
                         'description': True,
                         'class': True,
                         'OR': ':.2f',
                         'logpxdir': False,
                         'P': ':.2e',
                         'R2': ':.2f'
                     })

    # Add significance lines and annotations
    element_count = filtered_data['class'].nunique() if 'class' in filtered_data.columns else len(filtered_data)
    if element_count:
        positive_sig = -np.log10(0.05 / element_count)
        positive_sig_text = f"{positive_sig:.3f}"

        negative_sig = np.log10(0.05 / element_count)
        negative_sig_text = f"{negative_sig:.3f}"

        fig.add_shape(type='line', x0=0, x1=1, xref='paper', y0=positive_sig, y1=positive_sig, yref='y', line=dict(color='red', width=2, dash='dash'))
        fig.add_annotation(xref='paper', x=1, y=positive_sig, text=positive_sig_text, showarrow=False, font=dict(color='red', size=12), align='right', yshift=10)

        fig.add_shape(type='line', x0=0, x1=1, xref='paper', y0=negative_sig, y1=negative_sig, yref='y', line=dict(color='red', width=2, dash='dash'))
        fig.add_annotation(xref='paper', x=1, y=negative_sig, text=negative_sig_text, showarrow=False, font=dict(color='red', size=12), align='right', yshift=10)

        outliers = filtered_data[(filtered_data['logpxdir'] < negative_sig) | (filtered_data['logpxdir'] > positive_sig)]
        for index, row in outliers.iterrows():
            fig.add_annotation(x=row[x], y=row['logpxdir'], text=f"{row[x]}", showarrow=False, font=dict(color='black', size=12), align='center', yshift=10)

    # Cap y axis
    yvals = filtered_data['logpxdir'].abs().dropna()
    if len(yvals) > 0:
        ycap = max(1.0, float(np.nanpercentile(yvals, 99)))
        y_lim = ycap * 1.2
        fig.update_yaxes(range=[-y_lim, y_lim])

    # Layout matching main app
    fig.update_layout(xaxis_title='Diseases', yaxis_title='log10(p-value) × Effect size direction', xaxis_visible=False, xaxis_showticklabels=False, showlegend=True, height=600)

    # Baseline
    fig.add_shape(type='line', x0=0, x1=1, xref='paper', y0=0, y1=0, yref='y', line=dict(color='black', width=1))

    return fig


@app.callback(Output('clicked-data-store', 'data'), Input('correlations-graph', 'clickData'))
def update_clicked_data(clickData):
    # Store the clicked point's Code and description so the prevalence plot can use it
    if not clickData or 'points' not in clickData or len(clickData['points']) == 0:
        return None
    pt = clickData['points'][0]
    custom = pt.get('customdata') or []
    code = custom[0] if len(custom) > 0 else pt.get('x')
    desc = custom[1] if len(custom) > 1 else pt.get('text') or pt.get('hovertext') or pt.get('x')
    return {'code': code, 'description': desc}


@app.callback(Output('prevalence-graph', 'figure'), [Input('clicked-data-store', 'data'), Input('disease-dropdown', 'value')])
def update_prevalence(clicked_data, disease_value):
    # If no point clicked, show an informative placeholder
    if not clicked_data or not clicked_data.get('code'):
        return px.scatter(title='Click a point on the main plot to show prevalence by percentile')
    prs = db_handler.get_gwas_code_from_name(disease_value)
    target_code = clicked_data['code']
    prev = db_handler.get_prevalences(prs, target_code)
    if prev.empty:
        return px.scatter(title='No prevalence data available for selected target')
    # Melt prevalence for plotting
    plot_df = prev.melt(id_vars='percentile', value_vars=['prevalence_all','prevalence_female','prevalence_male'], var_name='sex', value_name='prevalence')
    # Friendly labels
    plot_df['sex_label'] = plot_df['sex'].map({'prevalence_all':'All','prevalence_female':'Female','prevalence_male':'Male'})
    fig = px.line(plot_df, x='percentile', y='prevalence', color='sex_label', markers=True, template='plotly_white')
    fig.update_layout(xaxis_title='Percentile', yaxis_title='Prevalence', height=300)
    return fig


# Callback to populate the PRS top-hits table (first-page style)
@app.callback(
    Output('prs-table', 'data'),
    [Input('disease-dropdown', 'value'), Input('reference-dropdown', 'value'), Input('division-dropdown', 'value'), Input('tabs', 'value')]
)
def update_table(disease_value, reference_value, division_value, tab):
    if not disease_value:
        return []
    target_type = get_target_type(tab)
    if reference_value == 'low + intermediate':
        reference_value = 'rest'
    gwas = db_handler.get_gwas_code_from_name(disease_value)
    if isinstance(target_type, tuple):
        df = pd.concat([
            db_handler.get_correlations(gwas, reference_value, division_value, target_type[0]),
            db_handler.get_correlations(gwas, reference_value, division_value, target_type[1])
        ], ignore_index=True)
    else:
        df = db_handler.get_correlations(gwas, reference_value, division_value, target_type)
    if df.empty:
        return []
    df = df.dropna(subset=['P', 'CI_5', 'CI_95'])
    # Round numeric columns
    numeric_columns = df.select_dtypes(include=['number']).columns
    df[numeric_columns] = df[numeric_columns].round(6)
    df = df.replace({pd.NA: None})
    # Return only the columns used in the table
    table_df = df[['Code', 'description', 'class', 'OR', 'P']]
    return table_df.to_dict('records')



if __name__ == '__main__':
    app.run_server(debug=True)
