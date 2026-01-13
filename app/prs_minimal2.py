import os
import sys
import logging
from pathlib import Path

import dash
from dash import Dash, html, dcc, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.colors as mcolors

# Ensure project root is importable
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(root_dir)

from sqlitedb.db_handler import DBHandler

# Logging
log_level = os.getenv('LOG_LEVEL') or ('DEBUG' if os.getenv('VERBOSE') else 'INFO')
logging.basicConfig(level=getattr(logging, log_level))
log = logging.getLogger(__name__)

# Instantiate DB
database_file = 'sqlitedb/polygenie.db'
db = DBHandler(database_file)

# App
app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
server = app.server

palette = sns.color_palette('colorblind')
colorblind_palette_hex = [mcolors.to_hex(c) for c in palette]

# Controls
gwas_names = db.get_gwas_names()
disease_options = [{'label': d, 'value': d} for d in gwas_names]

reference_options = [
    {'label': 'Bottom', 'value': 'low'},
    {'label': 'Bottom and Middle', 'value': 'rest'},
]

# Default division options (will be updated based on PRS when possible)
division_options = [{'label': '4 (quartiles)', 'value': '4'}, {'label': '10 (deciles)', 'value': '10'}]

# Build dynamic tabs from the DB's target classes
_tc_df = db._query("""
SELECT DISTINCT target_class
FROM target
WHERE target_class IS NOT NULL
  AND TRIM(target_class) != ''
ORDER BY target_class
""")

target_classes = (
    _tc_df['target_class'].astype(str).tolist()
    if not _tc_df.empty
    else ['Phecodes','ICD_codes','Metabolites','Other Variables']
)

tabs_children = [dcc.Tab(label=tc, value=tc) for tc in target_classes]
default_tab = target_classes[0] if target_classes else 'ICD_codes'

# Layout: Only Phewas (Phecodes) and prevalence + table
app.layout = dbc.Container([
    html.H1('PolyGenie — Minimal PRS (Phewas + Prevalence)'),
    dbc.Row([
        dbc.Col([
            html.P('Select PRS:'),
            dcc.Dropdown(id='disease-dropdown', options=disease_options, placeholder='Select PRS', value=(gwas_names[0] if gwas_names else None)),
            html.P('Reference:'),
            dcc.Dropdown(id='reference-dropdown', options=reference_options, value='low'),
            html.P('Division (n groups):'),
            dcc.Dropdown(id='division-dropdown', options=division_options, value='10')
        ], width=3),
        dbc.Col([
            dcc.Tabs(
                id='tabs',
                value=default_tab,
                children=tabs_children
            ),
            dcc.Graph(id='phewas-graph', config={'displayModeBar': False}, style={'height':'650px'}),
            html.Hr(),
            html.H4('Prevalence by percentile'),
            dcc.Graph(id='prevalence-graph', config={'displayModeBar': False}, style={'height':'320px'}),
            html.Hr(),
            html.H4('Top hits'),
            dash_table.DataTable(
                id='prs-table',
                columns=[
                    {'name': 'Code', 'id': 'Code'},
                    {'name': 'Description', 'id': 'description'},
                    {'name': 'Class', 'id': 'class'},
                    {'name': 'OR', 'id': 'OR', 'type': 'numeric'},
                    {'name': 'P', 'id': 'P', 'type': 'numeric'},
                ],
                page_size=10,
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left', 'padding': '5px'},
                style_header={'fontWeight': 'bold'},
            )
        ], width=9),
    ]),
    dcc.Store(id='clicked-data-store')
], fluid=True)


def get_target_class_for_phewas(prs_name=None):
    """Choose a sensible target_class for the Phewas plot.

    Preference order: any class that contains 'phecode' (case-insensitive),
    otherwise any class that contains 'icd', otherwise pick the first class found
    for the supplied PRS. If no PRS given or no classes found, fall back to 'Phecodes'.
    """
    if not prs_name:
        return 'Phecodes'
    try:
        df = db._query("SELECT DISTINCT t.target_class FROM target t JOIN phewas_result p ON p.target_code = t.target_code WHERE p.prs_name = ?", (prs_name,))
        classes = [c for c in df['target_class'].dropna().unique().tolist()] if not df.empty else []
        log.debug("Available classes for %s: %s", prs_name, classes)
        # prefer classes that look like phecodes
        for c in classes:
            if 'phecode' in str(c).lower():
                return c
        for c in classes:
            if 'icd' in str(c).lower():
                return c
        # otherwise, return the first available class
        if classes:
            return classes[0]
    except Exception:
        log.exception("Could not determine target_class for PRS: %s", prs_name)
    # default fallback
    return 'Phecodes'




@app.callback(
    Output('division-dropdown', 'options'), Output('division-dropdown', 'value'),
    Input('disease-dropdown', 'value')
)
def update_divisions(prs_display_name):
    if not prs_display_name:
        return division_options, '10'
    prs = db.get_gwas_code_from_name(prs_display_name)
    groups = db.get_prs_n_groups(prs)
    if not groups:
        return division_options, '10'
    opts = [{'label': f"{n} bins", 'value': str(n)} for n in sorted(groups)]
    return opts, str(sorted(groups)[-1])


@app.callback(
    Output('reference-dropdown','options'), Output('reference-dropdown','value'),
    Input('disease-dropdown','value')
)
def update_reference_options(prs_display_name):
    """Update Reference dropdown to include 'Bottom and Middle' when PRS runs include intermediates."""
    base = [{'label': 'Bottom', 'value': 'low'}]
    if not prs_display_name:
        return base, 'low'
    prs = db.get_gwas_code_from_name(prs_display_name)
    try:
        if db.get_prs_include_intermediates(prs):
            opts = base + [{'label': 'Bottom and Middle', 'value': 'rest'}]
            return opts, 'rest'
    except Exception:
        # If something goes wrong, fall back to base option
        pass
    return base, 'low'

@app.callback(
    Output('phewas-graph', 'figure'),
    [Input('disease-dropdown', 'value'), Input('reference-dropdown', 'value'), Input('division-dropdown', 'value'), Input('tabs', 'value')]
)
def update_phewas(prs_display_name, reference_value, division_value, tab):
    """Use the plotting code from `old/app.py` but allow tab-based selection of target class."""
    if not prs_display_name:
        return px.scatter(title='Select PRS')
    prs = db.get_gwas_code_from_name(prs_display_name)
    # Determine target class preference: tab overrides auto-detection; tabs carry exact DB target_class names
    if tab:
        target_type = tab
    else:
        target_type = get_target_class_for_phewas(prs)
    log.debug("Using target_type '%s' for PRS %s (tab=%s)", target_type, prs, tab)

    # Fetch data (allow for target_type being a tuple)
    if isinstance(target_type, tuple):
        df = pd.concat([
            db.get_correlations(prs, reference_value, division_value, target_type[0]),
            db.get_correlations(prs, reference_value, division_value, target_type[1])
        ], ignore_index=True)
    else:
        df = db.get_correlations(prs, reference_value, division_value, target_type)
    if df.empty:
        return px.scatter(title='No data available')

    # same processing as full app
    df = df.dropna(subset=['P', 'CI_5', 'CI_95'])
    df = df.sort_values(by=['class', 'domain', 'logpxdir'], ascending=[True, True, True]).reset_index(drop=True)

    # map each row to an integer x position so we can place domain separators precisely
    df['xpos'] = df.index.astype(float)
    x = 'xpos'
    y = 'logpxdir'

    unique_categories = df['domain'].unique() if 'domain' in df.columns else []
    color_map = {category: colorblind_palette_hex[i % len(colorblind_palette_hex)] for i, category in enumerate(unique_categories)}

    # Add lowercase code for hover
    if 'Code' in df.columns and 'code' not in df.columns:
        df['code'] = df['Code']

    # Build scatter on numeric x so domain separators (vertical lines) can be placed at fractional positions
    fig = px.scatter(df, x=x, y=y, color='domain', color_discrete_map=color_map, template='plotly_white',
                     custom_data=['Code','description','domain'],
                     hover_data={'description': True, 'OR': ':.2f', 'logpxdir': False, 'P': ':.2e', 'domain': True})


    # FDR-style lines and annotations copied from old app
    element_count = df['class'].nunique() if 'class' in df.columns else len(df)
    if element_count:
        positive_sig = -np.log10(0.05 / element_count)
        negative_sig = np.log10(0.05 / element_count)
        fig.add_shape(type='line', x0=0, x1=1, xref='paper', y0=positive_sig, y1=positive_sig, yref='y', line=dict(color='red', width=2, dash='dash'))
        fig.add_annotation(xref='paper', x=1, y=positive_sig, text=f"{positive_sig:.3f}", showarrow=False, font=dict(color='red', size=12), align='right', yshift=10)
        fig.add_shape(type='line', x0=0, x1=1, xref='paper', y0=negative_sig, y1=negative_sig, yref='y', line=dict(color='red', width=2, dash='dash'))
        fig.add_annotation(xref='paper', x=1, y=negative_sig, text=f"{negative_sig:.3f}", showarrow=False, font=dict(color='red', size=12), align='right', yshift=10)

        outliers = df[(df['logpxdir'] < negative_sig) | (df['logpxdir'] > positive_sig)]
        for index, row in outliers.iterrows():
            # place annotation at numeric x position but label with human-readable description
            xpos_val = row['xpos'] if 'xpos' in row else row[x]
            desc = row.get('description', '')
            fig.add_annotation(x=xpos_val, y=row['logpxdir'], text=f"{desc}", showarrow=False, font=dict(color='black', size=12), align='center', yshift=10)

    # Cap y-axis
    yvals = df['logpxdir'].abs().dropna()
    if len(yvals) > 0:
        ycap = max(1.0, float(np.nanpercentile(yvals, 99)))
        y_lim = ycap * 1.2
        fig.update_yaxes(range=[-y_lim, y_lim])

    fig.update_layout(
            xaxis_title='Diseases',
            yaxis_title='log10(p-value) × Effect size direction',
            xaxis_visible=False,
            xaxis_showticklabels=False,
            showlegend=False,
            autosize=False,
            height=600,
            margin=dict(l=40, r=40, t=40, b=80)
        )

    # baseline
    fig.add_shape(type='line', x0=0, x1=1, xref='paper', y0=0, y1=0, yref='y', line=dict(color='black', width=1))

    return fig


@app.callback(Output('clicked-data-store', 'data'), Input('phewas-graph', 'clickData'))
def store_clicked(clickData):
    if not clickData or 'points' not in clickData or len(clickData['points']) == 0:
        return None
    pt = clickData['points'][0]
    custom = pt.get('customdata') or []
    code = custom[0] if len(custom) > 0 else pt.get('x')
    desc = custom[1] if len(custom) > 1 else (pt.get('text') or code)
    try:
        # Ensure serializable strings
        code = str(code)
    except Exception:
        code = None
    try:
        desc = str(desc)
    except Exception:
        desc = None
    return {'code': code, 'description': desc}


@app.callback(Output('prevalence-graph', 'figure'), [Input('clicked-data-store', 'data'), Input('disease-dropdown', 'value')])
def update_prevalence(clicked, disease_value):
    if not clicked or not clicked.get('code'):
        return px.scatter(title='Click a point on the main plot to show prevalence by percentile')
    prs = db.get_gwas_code_from_name(disease_value)
    prev = db.get_prevalences(prs, clicked['code'])
    if prev.empty:
        return px.scatter(title='No prevalence data available for selected target')
    plot_df = prev.melt(id_vars='percentile', value_vars=['prevalence_all', 'prevalence_female', 'prevalence_male'], var_name='sex', value_name='prevalence')
    plot_df['sex_label'] = plot_df['sex'].map({'prevalence_all': 'All', 'prevalence_female': 'Female', 'prevalence_male': 'Male'})
    fig = px.line(plot_df, x='percentile', y='prevalence', color='sex_label', markers=True, template='plotly_white')
    fig.update_layout(xaxis_title='Percentile', yaxis_title='Prevalence', autosize=False, height=300, margin=dict(l=40, r=40, t=20, b=40))
    return fig


@app.callback(Output('prs-table', 'data'), [Input('disease-dropdown', 'value'), Input('reference-dropdown', 'value'), Input('division-dropdown', 'value'), Input('tabs', 'value')])
def update_table(disease_value, reference_value, division_value, tab):
    if not disease_value:
        return []
    prs = db.get_gwas_code_from_name(disease_value)
    # choose target_type directly from tab if supplied
    if tab:
        target_type = tab
    else:
        target_type = get_target_class_for_phewas(prs)
    log.debug("Table query using target_type '%s' for PRS %s (tab=%s)", target_type, prs, tab)
    df = db.get_correlations(prs, reference_value, division_value, target_type)
    if df.empty:
        return []
    df = df.dropna(subset=['P', 'CI_5', 'CI_95'])
    numeric_columns = df.select_dtypes(include=['number']).columns
    df[numeric_columns] = df[numeric_columns].round(6)
    df = df.replace({pd.NA: None})
    table_df = df[['Code', 'description', 'class', 'OR', 'P']]
    return table_df.to_dict('records')


if __name__ == '__main__':
    app.run_server(debug=True)
