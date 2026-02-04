"""
ENVIRONMENTAL INEQUALITY DASHBOARD - WITH ENHANCED MAP (FIXED)
Fixed to handle missing columns
"""

from flask import Flask, render_template, jsonify
import pandas as pd
import folium
import plotly.graph_objects as go
import plotly
import json

app = Flask(__name__)

# ============================================================================
# LOAD DATA AT STARTUP
# ============================================================================

print("\n" + "="*80)
print("🚀 LOADING DATA...")
print("="*80)

df = None

try:
    df = pd.read_csv('pune_environmental_data.csv')
    print(f"✅ CSV LOADED: {len(df)} rows")
    print(f"✅ Columns: {list(df.columns)}")
    
    # Fix column names
    if 'latitude' in df.columns:
        df['lat'] = df['latitude']
    if 'longitude' in df.columns:
        df['lon'] = df['longitude']
    
    # Add missing columns if they don't exist
    if 'population' not in df.columns:
        print("⚠️  'population' column not found - using default values")
        df['population'] = 50000  # Default population
    
    if 'total_budget' not in df.columns:
        print("⚠️  'total_budget' column not found - using default values")
        df['total_budget'] = 100000000  # Default budget in Crores
    
    print(f"✅ Data ready for {len(df)} wards")
    print("="*80 + "\n")
    
except Exception as e:
    print(f"❌ ERROR LOADING CSV: {e}")
    print("="*80 + "\n")
    df = None

# ============================================================================
# ROUTES
# ============================================================================

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/api/overview', methods=['GET'])
def get_overview():
    """Get overview statistics"""
    if df is None:
        return jsonify({
            'total_wards': 0,
            'high_stress_count': 0,
            'medium_stress_count': 0,
            'low_stress_count': 0,
            'avg_pm25': 0,
            'avg_esi': 0,
        }), 200
    
    try:
        high = int(len(df[df['stress_zone'] == 'High Stress']))
        medium = int(len(df[df['stress_zone'] == 'Medium Stress']))
        low = int(len(df[df['stress_zone'] == 'Low Stress']))
        
        data = {
            'total_wards': int(len(df)),
            'high_stress_count': high,
            'medium_stress_count': medium,
            'low_stress_count': low,
            'avg_pm25': round(float(df['pm25'].mean()), 1),
            'avg_esi': round(float(df['esi'].mean()), 3),
        }
        
        print(f"✅ Overview API called: {data}")
        return jsonify(data), 200
        
    except Exception as e:
        print(f"❌ Overview error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stress-distribution', methods=['GET'])
def stress_distribution():
    """Stress distribution pie chart"""
    if df is None:
        return jsonify({'data': [], 'layout': {}}), 200
    
    try:
        stress_counts = df['stress_zone'].value_counts().to_dict()
        
        fig = go.Figure(data=[
            go.Pie(
                labels=list(stress_counts.keys()),
                values=list(stress_counts.values()),
                marker=dict(colors=['#e74c3c', '#f39c12', '#2ecc71']),
                textinfo='label+percent+value',
            )
        ])
        fig.update_layout(title='Stress Zone Distribution', height=450)
        
        return jsonify(json.loads(plotly.io.to_json(fig))), 200
        
    except Exception as e:
        print(f"❌ Stress chart error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/pm25-green', methods=['GET'])
def pm25_green():
    """PM2.5 vs Green Cover scatter"""
    if df is None:
        return jsonify({'data': [], 'layout': {}}), 200
    
    try:
        colors_map = {'High Stress': '#e74c3c', 'Medium Stress': '#f39c12', 'Low Stress': '#2ecc71'}
        fig = go.Figure()
        
        for zone in ['Low Stress', 'Medium Stress', 'High Stress']:
            zone_data = df[df['stress_zone'] == zone]
            if len(zone_data) > 0:
                fig.add_trace(go.Scatter(
                    x=list(zone_data['green_cover'] * 100),
                    y=list(zone_data['pm25']),
                    mode='markers',
                    name=zone,
                    marker=dict(size=10, color=colors_map[zone], opacity=0.7),
                    text=list(zone_data['ward']),
                    hovertemplate='<b>%{text}</b><br>Green: %{x:.1f}%<br>PM2.5: %{y:.1f}<extra></extra>'
                ))
        
        fig.update_layout(
            title='PM2.5 vs Green Cover',
            xaxis_title='Green Cover (%)',
            yaxis_title='PM2.5 (µg/m³)',
            height=450
        )
        
        return jsonify(json.loads(plotly.io.to_json(fig))), 200
        
    except Exception as e:
        print(f"❌ PM2.5 chart error: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# API: ENHANCED INTERACTIVE MAP WITH DETAILED POPUPS
# ============================================================================

@app.route('/api/map', methods=['GET'])
def get_map():
    """Enhanced interactive map with detailed popups"""
    if df is None:
        return '<div style="color: red; padding: 2rem;">Error: No data</div>', 200
    
    try:
        colors = {'High Stress': '#e74c3c', 'Medium Stress': '#f39c12', 'Low Stress': '#2ecc71'}
        
        # Create Folium map with better styling
        m = folium.Map(
            location=[18.52, 73.85],
            zoom_start=11,
            tiles='OpenStreetMap'
        )
        
        # Add circle markers for each ward
        for idx, row in df.iterrows():
            stress = row['stress_zone']
            color = colors.get(stress, '#999')
            
            # Size based on ESI value
            radius = max(8, min(25, 5 + (row['esi'] * 20)))
            
            # Get values with defaults for missing columns
            population = row.get('population', 50000)
            total_budget = row.get('total_budget', 100000000)
            
            # Create detailed popup content
            popup_html = f"""
            <div style="font-family: Arial, sans-serif; width: 300px;">
                <h4 style="margin: 5px 0; color: #2c3e50; border-bottom: 2px solid {color}; padding-bottom: 5px;">
                    {row['ward']}
                </h4>
                
                <div style="margin-top: 10px;">
                    <p style="margin: 5px 0;"><b> Geographic Location:</b></p>
                    <div style="background: #f5f5f5; padding: 8px; border-radius: 4px; margin: 5px 0;">
                        <p style="margin: 3px 0; font-size: 12px;">
                            <b>Coordinates:</b> ({row['lat']:.4f}, {row['lon']:.4f})
                        </p>
                    </div>
                </div>
                
                <div style="margin-top: 10px;">
                    <p style="margin: 5px 0;"><b> Environmental Metrics:</b></p>
                    <table style="width: 100%; font-size: 12px; border-collapse: collapse;">
                        <tr style="background: #f9f9f9;">
                            <td style="padding: 5px; border: 1px solid #ddd;"><b>PM2.5</b></td>
                            <td style="padding: 5px; border: 1px solid #ddd;">{row['pm25']:.1f} µg/m³</td>
                        </tr>
                        <tr>
                            <td style="padding: 5px; border: 1px solid #ddd;"><b>Heat</b></td>
                            <td style="padding: 5px; border: 1px solid #ddd;">{row['heat']:.1f}°C</td>
                        </tr>
                        <tr style="background: #f9f9f9;">
                            <td style="padding: 5px; border: 1px solid #ddd;"><b>Green Cover</b></td>
                            <td style="padding: 5px; border: 1px solid #ddd;">{row['green_cover']*100:.1f}%</td>
                        </tr>
                        <tr>
                            <td style="padding: 5px; border: 1px solid #ddd;"><b>Population Density</b></td>
                            <td style="padding: 5px; border: 1px solid #ddd;">{row['pop_density']:.0f}/km²</td>
                        </tr>
                        <tr style="background: #f9f9f9;">
                            <td style="padding: 5px; border: 1px solid #ddd;"><b>ESI Score</b></td>
                            <td style="padding: 5px; border: 1px solid #ddd;"><b style="color: {color};">{row['esi']:.3f}</b></td>
                        </tr>
                    </table>
                </div>
                
                <div style="margin-top: 10px;">
                    <p style="margin: 5px 0;"><b> Stress Zone:</b></p>
                    <div style="padding: 6px; background: {color}; color: white; border-radius: 4px; text-align: center; font-weight: bold;">
                        {stress}
                    </div>
                </div>
                
                <div style="margin-top: 10px;">
                    <p style="margin: 5px 0;"><b>👥 Population Information:</b></p>
                    <p style="font-size: 12px; margin: 5px 0;">
                        Total Population: <b>{int(population):,}</b>
                    </p>
                </div>
                
               
                    </p>
                </div>
            </div>
            """
            
            popup = folium.Popup(popup_html, max_width=350)
            
            # Add circle marker
            folium.CircleMarker(
                location=[row['lat'], row['lon']],
                radius=radius,
                popup=popup,
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=0.7,
                weight=2,
                tooltip=f"<b>{row['ward']}</b><br>ESI: {row['esi']:.3f}<br>Stress: {stress}"
            ).add_to(m)
        
        # Add legend
        legend_html = '''
        <div style="position: fixed; 
                    bottom: 50px; right: 10px; width: 280px; height: auto; 
                    background-color: white; border:2px solid grey; z-index:9999; font-size:12px;
                    padding: 10px; border-radius: 5px; box-shadow: 0 0 15px rgba(0,0,0,0.2);">
            <h4 style="margin: 0 0 10px 0; color: #2c3e50; border-bottom: 2px solid #e74c3c; padding-bottom: 5px;">
                PUNE DISTRICT - ENVIRONMENTAL STRESS ZONES
            </h4>
            
            <p style="margin: 8px 0; font-weight: bold; color: #2c3e50;">STRESS LEVELS:</p>
            
            <div style="margin-bottom: 10px;">
                <div style="display: flex; align-items: center; margin: 5px 0;">
                    <div style="width: 15px; height: 15px; background: #e74c3c; border-radius: 50%; margin-right: 8px;"></div>
                    <span><b>High Stress</b> - Immediate Intervention (ESI > 0.65)</span>
                </div>
                <div style="display: flex; align-items: center; margin: 5px 0;">
                    <div style="width: 15px; height: 15px; background: #f39c12; border-radius: 50%; margin-right: 8px;"></div>
                    <span><b>Medium Stress</b> - Preventive Measures (ESI 0.45-0.65)</span>
                </div>
                <div style="display: flex; align-items: center; margin: 5px 0;">
                    <div style="width: 15px; height: 15px; background: #2ecc71; border-radius: 50%; margin-right: 8px;"></div>
                    <span><b>Low Stress</b> - Maintenance Only (ESI < 0.45)</span>
                </div>
            </div>
            
            <p style="margin: 8px 0; font-weight: bold; color: #2c3e50;">CIRCLE SIZE:</p>
            <p style="margin: 5px 0; font-size: 11px;">
                • Larger circles = Higher ESI (more stressed)<br>
                • Smaller circles = Lower ESI (healthier)
            </p>
            
        </div>
        '''
        m.get_root().html.add_child(folium.Element(legend_html))
        
        print("✅ Map created successfully")
        return m._repr_html_(), 200
        
    except Exception as e:
        print(f"❌ Map error: {e}")
        import traceback
        traceback.print_exc()
        return f'<div style="color: red; padding: 2rem;">Error: {str(e)}</div>', 200

@app.route('/api/wards', methods=['GET'])
def get_wards():
    """All ward data for table"""
    if df is None:
        return jsonify([]), 200
    
    try:
        data = df[['ward', 'pm25', 'heat', 'pop_density', 'green_cover', 'esi', 'stress_zone']].copy()
        data = data.sort_values('esi', ascending=False)
        return jsonify(data.to_dict('records')), 200
    except Exception as e:
        print(f"❌ Wards error: {e}")
        return jsonify([]), 200

@app.route('/api/insights', methods=['GET'])
def get_insights():
    """Key insights from data"""
    if df is None:
        return jsonify([]), 200
    
    try:
        insights = []
        
        critical = len(df[df['stress_zone'] == 'High Stress'])
        total = len(df)
        insights.append({
            'type': 'critical',
            'icon': '🚨',
            'title': 'Critical Zones',
            'text': f"{critical} wards ({critical/total*100:.0f}%) need urgent intervention",
            'action': 'High ESI > 0.65'
        })
        
        worst_idx = df['pm25'].idxmax()
        worst_ward = df.loc[worst_idx]
        avg_pm25 = df['pm25'].mean()
        pct_above = ((worst_ward['pm25'] / avg_pm25 - 1) * 100) if avg_pm25 > 0 else 0
        insights.append({
            'type': 'pollution',
            'icon': '💨',
            'title': 'Pollution Hotspot',
            'text': f"{worst_ward['ward']}: {worst_ward['pm25']:.1f} µg/m³",
            'action': f"{pct_above:.0f}% above avg"
        })
        
        avg_green = df['green_cover'].mean()
        target = 0.25
        gap = (target - avg_green) * 100
        insights.append({
            'type': 'green',
            'icon': '🌳',
            'title': 'Green Cover Gap',
            'text': f"Current: {avg_green*100:.1f}% | Target: 25%",
            'action': f"Need +{gap:.1f}%"
        })
        
        critical_pop = df[df['stress_zone'] == 'High Stress']['population'].sum() if 'population' in df.columns else 0
        insights.append({
            'type': 'population',
            'icon': '👥',
            'title': 'Population at Risk',
            'text': f"{critical_pop/1e6:.1f}M people in critical zones",
            'action': 'Urgent action'
        })
        
        high_budget = df[df['stress_zone'] == 'High Stress']['total_budget'].sum() if 'total_budget' in df.columns else 0
        total_budget = df['total_budget'].sum() if 'total_budget' in df.columns else 1
        pct_budget = (high_budget / total_budget * 100) if total_budget > 0 else 0
        insights.append({
            'type': 'budget',
            'icon': '💰',
            'title': 'Budget Strategy',
            'text': f"₹{high_budget/10000000:.1f}Cr to critical zones",
            'action': f"{pct_budget:.0f}% of total"
        })
        
        return jsonify(insights), 200
        
    except Exception as e:
        print(f"❌ Insights error: {e}")
        return jsonify([]), 200

@app.route('/api/faq', methods=['GET'])
def get_faq():
    """FAQ data"""
    faq = [
        {
            'question': 'What does "High Stress" mean?',
            'answer': 'High Stress wards have ESI > 0.65, indicating environmental challenges requiring immediate intervention.'
        },
        {
            'question': 'How is ESI calculated?',
            'answer': 'Environmental Stress Index = 40% PM2.5 + 20% Heat + 25% Density + 15% Green Deficit'
        },
        {
            'question': 'Which wards need priority?',
            'answer': 'High Stress wards with high population density should get priority.'
        },
        {
            'question': 'How can ESI be reduced?',
            'answer': '1) Plant trees (green cover) → 25-30% reduction\n2) Reduce emissions → 15-20% reduction\n3) Improve monitoring'
        },
        {
            'question': 'What is PM2.5?',
            'answer': 'Particulate matter < 2.5µm. WHO safe limit: 15 µg/m³. High PM2.5 causes respiratory problems.'
        },
    ]
    return jsonify(faq), 200

# ============================================================================
# RUN
# ============================================================================

if __name__ == '__main__':
    print("="*80)
    print("🚀 ENVIRONMENTAL INEQUALITY DASHBOARD")
    print("="*80)
    
    if df is not None:
        print(f"✅ Data: {len(df)} wards")
        print(f"✅ High Stress: {len(df[df['stress_zone']=='High Stress'])}")
        print(f"✅ Running on http://localhost:5000")
    else:
        print("❌ CSV not found - running with empty data")
    
    print("="*80)
    print()
    
    app.run(debug=True, port=5000, use_reloader=False)