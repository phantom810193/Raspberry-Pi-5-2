import plotly.graph_objects as go
import plotly.express as px
import json

# Data for the flowchart with adjusted positioning
data = {
    "steps": [
        {"id": 1, "name": "消費者進入賣場", "type": "trigger", "x": 100, "y": 50},
        {"id": 2, "name": "攝影機啟動", "type": "hardware", "x": 100, "y": 120},
        {"id": 3, "name": "人臉偵測", "type": "software", "x": 100, "y": 190},
        {"id": 4, "name": "人臉辨識", "type": "software", "x": 100, "y": 260},
        {"id": 5, "name": "已知會員?", "type": "decision", "x": 100, "y": 330},
        {"id": 6, "name": "建立新會員ID", "type": "database", "x": 180, "y": 280},  # Moved closer
        {"id": 7, "name": "查詢會員資料", "type": "database", "x": 100, "y": 400},
        {"id": 8, "name": "分析消費記錄", "type": "software", "x": 100, "y": 470},
        {"id": 9, "name": "生成客製化廣告", "type": "software", "x": 100, "y": 540},
        {"id": 10, "name": "推播廣告至螢幕", "type": "display", "x": 100, "y": 610}
    ],
    "connections": [
        {"from": 1, "to": 2},
        {"from": 2, "to": 3},
        {"from": 3, "to": 4},
        {"from": 4, "to": 5},
        {"from": 5, "to": 6, "label": "否"},
        {"from": 5, "to": 7, "label": "是"},
        {"from": 6, "to": 7},
        {"from": 7, "to": 8},
        {"from": 8, "to": 9},
        {"from": 9, "to": 10}
    ]
}

# Color mapping for step types
color_map = {
    "trigger": "#1FB8CD",    # Strong cyan
    "hardware": "#DB4545",   # Bright red
    "software": "#2E8B57",   # Sea green
    "database": "#5D878F",   # Cyan
    "decision": "#D2BA4C",   # Moderate yellow
    "display": "#B4413C"     # Moderate red
}

# Create figure
fig = go.Figure()

# Create lookup for steps
steps_lookup = {step["id"]: step for step in data["steps"]}

# Add connection lines with arrows
for conn in data["connections"]:
    from_step = steps_lookup[conn["from"]]
    to_step = steps_lookup[conn["to"]]
    
    # Add main line
    fig.add_trace(go.Scatter(
        x=[from_step["x"], to_step["x"]],
        y=[from_step["y"], to_step["y"]],
        mode='lines',
        line=dict(color='#333333', width=3),
        showlegend=False,
        hoverinfo='skip'
    ))
    
    # Add arrow head
    dx = to_step["x"] - from_step["x"]
    dy = to_step["y"] - from_step["y"]
    length = (dx**2 + dy**2)**0.5
    
    if length > 0:
        # Normalize direction
        dx_norm = dx / length
        dy_norm = dy / length
        
        # Arrow head position (closer to target node)
        arrow_x = to_step["x"] - dx_norm * 25
        arrow_y = to_step["y"] - dy_norm * 25
        
        # Arrow head points
        arrow_size = 8
        perp_x = -dy_norm * arrow_size
        perp_y = dx_norm * arrow_size
        
        fig.add_trace(go.Scatter(
            x=[arrow_x - dx_norm * arrow_size + perp_x, arrow_x, arrow_x - dx_norm * arrow_size - perp_x, arrow_x - dx_norm * arrow_size + perp_x],
            y=[arrow_y - dy_norm * arrow_size + perp_y, arrow_y, arrow_y - dy_norm * arrow_size - perp_y, arrow_y - dy_norm * arrow_size + perp_y],
            mode='lines',
            line=dict(color='#333333', width=3),
            fill='toself',
            fillcolor='#333333',
            showlegend=False,
            hoverinfo='skip'
        ))
    
    # Add connection labels for decision branches
    if "label" in conn:
        mid_x = (from_step["x"] + to_step["x"]) / 2
        mid_y = (from_step["y"] + to_step["y"]) / 2
        
        # Offset label slightly to avoid line overlap
        offset_x = 15 if conn["label"] == "否" else -15
        
        fig.add_trace(go.Scatter(
            x=[mid_x + offset_x],
            y=[mid_y],
            mode='text',
            text=[conn["label"]],
            textfont=dict(size=12, color='#333333'),
            showlegend=False,
            hoverinfo='skip'
        ))

# Group steps by type for legend
step_types = {}
for step in data["steps"]:
    step_type = step["type"]
    if step_type not in step_types:
        step_types[step_type] = []
    step_types[step_type].append(step)

# Abbreviate long names to fit 15 character limit
name_abbreviations = {
    "消費者進入賣場": "進入賣場",
    "攝影機啟動": "攝影機啟動", 
    "人臉偵測": "人臉偵測",
    "人臉辨識": "人臉辨識",
    "已知會員?": "已知會員?",
    "建立新會員ID": "建立會員ID",
    "查詢會員資料": "查詢資料",
    "分析消費記錄": "分析記錄", 
    "生成客製化廣告": "生成廣告",
    "推播廣告至螢幕": "推播螢幕"
}

# Add nodes for each step type
for step_type, steps in step_types.items():
    x_coords = [step["x"] for step in steps]
    y_coords = [step["y"] for step in steps]
    text_labels = [name_abbreviations.get(step["name"], step["name"]) for step in steps]
    
    fig.add_trace(go.Scatter(
        x=x_coords,
        y=y_coords,
        mode='markers+text',
        marker=dict(
            color=color_map[step_type],
            size=60,  # Increased size
            symbol='diamond' if step_type == 'decision' else 'circle',
            line=dict(width=2, color='white')
        ),
        text=text_labels,
        textposition='middle center',
        textfont=dict(size=12, color='white', family='Arial Black'),  # Increased font size and made bold
        name=step_type.title(),
        showlegend=True,
        hovertemplate='<b>%{text}</b><extra></extra>'
    ))

# Update layout
fig.update_layout(
    title="Raspberry Pi Face Recognition Ad System",
    showlegend=True,
    legend=dict(
        orientation='h', 
        yanchor='bottom', 
        y=-0.1,  # Moved closer to chart
        xanchor='center', 
        x=0.5,
        bgcolor='rgba(255,255,255,0.8)',
        bordercolor='gray',
        borderwidth=1
    ),
    xaxis=dict(
        showgrid=False, 
        showticklabels=False, 
        zeroline=False,
        range=[20, 260]  # Adjusted range for better fit
    ),
    yaxis=dict(
        showgrid=False, 
        showticklabels=False, 
        zeroline=False, 
        autorange='reversed',
        range=[20, 640]
    ),
    plot_bgcolor='white',
    paper_bgcolor='white'
)

# Update traces to prevent clipping
fig.update_traces(cliponaxis=False)

# Save the chart
fig.write_image("chart.png")
fig.write_image("chart.svg", format="svg")

fig.show()