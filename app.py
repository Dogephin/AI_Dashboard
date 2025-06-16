from flask import Flask, render_template
from llm import create_llm_client 
from db import test_db_connection
from analysis.overall_analysis import (
    get_sample_results, 
    error_frequency_analysis, 
    extract_relevant_text,
    bin_errors_over_time  
)

app = Flask(__name__)

test_db_connection()
llm_client = create_llm_client()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/overall')
def overall():
    results = get_sample_results()
    if not results:
        analysis_text = "No data found."
        chart_data = {
            'labels': [],
            'datasets': []
        }
    else:
        analysis_response = error_frequency_analysis(results, llm_client)
        analysis_text = extract_relevant_text(analysis_response)

        binned = bin_errors_over_time(results, bin_size=5)
        time_bins = list(binned.keys())
        warnings = [binned[t]['warnings'] for t in time_bins]
        minors = [binned[t]['minors'] for t in time_bins]
        severes = [binned[t]['severes'] for t in time_bins]

        chart_data = {
            'labels': time_bins,
            'datasets': [
                {'label': 'Warnings', 'data': warnings, 'borderColor': 'orange'},
                {'label': 'Minors', 'data': minors, 'borderColor': 'green'},
                {'label': 'Severes', 'data': severes, 'borderColor': 'red'}
            ]
        }

    return render_template('overall.html', chart_data=chart_data, analysis=analysis_text)

@app.route('/session')
def session():
    return render_template('session.html')

@app.route('/user')
def user():
    return render_template('user.html')

if __name__ == '__main__':
    app.run(debug=True)
