from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import pandas as pd
import numpy as np
from datetime import datetime
import io
import json
import os

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

def analyze_dataframe(df):
    """Analyze the dataframe and generate insights"""
    insights = {
        'summary': {},
        'top_items': [],
        'charts': {},
        'statistics': {}
    }
    
    # Basic summary
    insights['summary']['total_rows'] = len(df)
    insights['summary']['total_columns'] = len(df.columns)
    insights['summary']['columns'] = df.columns.tolist()
    
    # Detect numeric columns
    numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
    
    # Detect potential date columns
    date_columns = []
    for col in df.columns:
        if df[col].dtype == 'object':
            try:
                pd.to_datetime(df[col], errors='coerce')
                if pd.to_datetime(df[col], errors='coerce').notna().sum() > len(df) * 0.5:
                    date_columns.append(col)
            except:
                pass
    
    # Calculate total earnings (sum of numeric columns that might represent money)
    earnings_keywords = ['price', 'total', 'amount', 'revenue', 'earnings', 'sales', 'cost']
    earnings_columns = [col for col in numeric_columns if any(keyword in col.lower() for keyword in earnings_keywords)]
    
    if earnings_columns:
        for col in earnings_columns:
            insights['summary'][f'total_{col.lower()}'] = float(df[col].sum())
            insights['summary'][f'average_{col.lower()}'] = float(df[col].mean())
    
    # Find top items (categorical columns with counts)
    categorical_columns = df.select_dtypes(include=['object']).columns.tolist()
    categorical_columns = [col for col in categorical_columns if col not in date_columns]
    
    if categorical_columns:
        # Get top items from first categorical column
        first_cat = categorical_columns[0]
        top_items_df = df[first_cat].value_counts().head(10)
        insights['top_items'] = [
            {'name': str(name), 'count': int(count)} 
            for name, count in top_items_df.items()
        ]
        
        # Create chart data for top items
        insights['charts']['top_items'] = {
            'labels': [str(name) for name in top_items_df.index],
            'data': [int(count) for count in top_items_df.values],
            'title': f'Top {first_cat}'
        }
    
    # Analyze delivery times or date-based metrics
    if date_columns:
        for date_col in date_columns[:1]:  # Analyze first date column
            try:
                df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                df_sorted = df.sort_values(date_col)
                
                # Group by date and count
                daily_counts = df[date_col].dt.date.value_counts().sort_index()
                
                insights['charts']['timeline'] = {
                    'labels': [str(date) for date in daily_counts.index[-30:]],  # Last 30 days
                    'data': [int(count) for count in daily_counts.values[-30:]],
                    'title': f'Activity Over Time ({date_col})'
                }
            except:
                pass
    
    # Statistics for numeric columns
    if numeric_columns:
        for col in numeric_columns[:5]:  # Limit to first 5 numeric columns
            insights['statistics'][col] = {
                'min': float(df[col].min()),
                'max': float(df[col].max()),
                'mean': float(df[col].mean()),
                'median': float(df[col].median()),
                'std': float(df[col].std()) if len(df) > 1 else 0
            }
        
        # Create distribution chart for first numeric column
        if len(numeric_columns) > 0:
            first_num = numeric_columns[0]
            # Create bins for histogram
            hist, bin_edges = np.histogram(df[first_num].dropna(), bins=20)
            insights['charts']['distribution'] = {
                'labels': [f'{bin_edges[i]:.2f}' for i in range(len(hist))],
                'data': [int(count) for count in hist],
                'title': f'{first_num} Distribution'
            }
    
    # If we have both categorical and numeric columns, create a grouped analysis
    if categorical_columns and numeric_columns:
        cat_col = categorical_columns[0]
        num_col = numeric_columns[0]
        grouped = df.groupby(cat_col)[num_col].sum().sort_values(ascending=False).head(10)
        
        insights['charts']['grouped_analysis'] = {
            'labels': [str(name) for name in grouped.index],
            'data': [float(val) for val in grouped.values],
            'title': f'{num_col} by {cat_col}'
        }
    
    return insights

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

@app.route('/api/upload', methods=['POST'])
def upload_csv():
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.endswith('.csv'):
            return jsonify({'error': 'Please upload a CSV file'}), 400
        
        # Read CSV into pandas dataframe
        csv_data = file.read().decode('utf-8')
        df = pd.read_csv(io.StringIO(csv_data))
        
        # Analyze the data
        insights = analyze_dataframe(df)
        
        # Return insights as JSON
        return jsonify({
            'success': True,
            'insights': insights,
            'message': 'CSV analyzed successfully'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)

