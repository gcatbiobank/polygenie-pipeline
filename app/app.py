import dash
from dash import Dash, html, dcc, Input, Output, State, no_update
import dash_bootstrap_components as dbc
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import seaborn as sns
from dash import dash_table
import statsmodels.api as sm
import matplotlib.colors as mcolors
import sys
import os
from .about import layout as about_page_layout

# Get the root directory (two levels up from the app.py file)
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the root directory to sys.path
sys.path.append(root_dir)

try:
    from sqlitedb.db_handler import DBHandler
except ModuleNotFoundError as e:
    raise ModuleNotFoundError(
        "sqlitedb package not found. Make sure `sqlitedb/db_handler.py` exists and the project root is on PYTHONPATH.\n"
        "If you just added the DB handler, run `git status` to verify and restart the app."
    ) from e

# Create a connection to the SQLite database
database_file = "sqlitedb/polygenie.db"
# instantiate handler (DB file may not yet exist; the handler methods handle missing data gracefully)
db_handler = DBHandler(database_file)

# Create the Dash app
app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY, '/assets/style.css'], suppress_callback_exceptions=True)
server = app.server

app.title = "PolyGenie"
print("App title is:", app.title)


# Create dropdown options
gwas_names = db_handler.get_gwas_names()
disease_options = [{'label': disease, 'value': disease} for disease in gwas_names]

# Rename the labels from the dropdown
ref_values = ['low', 'low + intermediate']
ref_labels = ['Bottom', 'Bottom and Middle']

reference_options = [{'label': label, 'value': value} for label, value in zip(ref_labels, ref_values)]

div_values = ['quartile', 'decile']
div_labels = ['Quartiles', 'Deciles']

division_options = [{'label': label, 'value': value} for label, value in zip(div_labels, div_values)]

# Color palette definition
palette = sns.color_palette("colorblind")
colorblind_palette_hex = [mcolors.to_hex(color) for color in palette]

# Color palette graphs (Male, Female, All)
colors = ["#90BAAD", "#FF6542", "#56667A"]

col_headers = ['GWAS_code', "Code", 'Reference', 'Division', 'OR', 'CI_5', 'CI_95', 'P', 'R2', 'logpxdir', 'Description', 'Class', 'Type', 'GWAS']
col_headers_tokeep = ['GWAS', "Code", 'Reference', 'Division', 'OR', 'CI_5', 'CI_95', 'P', 'R2', 'Description', 'Class', 'Type']

#####################################################################################################################
##################################################### Callbacks #####################################################
#####################################################################################################################

# Callback to update the graph based on the selected tab and dropdowns
@app.callback(
    Output('correlations-graph', 'figure'),
    [Input('disease-dropdown', 'value'),
     Input('reference-dropdown', 'value'),
     Input('division-dropdown', 'value'),
     Input('tabs', 'value')],
)
def update_graph(disease_value, reference_value, division_value, tab):
    """
    Callback function to update the graph contents

    :param disease_value: condition selected on the disease field of the filters.
    :param quartile_value: quartile selected on the quartile field of the filters.
    :param reference_value: reference selected on the reference field of the filters.
    :param division_value: division selected on the division field of the filters.
    :param tab: inidcates the active tab (to know which graph has to be shown).
    :return: figure with the updated graph content
    """
    
    target_type = get_target_type(tab)
    if reference_value == "low + intermediate": reference_value = "rest"

    gwas = db_handler.get_gwas_code_from_name(disease_value)

    if isinstance(target_type, tuple): filtered_data = pd.concat([db_handler.get_correlations(gwas, reference_value, division_value, target_type[0]),
                                                        db_handler.get_correlations(gwas, reference_value, division_value, target_type[1])], ignore_index=True)
    else: filtered_data = db_handler.get_correlations(gwas, reference_value, division_value, target_type)

    filtered_data = filtered_data.dropna(subset=['P', 'CI_5', 'CI_95'])
    filtered_data = filtered_data.sort_values(by=['class', 'logpxdir'], ascending=[True, True])

    # Plotly figure based on filtered data
    x = 'description'
    y = 'logpxdir'
    title = (
    '' # XFR: I removed the title since it does not provide any useful info
        #'Metabolites vs logpxdir' if tab == 'met' 
        #else 'Variable vs. logpxdir' if tab == 'quest' 
        #else 'Diseases vs. logpxdir'
    )
    color = 'class'

    unique_categories = filtered_data['class'].unique()
    color_map = {category: colorblind_palette_hex[i % len(colorblind_palette_hex)] for i, category in enumerate(unique_categories)}
 
    filtered_data = filtered_data.rename(columns={'target':'code'})
    fig = px.scatter(filtered_data, x=x, y=y,
                title=title,
                color= color,
                color_discrete_map=color_map,
                template="plotly_white",
                hover_data={
                    'code': True, #Show target code
                    'description': True,  # Show the description
                    'class': True,  # Hide class if it's not needed on hover
                    'odds_ratio': ':.2f',  # Odds Ratio, formatted to 2 decimal places
                    'logpxdir': False,  # Hide logpxdir if not necessary
                    'P': ':.2e',
                    'R2': ':.2f' 
                } 
            )
    
    # Get the number of rows
    element_count = filtered_data['class'].nunique()

    if element_count:

        positive_sig = -np.log10(0.05/element_count)
        positive_sig_text = f"{positive_sig:.3f}"

        negative_sig = np.log10(0.05/element_count)
        negative_sig_text = f"{negative_sig:.3f}"

        # Add the positive significance line
        fig.add_shape(
            type="line",
            x0=0,
            x1=1,
            xref='paper',
            y0=positive_sig,
            y1=positive_sig,
            yref='y',
            line=dict(
                color="red",
                width=2,
                dash="dash",
            ),
        )

        # Add a label to the significance line
        fig.add_annotation(
            xref="paper", 
            x=1, 
            y=positive_sig, 
            text=positive_sig_text, 
            showarrow=False, 
            font=dict(
                color="red",
                size=12
            ),
            align="right",
            yshift=10
        )

        # Add the negative significance line
        fig.add_shape(
            type="line",
            x0=0,
            x1=1,
            xref='paper',
            y0=negative_sig,
            y1=negative_sig,
            yref='y',
            line=dict(
                color="red",
                width=2,
                dash="dash",
            ),
        )

        # Add a label to the significance line
        fig.add_annotation(
            xref="paper", 
            x=1, 
            y=negative_sig, 
            text=negative_sig_text, 
            showarrow=False, 
            font=dict(
                color="red",
                size=12
            ),
            align="right",
            yshift=10
        )

        
        # Filter data points outside thresholds
        outliers = filtered_data[(filtered_data['logpxdir'] < negative_sig) | (filtered_data['logpxdir'] > positive_sig)]

        # Add annotations for outliers
        for index, row in outliers.iterrows():
            fig.add_annotation(
                x=row[x], 
                y=row['logpxdir'],
                text=f"{row[x]}",
                showarrow=False,
                font=dict(
                    color="black",
                    size=12
                ),
                align="center",
                yshift=10
            )
        
    xname = (
        'Metabolites' if tab == 'met'
        else 'Variables' if tab == 'quest'
        else 'Diseases'
    )

    # Update layout
    fig.update_layout(
        xaxis_title=xname,
        yaxis_title='log10(p-value) × Effect size direction',
        xaxis_visible=False,
        xaxis_showticklabels=False,
        showlegend=False
    ),

    # Add a black line at y=0
    fig.add_shape(
        type="line",
        x0=0,
        x1=1,
        xref='paper',
        y0=0,
        y1=0,
        yref='y',
        line=dict(
            color="black",
            width=1,
            ),
    )
    return fig

# Callback to update the prs table based on the selected filters
@app.callback(
    [Output('prs-table-content', 'data'),  # Dash DataTable expects 'data' as list of dicts
     Output('table-stored-data', 'data')],
    [Input('disease-dropdown', 'value'),
     Input('reference-dropdown', 'value'),
     Input('division-dropdown', 'value'),
     Input('tabs', 'value')]
)
def update_table(disease_value, reference_value, division_value, tab):
    """
    Callback function to update the content of the interactive DataTable and store filtered data.
    """
    target_type = get_target_type(tab)
    if reference_value == "low + intermediate": 
        reference_value = "rest"

    # Example: Fetching filtered data
    gwas = db_handler.get_gwas_code_from_name(disease_value)
    
    if isinstance(target_type, tuple): filtered_data = pd.concat([db_handler.get_correlations(gwas, reference_value, division_value, target_type[0]),
                                                        db_handler.get_correlations(gwas, reference_value, division_value, target_type[1])], ignore_index=True)
    else: filtered_data = db_handler.get_correlations(gwas, reference_value, division_value, target_type)

    filtered_data = filtered_data.dropna(subset=['P', 'CI_5', 'CI_95'])
    # Round numeric columns to 6 decimal places
    numeric_columns = filtered_data.select_dtypes(include=[np.number]).columns
    filtered_data[numeric_columns] = filtered_data[numeric_columns].round(6)

    # Ensure all data types are JSON serializable
    filtered_data = filtered_data.replace({np.nan: None})  # Replace NaN values with None for JSON compatibility
    filtered_data.columns = col_headers
    filtered_data = filtered_data[['GWAS', "Code", 'Reference', 'Division', 'OR', 'CI_5', 'CI_95', 'P', 'R2', 'Description', 'Class']] # TODO: Need a more elegant solution

    # Convert DataFrame to list of dictionaries for DataTable
    data_store = filtered_data.to_dict('records')

    return data_store, data_store  # Populate dash_table.DataTable and store data

# Callback to handle file download
@app.callback(
    Output("download-dataframe-excel", "data"),
    Input("download-button", "n_clicks"),
    State("table-stored-data", "data"),
    prevent_initial_call=True
)
def download_table(n_clicks, stored_data):
    """
    #Callback to download the table as an Excel file.
    """
    if not stored_data:
        return None

    # Convert stored data (list of dicts) back to DataFrame
    df = pd.DataFrame(stored_data)

    def to_excel(bytes_io):
        with pd.ExcelWriter(bytes_io, engine="xlsxwriter") as writer:
            df.to_excel(writer, sheet_name="Sheet1", index=False)
    return dcc.send_bytes(to_excel, "polygenie-table_data.xlsx")

def filter_values(unfiltered_data, disease_value, quartile_value, reference_value, division_value):
    """
    Function to filter the data according to the content of the filters

    :param unfiletered_data: original dataset
    :param disease_value: condition selected on the disease field of the filters.
    :param quartile_value: quartile selected on the quartile field of the filters.
    :param reference_value: reference selected on the reference field of the filters.
    :param division_value: division selected on the division field of the filters.
    :return: dataset with the filtered data
    """
    filtered_data = unfiltered_data.copy()
    if reference_value == "low + intermediate": reference_value = "rest" #TODO: fix this


     # Apply filters based on dropdown values
    if disease_value:
        filtered_data = filtered_data[filtered_data['score'] == disease_value]
    if quartile_value:
        filtered_data = filtered_data[filtered_data['Quartile'] == quartile_value]
    if reference_value:
        filtered_data = filtered_data[filtered_data['reference'] == reference_value]
    if division_value:
        filtered_data = filtered_data[filtered_data['division'] == division_value]

    return filtered_data

# Callback to change metadata info
@app.callback(
    Output('graph-footer', 'children'),
    [Input('disease-dropdown', 'value')]
)
def update_graph_footer(target_gwas):
    """
    Callback function to update the graph footer depending on the selected condition.

    :param target_gwas: name of the condition selected.
    :return: formatted text containing the metadata to show on the footer.
    """  

    # Load the result into a Pandas DataFrame
    df = db_handler.get_gwas_metadata(target_gwas)

    # Check if we got any result
    if not df.empty:
        # Extract the data from the DataFrame
        row = df.iloc[0] 
        
        # Retrieve date information from metadata
        date_info = row['date']
        link_p = row['link_paper']
        link_s = row['link_sumstats']
        population = row['population']
        n = row['n']

        # Create a clickable link
        parts = [f"GWAS information. Sources: "]

        if not pd.isna(link_p):
            parts.append(html.A("Paper", href=link_p, target='_blank'))
        if not pd.isna(link_s):
            if len(parts) > 1:
                parts.append(", ")
            parts.append(html.A("GWAS summary statistics", href=link_s, target='_blank'))

        # Add population and n information
        parts.append(html.Br())  # Add a line break
        parts.append(f"Population: {population}, N: {n}")

        return html.Div(parts)

    else:
        return "No metadata available for the selected GWAS."

# Callback to save clicked point data
@app.callback(
    Output('clicked-data-store', 'data'),
    Input('correlations-graph', 'clickData')
)
def update_clicked_data(clickData):
    if clickData:
        return {'name': clickData['points'][0].get('x')}
    return no_update

# Callback to update statistics title
@app.callback(
    Output('target-statistics-title', 'children'),
    [Input('clicked-data-store', 'data'),
     State('tabs', 'value')]
)
def update_statistics_title(clicked_data, tab):
    if tab == 'met': return html.H2("Target Statistics", className="section-heading")
    if clicked_data and 'name' in clicked_data:
        return html.H2(f"Target Statistics: {clicked_data['name']}", className="section-heading")
    return html.H2("Target Statistics", className="section-heading")

# Callback to update target information box
@app.callback(
    Output('target-information-box', 'children'),
    [Input('clicked-data-store', 'data'),
     State('tabs', 'value')]
)
def update_basic_statistics(clicked_data, tab):
    # Define a reusable component for the default message
    def default_message():
        return html.Div([
            html.H2("Target Information"),
            html.P("Select a Phecode or ICD code from the graph")
        ], className="info-box")

    # Return the default message if the 'met' tab is selected
    if tab == 'met' or tab == 'quest':
        return default_message()

    # Check if clicked_data contains necessary information
    if not clicked_data or 'name' not in clicked_data:
        return default_message()

    target_desc = clicked_data['name']

    # Execute queries and load results into DataFrames
    all_individuals = db_handler.get_indiv_stats()
    target_individuals = db_handler.get_indiv_stats_for_target(target_desc)

    # Ensure data is not empty
    if all_individuals.empty or target_individuals.empty:
        return default_message()

    # Extract relevant data
    all_row = all_individuals.iloc[0]
    target_row = target_individuals.iloc[0]

    total_individuals = all_row['total_individuals']
    total_males = all_row['total_males']
    total_females = all_row['total_females']

    individuals_with_target = target_row['individuals_with_target']
    males_with_target = target_row['males_with_target']
    females_with_target = target_row['females_with_target']

    # Calculate percentages safely
    general_percentage = (individuals_with_target / total_individuals) * 100 if total_individuals > 0 else 0
    males_percentage = (males_with_target / total_males) * 100 if total_males > 0 else 0
    females_percentage = (females_with_target / total_females) * 100 if total_females > 0 else 0

    # Create a DataFrame for the table
    table_data = pd.DataFrame({
        'Category': ['All', 'Males', 'Females'],
        'Total n': [total_individuals, total_males, total_females],
        'With the phenotype': [individuals_with_target, males_with_target, females_with_target],
        'Percentage': [f"{general_percentage:.2f}%", f"{males_percentage:.2f}%", f"{females_percentage:.2f}%"]
    })

    # Generate the table
    table = dash_table.DataTable(
        data=table_data.to_dict('records'),
        columns=[{'name': i, 'id': i} for i in table_data.columns],
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'center', 'padding': '10px'},
        style_header={'fontWeight': 'bold'},
        page_size=10
    )
    
    # Add the redirect button
    button = html.Button("View in Cohort", id='redirect-button', n_clicks=0, className='button')

    return html.Div([
        html.H2(f"Statistics for {target_desc}"),
        html.Br(),
        table,
        html.Br(),
        button  # Add the button here
    ], className="info-box")

# Callback to update the prevalences graph
@app.callback(
    Output('prevalences-graph', 'figure'),
    [Input('disease-dropdown', 'value'),
    Input('clicked-data-store', 'data'),
    State('tabs', 'value')]
)
def update_prevalences_graph(disease_value, target, tab):

    target_type = get_target_type(tab)

    try:
        target_id = db_handler.get_target_code(target['name'], target_type)
        gwas = db_handler.get_gwas_code_from_name(disease_value)
        df = db_handler.get_prevalences(gwas, target_id)

        # Check if data is available
        if df.empty:
            return px.scatter(title="Select a Phecode or ICD code from the graph")

        # Melt the DataFrame to have a long format suitable for Plotly
        df = df.rename(columns={'prevalence_all':'All', 'prevalence_male':'Male', 'prevalence_female':'Female'})
        df_melted = df.melt(id_vars='percentile', value_vars=['All', 'Female', 'Male'],
                            var_name='Sex', value_name='Prevalence')

        # Create the Plotly figure
        fig = px.scatter(df_melted, x='percentile', y='Prevalence', color='Sex',
                        title=f"{target_id} - {target['name']} - Prevalence by Percentile".title(),
                        labels={'percentile': 'Percentile', 'Prevalence': 'Prevalence'},
                        color_discrete_map={'All': colors[0], 'Female': colors[1], 'Male': colors[2]},
                        opacity=0.4,
                        )
        
        # Update the scatter traces to hide Female and Male points by default
        fig.for_each_trace(lambda trace: trace.update(visible='legendonly'))
        
        # Define a function to compute LOESS and add to the plot
        def add_loess_line(df, percentile_col, prevalence_col, color, name, visible='legendonly', frac=0.3):
            loess = sm.nonparametric.lowess(df[prevalence_col], df[percentile_col], frac=frac)
            loess_x = loess[:, 0]
            loess_y = loess[:, 1]
            
            fig.add_trace(go.Scatter(x=loess_x, y=loess_y, mode='lines',
                                    name=name,
                                    line=dict(color=color, width=3),
                                    showlegend=True,
                                    visible=visible))

        # Apply LOESS for each prevalence category
        add_loess_line(df_melted[df_melted['Sex'] == 'All'], 'percentile', 'Prevalence',
                    color=colors[0], name='LOESS All', visible=True, frac=0.3)
        add_loess_line(df_melted[df_melted['Sex'] == 'Female'], 'percentile', 'Prevalence',
                    color=colors[1], name='LOESS Female', visible='legendonly', frac=0.3)
        add_loess_line(df_melted[df_melted['Sex'] == 'Male'], 'percentile', 'Prevalence',
                    color=colors[2], name='LOESS Male', visible='legendonly', frac=0.3)

        # Customize the layout to only show points in the legend
        fig.update_traces(showlegend=True, selector=dict(mode='lines'))
        fig.update_traces(showlegend=True, selector=dict(mode='markers'))

        fig.update_layout(
            xaxis_title=f'Percentile (risk score for {disease_value})',
            yaxis_title='Prevalence (%)',
            template="plotly_white",
        )

    except UnboundLocalError:
        return px.scatter(title="Select a Phecode or ICD code from the graph")
    except TypeError:
        return px.scatter(title="Select a Phecode or ICD code from the graph")

    
    return fig

def get_target_type(tab):
    if (tab == 'met'):
        return 'Metabolite'
    elif (tab == 'icd'):
        return 'ICD code'
    elif (tab == 'phe'):
        return 'Phecode'
    elif (tab == 'quest'):
        return ('binary', 'continuous')

# Callback to update targets graph in cohort page
@app.callback(
    [Output('phecode-graph', 'figure'),
     Output('icd-code-graph', 'figure')],
    [Input('gender-filter', 'value')]
)
def update_graphs(gender_filter):
    phecode_fig = get_target_plot('Phecode', gender_filter)
    icd_code_fig = get_target_plot('ICD code', gender_filter)
    return phecode_fig, icd_code_fig

# Callback to update the target specific age distribution graph
@app.callback(
    [Output('age-distribution-target-specific-graph', 'figure'),
     Output('bmi-distribution-target-specific-graph', 'figure'),
     Output('hs-distribution-target-specific-graph', 'figure')],
    Input('target-filter', 'value')
)
def update_target_specific_distribution_graph(selected_target):
    age = get_target_specific_dist_graph(selected_target, 'age')
    bmi = get_target_specific_dist_graph(selected_target, 'bmi')
    hs = get_target_specific_hs_graph(selected_target)

    return age, bmi, hs

def get_target_specific_dist_graph(selected_target, output_type):
    if selected_target is None:
        return go.Figure(
            layout=go.Layout(
                xaxis={"visible": False},
                yaxis={"visible": False},
                annotations=[{
                    "text": "Select target to view graph",
                    "xref": "paper",
                    "yref": "paper",
                    "showarrow": False,
                    "font": {
                        "size": 20
                    },
                    "x": 0.5,
                    "y": 0.5,
                    "xanchor": "center",
                    "yanchor": "middle"
                }],
            )
        )
    
    targets_df = db_handler.get_target_stats()

    # Filter data based on the selected target
    filtered_df = targets_df[targets_df['target_id'] == selected_target]

    if output_type == 'age':
        col_name = 'age_group'
        axis_name = 'Age'
        df_name = 'age'
    elif output_type == 'bmi':
        col_name = 'bmi_group'
        axis_name = 'BMI'
        df_name = 'bmi'

    # Group ages into 5-year intervals
    filtered_df = filtered_df.copy()
    filtered_df.loc[:, col_name] = pd.cut(filtered_df[df_name], bins=range(0, 101, 5), right=False)

    # Summarize the counts by age group and gender
    summary_df = filtered_df.groupby([col_name, 'gender'],  observed=True).agg({'count': 'sum'}).reset_index()

    # Compute the total count per age group (sum of both genders)
    total_counts = summary_df.groupby(col_name,  observed=True)['count'].sum().reset_index()
    total_counts['gender'] = 'Combined'
    summary_df = pd.concat([summary_df, total_counts])

    genders = summary_df['gender'].unique()
    age_groups = summary_df[col_name].unique()
    all_combinations = pd.MultiIndex.from_product([age_groups, genders], names=[col_name, 'gender']).to_frame(index=False)
    df_complete = pd.merge(all_combinations, summary_df, on=[col_name, 'gender'], how='left')
    df_complete['count'] = df_complete['count'].fillna(0)

    # Create the bar graph with three bars: Male, Female, and Total
    fig = go.Figure()

    genders = [['Male', colors[1]], ['Female', colors[2]], ['Combined', colors[0]]]
    for gender,color in genders:
        gender_data = df_complete[df_complete['gender'] == gender]
        fig.add_trace(go.Bar(
            x=[str(age) for age in gender_data[col_name]],
            y=gender_data['count'],
            name=gender,
            marker_color=color,
        ))

    title = f'{axis_name} - {filtered_df.iloc[0]["target_id"].capitalize()}'
    font_size = get_dynamic_font_size(title)

    # Update layout for better visualization
    fig.update_layout(
        title={
            'text': title,
            'x': 0.5,  # Center the title
            'xanchor': 'center',
            'yanchor': 'top',
            'font': {'size': font_size}
        },
        barmode='group',
        xaxis_title=f'{axis_name}',
        yaxis_title='Nº Individuals',
        xaxis_tickangle=-45,
        margin=dict(t=60, b=20, l=20, r=20),
        paper_bgcolor='rgba(0, 0, 0, 0)',
        plot_bgcolor='rgba(0, 0, 0, 0)',
        xaxis=dict(autorange=True)
    )

    # Hide the legend
    fig.update_layout(showlegend=False)

    return fig

def get_target_specific_hs_graph(selected_target):
    if selected_target is None:
        return go.Figure(
            layout=go.Layout(
                xaxis={"visible": False},
                yaxis={"visible": False},
                annotations=[{
                    "text": "Select target to view graph",
                    "xref": "paper",
                    "yref": "paper",
                    "showarrow": False,
                    "font": {
                        "size": 20
                    },
                    "x": 0.5,
                    "y": 0.5,
                    "xanchor": "center",
                    "yanchor": "middle"
                }],
            )
        )
    
    targets_df = db_handler.get_target_stats()
    filtered_df = targets_df[targets_df['target_id'] == selected_target]

    # Define the desired order for self_perceived_hs
    hs_order = ['Very Bad', 'Bad', 'Fair', 'Good', 'Very good', 'DK/NO']
    
    # Convert self_perceived_hs to a categorical type with the defined order
    filtered_df['self_perceived_hs'] = pd.Categorical(filtered_df['self_perceived_hs'], categories=hs_order, ordered=True)
    hs_dist = filtered_df.groupby(['gender', 'self_perceived_hs'], observed=False).size().unstack(fill_value=0)
    dist = hs_dist[hs_order]

    fig = go.Figure()

    # Add bar for males
    if 'Male' in dist.index:
        fig.add_trace(go.Bar(
            x=dist.columns,
            y=dist.loc['Male'],
            name='Males',
            marker_color=colors[1]
        ))

    # Add bar for females
    if 'Female' in dist.index:
        fig.add_trace(go.Bar(
            x=dist.columns,
            y=dist.loc['Female'],
            name='Females',
            marker_color=colors[2]
        ))

    # Add bar for combined data
    if 'Male' in dist.index and 'Female' in dist.index:
        combined_counts = dist.loc['Male'] + dist.loc['Female']
        fig.add_trace(go.Bar(
            x=dist.columns,
            y=combined_counts,
            name='Combined',
            marker_color=colors[0],
            opacity=0.5  # Make combined bars slightly transparent
        ))

    title = f'Self-Perc. HS - {filtered_df.iloc[0]["target_id"].capitalize()}'
    font_size = get_dynamic_font_size(title)

    # Update layout for better visualization
    fig.update_layout(
        title={
            'text': title,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': {'size': font_size}
        },
        barmode='group',
        xaxis_title='Self-Perceived HS',
        yaxis_title='Nº Individuals',
        xaxis_tickangle=-45,
        margin=dict(t=60, b=20, l=20, r=20),
        paper_bgcolor='rgba(0, 0, 0, 0)',
        plot_bgcolor='rgba(0, 0, 0, 0)',
        xaxis=dict(autorange=True)
    )

    # Hide the legend
    fig.update_layout(showlegend=False)

    return fig

# Callback to update the target specific age distribution graph
@app.callback(
    Output('gender-distribution-target-specific-graph', 'figure'),
    Input('target-filter', 'value'),
)
def update_target_specific_gender_distribution_graph(selected_target):
    if selected_target is None:
        return go.Figure(
            layout=go.Layout(
                xaxis={"visible": False},
                yaxis={"visible": False},
                annotations=[{
                    "text": "Select target to view graph",
                    "xref": "paper",
                    "yref": "paper",
                    "showarrow": False,
                    "font": {
                        "size": 20
                    },
                    "x": 0.5,
                    "y": 0.5,
                    "xanchor": "center",
                    "yanchor": "middle"
                }]
            )
        )
    
    targets_df = db_handler.get_target_stats()

    # Filter data based on the selected target
    filtered_df = targets_df[targets_df['target_id'] == selected_target]
    total_counts = filtered_df.groupby('gender')['count'].sum().reset_index()
    try:
        female_count = total_counts.loc[total_counts['gender'] == 'Female', 'count'].values[0]
    except IndexError as e:
        female_count = 0
    try:
        male_count = total_counts.loc[total_counts['gender'] == 'Male', 'count'].values[0]
    except IndexError as e:
        male_count = 0

    fig = go.Figure(
        data=go.Pie(
            values=[male_count, female_count],
            labels=["Male", "Female"],
            hole=.6,
            direction='clockwise',
            sort=True,
            marker_colors=[colors[1], colors[2]],
            textinfo='label+percent',
            textposition='outside',
            hoverinfo='label+percent'
        )
    )

    title = f'Gender - {filtered_df.iloc[0]["target_id"].capitalize()}'
    font_size = get_dynamic_font_size(title)

    fig.update(layout_showlegend=False)
    fig.update_layout(
        title={
            'text': title,
            'x': 0.5,  # Center the title
            'xanchor': 'center',
            'yanchor': 'top',
            'font': {'size': font_size}
        },
        margin=dict(t=55, b=30, l=0, r=0),
    )

    # Hide the legend
    fig.update_layout(showlegend=False)

    return fig

# Callback to change from prs page to cohort page
@app.callback(
    [Output('url', 'pathname', allow_duplicate=True),
     Output('shared-target-data', 'data')],
    [Input('redirect-button', 'n_clicks')],
    [State('clicked-data-store', 'data'),
     State('tabs', 'value')],
    prevent_initial_call=True
)
def redirect_and_set_filter(n_clicks, clicked_data, tab):
    target_type = get_target_type(tab)
    if n_clicks > 0 and clicked_data and 'name' in clicked_data:
        target_desc = clicked_data['name']
        if target_desc:
            return '/cohort', [target_desc, target_type]
    return dash.no_update, dash.no_update

# Callback to update the dropdown value
@app.callback(
    Output('target-filter', 'value'),
    [Input('phecode-graph', 'clickData'),
     Input('icd-code-graph', 'clickData'),
     Input('shared-target-data', 'data')],
)
def update_dropdown_value(phecode_click_data, icd_code_click_data, shared_data):
    ctx = dash.callback_context

    if not ctx.triggered:
        desc = shared_data[0]
        t_type = shared_data[1]
        code = db_handler.get_target_code(desc, t_type)
    else:
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

        if trigger_id == 'phecode-graph' and phecode_click_data:
            code = phecode_click_data['points'][0]['y']
        elif trigger_id == 'icd-code-graph' and icd_code_click_data:
            code = icd_code_click_data['points'][0]['y']
        else:
            return dash.no_update
    return code


# Clientside callback for scrolling
app.clientside_callback(
    """
    function(n_clicks) {
        if(n_clicks > 0) {
            var element = document.getElementById('prs-heading');
            element.scrollIntoView({ behavior: 'smooth' });
        }
        return null;
    }
    """,
    Output('location', 'href'),  # Dummy output; not actually used
    Input('table-button', 'n_clicks')
)

# Callback for the gwas table
@app.callback(
    [Output('url', 'pathname', allow_duplicate=True), Output('selected-gwas', 'data')],
    Input('gwas-table-content', 'active_cell'),
    State('gwas-table-content', 'data'),
    prevent_initial_call=True
)
def on_gwas_row_click(active_cell, table_data):
    if active_cell:
        row = active_cell['row']
        selected_gwas = table_data[row]['name']
        return '/prs', selected_gwas
    return dash.no_update, dash.no_update


# Callback to update the gwas dropdown
@app.callback(
    Output('disease-dropdown', 'value'),
    Input('selected-gwas', 'data')
)
def update_disease_dropdown(selected_gwas):
    if selected_gwas:
        return selected_gwas
    return dash.no_update


#####################################################################################################################
##################################################### App Layout ####################################################
#####################################################################################################################

def format_targets_for_dropdown():
    targets = db_handler.get_target_stats()

    # Remove duplicates based on 'target_id', 'target_description', and 'target_type'
    unique_targets = targets[['target_id', 'target_description', 'target_type']].drop_duplicates()
    unique_targets = unique_targets.sort_values(by='target_id')

    # Create a list of dictionaries for the dropdown options
    dropdown_options = [
        {
            'label': f"{row['target_id']} - {row['target_description'].capitalize()[:25]}{'...' if len(row['target_description']) > 30 else ''} ({row['target_type']})",
            'value': row['target_id']
        }
        for _, row in unique_targets.iterrows()
    ]

    return dropdown_options

def get_dynamic_font_size(title):
    # Set a base font size and reduce it based on the title length
    base_font_size = 24
    max_font_size = 16  # Maximum allowed font size
    length_threshold = 30  # Define a threshold for title length

    # Calculate the font size dynamically
    if len(title) > length_threshold:
        dynamic_size = max(12, base_font_size - (len(title) - length_threshold) * 0.5)
    else:
        dynamic_size = base_font_size

    # Ensure the font size does not exceed the max allowed size
    return min(dynamic_size, max_font_size)


# Navbar
navbar = dbc.Navbar(
    dbc.Container([
        dbc.NavbarBrand(html.Img(src="/assets/logo.png", height="30px"), className="navbar-brand"),
        dbc.NavbarToggler(id="navbar-toggler"),
        dbc.Collapse(
            dbc.Nav([
                dbc.NavItem(dbc.NavLink("PRS Visualisation", href="/", id='prs-link', className="nav-link active")),
                dbc.NavItem(dbc.NavLink("GWAS Sources", href="/gwas", id='gwas-link', className="nav-link")),
                dbc.NavItem(dbc.NavLink("Cohort Overview", href="/cohort", id='cohort-link', className="nav-link")),
                dbc.NavItem(dbc.NavLink("About the Project", href="/about", id='about-link', className="nav-link"))
            ], className="ml-auto", navbar=True),
            id="navbar-collapse",
            navbar=True,
        ),
    ], fluid=True),
    sticky="top",
)



# PRS page layout
prs_page_layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H1([
    			html.Img(src="/assets/PolyGenie.png", height="80px", style={"verticalAlign": "middle"})
		]),
                html.P("Unearthing Genetic Links with Polygenic Scores", className="subheading"),
                html.Hr(className="short-sep-line"),
            ], className="prs-info-box"),
            html.Div([
                html.Div([
                    html.H2("Select Filters", className="section-heading"),
                    html.P('Select PRS:', className="dropdown-title"),
                    dcc.Dropdown(
                        id='disease-dropdown',
                        options=disease_options,
                        placeholder='Select phenotype',
                        clearable=True,
                        value='Waist-hip Ratio',
                        className="dropdown-box"
                    ),
                    html.P('Reference Group (decile/quartile) for Comparison:', className="dropdown-title"),
                    dcc.Dropdown(
                        id='reference-dropdown',
                        options=reference_options,
                        placeholder='Select reference',
                        clearable=False,
                        value="low",
                        className="dropdown-box"
                    ),
                    html.P('PRS Division:', className="dropdown-title"),
                    dcc.Dropdown(
                        id='division-dropdown',
                        options=division_options,
                        placeholder='Select division',
                        clearable=False,
                        value="decile",
                        className="dropdown-box"
                    ),
                ]),
                html.Div([
                    html.Button("Check Results Table", id='table-button', className='button'),
                    dcc.Link(
                        html.Button("Check Available GWAS", id='gwas_button', className='button'),
                        href="/gwas"
                    )], className="button-box d-flex justify-content-center gap-3"),
                dcc.Location(id='location', refresh=False),
            ], className="dropdown-box"),
        ], xs=12, sm=12, md=4, lg=4, xl=4, className="left-container"),
        dbc.Col([
            dcc.Tabs(id="tabs", value='icd', children=[
            dcc.Tab(label='ICD codes', value='icd'),
            dcc.Tab(label='Phecodes', value='phe'),
            dcc.Tab(label='Metabolites', value='met'),
            dcc.Tab(label='Other Variables', value='quest'),
            ]),
            dcc.Graph(id='correlations-graph'),
            html.P(id='graph-footer', className="graph-footer"),
        ], xs=12, sm=12, md=8, lg=8, xl=8, className="graph-container")
    ], justify='center', className="dashboard-div"),
    html.Br(),
    # Store component to keep track of clicked data point
    dcc.Store(id='clicked-data-store'),
    html.Br(),    
    dbc.Row([
        # First row with basic statistics and one graph
        dbc.Col([
            dcc.Graph(id='prevalences-graph', className="prevalences-graph")
        ], width=12, md=7, className="full-height custom-col"),  # 70% width for the graph
        dbc.Col([
            html.Div([
                html.H2("Target Information"),
                html.P("Select a Phecode or ICD code from the graph"),
            ], className="info-box")
        ], width=12, md=5, className="target-information-box custom-col", id='target-information-box')  # 30% width for basic stats
    ], className="row-with-margin"),
    html.Br(id="prs-heading"),
    html.H2([
        html.Span("PRS Association Results"),
    ], className="section-heading heading-line"),
    html.Div([
        html.Button("Download Table", id='download-button', className='button ms-auto'),
    ], className="button-box d-flex download-button"),

    # Components to save the table and trigger the download
    dcc.Download(id="download-dataframe-excel"),  
    dcc.Store(id='table-stored-data'), 
        
    dbc.Row([
        html.Div([
            dash_table.DataTable(
                id='prs-table-content',
                columns = [{"name": col, "id": col} for col in col_headers_tokeep],                
                data=[],  
                editable=False,
                sort_action="native",  # Enable sorting
                filter_action='native',
                sort_mode="multi",  # Allow multi-column sorting
                page_action="native",  # Enable pagination
                page_current=0,  # Start from first page
                page_size=20,  # Number of rows per page

                style_cell={
                    'overflow': 'hidden',
                    'textOverflow': 'ellipsis',
                    'maxWidth': 0
                },
                
                style_header={
                'backgroundColor': 'rgba(86, 102, 122, .10)',
                'color': 'black',
                'fontWeight': 'bold',
                'textAlign': 'center'
                },

                style_data_conditional=[
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': 'rgba(86, 102, 122, .05)',
                },
                {
                    'if': {'state': 'selected'},
                    'backgroundColor': 'rgba(255, 101, 66, .10)',
                    'border': '1px solid #FF6542',
                },
                {
                    'if': {'state': 'active'},
                    'backgroundColor': 'rgba(255, 101, 66, .10)',
                    'border': '1px solid #FF6542',
                }
            ],

            )
        ], id='table-section')
    ]),
    html.Br(),
], fluid=True, style={'margin-top': '50px'})


# General app layout
app.layout = dbc.Container([
    dcc.Location(id='url', refresh=False),
    navbar,
    # Modal (Popup) for Beta Notice
    html.Div(
        id='terms-modal',
        className='modal',
        children=[
            html.Div(
                className='modal-content',
                children=[
                    html.H4('Usage and Contact Information'),
                    html.P([
                        "For questions, feedback, request a new PRS, or collaboration inquiries, please contact us at: ",
                        html.A("gcatbiobank@igtp.cat", href="mailto:gcatbiobank@igtp.cat")
                    ]),
                    html.P("If the tool contributes to a publication, please cite PolyGenie and the original GWAS used to compute the PRS."),
                    html.Button('Accept', id='accept-button', className='button', n_clicks=0),
                ]
            )
        ]
    ),

    html.Div(id='page-content'),
    dcc.Store(id='shared-target-data', data=[None, None], storage_type='session'),
    dcc.Store(id='selected-gwas', data=None)
], fluid=True)

# Callback to update the page content based on URL
@app.callback(
    Output('page-content', 'children'),
    [Input('url', 'pathname')]
)
def display_page(pathname):
        return 

@app.callback(
    Output('prs-link', 'className'),
    Output('gwas-link', 'className'),
    Output('cohort-link', 'className'),
    Output('about-link', 'className'),
    Input('url', 'pathname')
)
def update_nav_links(pathname):
    if pathname in ['/', '/prs']:
        return 'nav-link active', 'nav-link', 'nav-link', 'nav-link'

# Callback to hide modal and show content after accepting the terms
@app.callback(
    [Output('terms-modal', 'style'),
     Output('page-content', 'style')],
    [Input('accept-button', 'n_clicks')],
    [State('terms-modal', 'style')]
)
def display_content_after_accept(n_clicks, modal_style):
    if n_clicks > 0:
        # Hide the modal and show the main content
        return {'display': 'none'}, {'display': 'block'}
    # Default state (modal shown, content hidden)
    return {'display': 'block'}, {'display': 'none'}


if __name__ == "__main__":
    app.run_server(debug=True)
